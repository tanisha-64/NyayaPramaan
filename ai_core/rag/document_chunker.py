"""
Document Chunker — page-aware chunking, batched embedding with retries, OCR fallback
for scanned pages, and SAFE (never destructive-before-success) re-indexing.

Every indexing entry point returns / records an IndexReport so "ready" can never again
silently mean "some pages were dropped".
"""
import re
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict

from pypdf import PdfReader
from ai_core.rag.embeddings import embed_texts_batch
from ai_core.rag.provenance import starts_paragraph
from ai_core.rag.vector_store import (
    insert_document_chunks_batch,
    count_document_chunks,
    list_document_chunk_ids,
    delete_document_chunks,
    get_supabase_client,
    invalidate_case_cache,
    PartialInsertError,
)

BATCH_SIZE = 20             # PDF pages processed per embed+insert round
EMBED_TEXTS_PER_CALL = 50   # embedding API accepts up to 100 texts; stay well under
MAX_CHUNK_CHARS = 1200      # ~300 tokens: small enough for precise retrieval, large enough for context
CHUNK_OVERLAP_CHARS = 150
MIN_CHUNK_CHARS = 30
MIN_PAGE_TEXT_CHARS = 20    # below this a PDF page is treated as scanned and OCR is attempted
EST_CHARS_PER_PAGE = 3000   # only used when the source text carries no page information
EMBED_ATTEMPTS = 3
EMBED_RETRY_DELAY = 1.0     # seconds; doubled each retry
LOCK_WAIT_SECONDS = 600.0   # how long a BLOCKING indexer waits for another indexer of the same case

PAGE_BREAK = "\f"           # emitted between pages by document_reader
_EXPLICIT_PAGE_MARKER = re.compile(r"(?:\[Page\s*(\d+)\]|---\s*Page\s*(\d+)\s*---)", re.IGNORECASE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?।])\s+")


@dataclass
class IndexReport:
    source: str = "text"                 # "pdf" | "text"
    total_pages: int = 0
    pages_with_text: int = 0
    pages_indexed: int = 0
    ocr_pages: int = 0
    chunks_expected: int = 0
    chunks_inserted: int = 0
    failed_pages: list = field(default_factory=list)
    pages_estimated: bool = False        # True => page numbers are approximations, not real page boundaries
    skipped_existing: bool = False       # True => an identical complete index already existed
    kept_previous_index: bool = False    # True => re-index failed and the previous index was preserved
    error: str | None = None

    @property
    def complete(self) -> bool:
        return self.error is None and not self.failed_pages and self.chunks_inserted + (0) > 0 \
            and self.pages_indexed >= self.pages_with_text

    @property
    def indexed_chunks(self) -> int:
        return self.chunks_inserted

    def to_dict(self) -> dict:
        d = asdict(self)
        d["complete"] = self.complete
        return d


# ---------------------------------------------------------------- one indexer per case (per process)

_locks_guard = threading.Lock()
_case_locks: dict[str, threading.Lock] = {}


@contextmanager
def _case_index_lock(case_id: str, wait: bool):
    """Two indexers of the same case (background upload task + an on-the-fly index triggered by a chat request, or a
    re-index) would both see "nothing indexed" and both insert, leaving duplicate chunks. This serialises them within
    one process. It does NOT protect across several app instances; there the safe-replace logic limits the damage to
    duplicates that the next re-index removes."""
    with _locks_guard:
        lock = _case_locks.setdefault(case_id, threading.Lock())
    got = lock.acquire(timeout=LOCK_WAIT_SECONDS) if wait else lock.acquire(blocking=False)
    try:
        yield got
    finally:
        if got:
            lock.release()


# ---------------------------------------------------------------- pure chunking

def _pack_units(units: list[str], max_chars: int, overlap: int) -> list[str]:
    """Greedy packing. A unit that begins a numbered paragraph ("12. ...") is joined with a newline instead of a space
    so the marker stays at the start of a line; provenance.paragraph_numbers() relies on that."""
    chunks: list[str] = []
    current = ""
    for unit in units:
        sep = "\n" if starts_paragraph(unit) else " "
        if current and len(current) + 1 + len(unit) > max_chars:
            chunks.append(current)
            tail = current[-overlap:] if overlap > 0 else ""
            if tail:
                cut = tail.find(" ")
                tail = tail[cut + 1:] if 0 <= cut < len(tail) - 1 else tail
            current = f"{tail}{sep}{unit}".strip() if tail else unit
            if len(current) > max_chars:   # overlap pushed it over: drop the overlap rather than the unit
                current = unit
        else:
            current = f"{current}{sep}{unit}".strip() if current else unit
    if current:
        chunks.append(current)
    return chunks


def split_text_into_chunks(text: str, max_chars: int = MAX_CHUNK_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    """Splits text into chunks of at most max_chars, preferring paragraph then sentence boundaries."""
    if not text or not text.strip():
        return []
    overlap = max(0, min(overlap, max_chars // 3))
    units: list[str] = []
    for para in re.split(r"\n\s*\n|\n", text):
        para = re.sub(r"[ \t]+", " ", para).strip()
        if not para:
            continue
        if len(para) <= max_chars:
            units.append(para)
            continue
        for sent in _SENTENCE_SPLIT.split(para):
            sent = sent.strip()
            while len(sent) > max_chars:      # pathological: no sentence boundary at all
                cut = sent.rfind(" ", 0, max_chars)
                cut = cut if cut > max_chars // 2 else max_chars
                units.append(sent[:cut].strip())
                sent = sent[cut:].strip()
            if sent:
                units.append(sent)
    return [c for c in _pack_units(units, max_chars, overlap) if len(c) >= MIN_CHUNK_CHARS or len(units) == 1]


def pages_from_text(case_text: str) -> tuple[list[tuple[int, str]], bool]:
    """Returns ([(page_number, page_text)], pages_estimated).

    Uses real page boundaries when the text carries them (form-feed from document_reader, or explicit
    [Page N] / --- Page N --- markers). Otherwise page numbers are ESTIMATES and flagged as such.
    'Page X of Y' is deliberately NOT treated as a boundary: it is usually a footer, so it would shift
    every following chunk onto the wrong page."""
    if PAGE_BREAK in case_text:      # split BEFORE any strip(): str.strip() also removes leading form-feeds
        pages = [(i + 1, p.strip()) for i, p in enumerate(case_text.split(PAGE_BREAK))]
        return [(n, p) for n, p in pages if p], False
    text = case_text.strip()

    parts = _EXPLICIT_PAGE_MARKER.split(text)
    if len(parts) > 1:
        pages: list[tuple[int, str]] = []
        current = 1
        if parts[0].strip():
            pages.append((1, parts[0].strip()))
        for i in range(1, len(parts), 3):
            current = int(parts[i] or parts[i + 1])
            body = (parts[i + 2] or "").strip()
            if body:
                pages.append((current, body))
        if pages:
            return pages, False

    # No page information: estimate from the chunk's position in the text (flagged via pages_estimated).
    estimated: list[tuple[int, str]] = []
    pos = 0
    for c in split_text_into_chunks(text):
        loc = text.find(c[:40], pos)
        pos = loc if loc >= 0 else pos
        estimated.append((pos // EST_CHARS_PER_PAGE + 1, c))
    return estimated, True


def build_page_chunks(case_text: str) -> tuple[list[tuple[int, str]], bool]:
    """(page_number, chunk_text) pairs for a document's extracted text, plus the pages_estimated flag."""
    if not case_text or not case_text.strip():
        return [], False
    pages, estimated = pages_from_text(case_text)
    if estimated:                 # pages_from_text already returned chunk-level entries
        return _dedupe(pages), True
    out: list[tuple[int, str]] = []
    for page_number, page_text in pages:
        out.extend((page_number, c) for c in split_text_into_chunks(page_text))
    return _dedupe(out), False


def _dedupe(chunks: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Drops exact repeats of the same text on the same page (a duplicated extraction would otherwise be indexed twice
    and crowd out distinct passages). Identical text on DIFFERENT pages is kept: it is a different citation."""
    seen, out = set(), []
    for item in chunks:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


# ---------------------------------------------------------------- embedding

def _embed_all(texts: list[str]) -> list[list[float]]:
    """Embeds with retries. Raises if any text ends up without an embedding (never returns a short list)."""
    out: list[list[float]] = []
    for i in range(0, len(texts), EMBED_TEXTS_PER_CALL):
        group = texts[i:i + EMBED_TEXTS_PER_CALL]
        delay = EMBED_RETRY_DELAY
        for attempt in range(1, EMBED_ATTEMPTS + 1):
            try:
                vectors = embed_texts_batch(group)
                if len(vectors) != len(group):
                    raise RuntimeError(f"embedding API returned {len(vectors)} vectors for {len(group)} texts")
                out.extend(vectors)
                break
            except Exception:
                if attempt == EMBED_ATTEMPTS:
                    raise
                time.sleep(delay)
                delay *= 2
    return out


# ---------------------------------------------------------------- persistence

def _rollback(ids: list[str]) -> None:
    if ids:
        try:
            delete_document_chunks(ids)
        except Exception as e:
            print(f"[document_chunker] rollback of {len(ids)} chunks failed: {type(e).__name__}")


def _safe_old_ids(case_id: str) -> list[str]:
    try:
        return list_document_chunk_ids(case_id)
    except Exception:
        return []


def _insert_batch(case_id: str, chunks: list[tuple[int, str]]) -> list[str]:
    """Embed + insert one batch. Raises on failure AFTER removing any rows of this batch that were written."""
    embeddings = _embed_all([t for (_, t) in chunks])
    try:
        return insert_document_chunks_batch(case_id, chunks, embeddings)
    except PartialInsertError as e:
        _rollback(e.inserted_ids)
        raise
    finally:
        invalidate_case_cache(case_id)        # hybrid search keeps a short-lived per-case text index


def _finish_swap(case_id: str, report: IndexReport, new_ids: list[str], old_ids: list[str]) -> None:
    """Decides which index survives. Old rows are deleted only after the new ones are known-good."""
    invalidate_case_cache(case_id)
    if report.chunks_inserted == 0:
        _rollback(new_ids)
        report.kept_previous_index = bool(old_ids)
        invalidate_case_cache(case_id)
        return
    if report.failed_pages and old_ids:
        # Re-index was incomplete and a previous index exists: keep the previous one untouched.
        _rollback(new_ids)
        report.kept_previous_index = True
        report.chunks_inserted = 0
        report.pages_indexed = 0
        return
    _rollback(old_ids)


# ---------------------------------------------------------------- public: text path

def index_case_text(case_text: str, case_id: str, force: bool = False, wait: bool = True) -> IndexReport:
    """Chunks extracted text (page-aware when possible) and indexes it. Safe to call repeatedly:
    an identical complete index is left alone; anything else is replaced without a window of no data.
    wait=False returns immediately (error "index_in_progress") if another thread is indexing this case."""
    with _case_index_lock(case_id, wait) as got:
        if not got:
            return IndexReport(source="text", error="index_in_progress")
        return _index_case_text_locked(case_text, case_id, force)


def _index_case_text_locked(case_text: str, case_id: str, force: bool) -> IndexReport:
    report = IndexReport(source="text")
    if not case_text or not case_text.strip() or not case_id:
        report.error = "empty_text"
        return report

    chunks, estimated = build_page_chunks(case_text)
    report.pages_estimated = estimated
    report.chunks_expected = len(chunks)
    report.total_pages = max((p for p, _ in chunks), default=0)
    report.pages_with_text = len({p for p, _ in chunks})
    if not chunks:
        report.error = "no_chunks"
        return report

    existing = count_document_chunks(case_id)
    if not force and existing == len(chunks):
        report.skipped_existing = True
        report.chunks_inserted = existing
        report.pages_indexed = report.pages_with_text
        return report

    old_ids = _safe_old_ids(case_id) if existing != 0 else []
    new_ids: list[str] = []
    indexed_pages: set[int] = set()
    for i in range(0, len(chunks), BATCH_SIZE * 3):
        batch = chunks[i:i + BATCH_SIZE * 3]
        try:
            new_ids.extend(_insert_batch(case_id, batch))
            report.chunks_inserted += len(batch)
            indexed_pages.update(p for p, _ in batch)
        except Exception as e:
            report.failed_pages.extend(sorted({p for p, _ in batch}))
            report.error = f"{type(e).__name__}"
            print(f"[document_chunker] text batch failed for case {case_id}: {type(e).__name__}")
    report.pages_indexed = len(indexed_pages)
    _finish_swap(case_id, report, new_ids, old_ids)
    if report.failed_pages:
        report.failed_pages = sorted(set(report.failed_pages))
    return report


def chunk_text_into_pages(case_text: str, case_id: str, chunk_size: int = 1000, overlap: int = 150, force: bool = False,
                          wait: bool = False) -> int:
    """Backward-compatible wrapper used by the request path: returns the number of chunks now indexed for the case
    (0 on failure, or when another indexer is already working on this case - it never blocks the request)."""
    report = index_case_text(case_text, case_id, force=force, wait=wait)
    return report.chunks_inserted


# ---------------------------------------------------------------- public: PDF path

def _try_ocr(file_path: str, page_number: int) -> str:
    try:
        import pytesseract
        from pdf2image import convert_from_path
        images = convert_from_path(file_path, first_page=page_number, last_page=page_number, dpi=200)
        if images:
            return pytesseract.image_to_string(images[0])
    except Exception:
        pass
    return ""


def index_pdf(file_path: str, case_id: str) -> IndexReport:
    """Indexes a PDF page by page (real page numbers), splitting long pages into <=MAX_CHUNK_CHARS chunks."""
    with _case_index_lock(case_id, wait=True) as got:
        if not got:
            return IndexReport(source="pdf", error="index_in_progress")
        return _index_pdf_locked(file_path, case_id)


def _index_pdf_locked(file_path: str, case_id: str) -> IndexReport:
    report = IndexReport(source="pdf")
    try:
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
    except Exception as e:
        report.error = f"pdf_unreadable:{type(e).__name__}"
        print(f"[document_chunker] PdfReader failed to open file for case {case_id}: {type(e).__name__}")
        return report

    report.total_pages = total_pages
    old_ids = _safe_old_ids(case_id)
    new_ids: list[str] = []

    for batch_start in range(0, total_pages, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_pages)
        batch_chunks: list[tuple[int, str]] = []
        batch_pages: set[int] = set()

        for i in range(batch_start, batch_end):
            page_number = i + 1
            try:
                text = reader.pages[i].extract_text() or ""
            except Exception:
                text = ""
            if len(text.strip()) < MIN_PAGE_TEXT_CHARS:
                ocr_text = _try_ocr(file_path, page_number)
                if len(ocr_text.strip()) >= MIN_PAGE_TEXT_CHARS:
                    text = ocr_text
                    report.ocr_pages += 1
            if len(text.strip()) < MIN_PAGE_TEXT_CHARS:
                continue            # genuinely blank / unreadable page: not a failure, not counted as text
            page_chunks = _dedupe([(page_number, c) for c in split_text_into_chunks(text)])
            if page_chunks:
                batch_chunks.extend(page_chunks)
                batch_pages.add(page_number)

        report.pages_with_text += len(batch_pages)
        report.chunks_expected += len(batch_chunks)
        if not batch_chunks:
            continue
        try:
            new_ids.extend(_insert_batch(case_id, batch_chunks))
            report.chunks_inserted += len(batch_chunks)
            report.pages_indexed += len(batch_pages)
        except Exception as e:
            report.failed_pages.extend(sorted(batch_pages))
            report.error = f"{type(e).__name__}"
            print(f"[document_chunker] pages {batch_start + 1}-{batch_end} failed for case {case_id}: {type(e).__name__}")

    _finish_swap(case_id, report, new_ids, old_ids)
    return report


def chunk_and_index_pdf(file_path: str, case_id: str) -> int:
    """Backward-compatible wrapper: returns the number of PAGES indexed."""
    return index_pdf(file_path, case_id).pages_indexed


# ---------------------------------------------------------------- case-row bookkeeping

def record_index_result(case_id: str, report: IndexReport, total_pages_hint: int = 0) -> str:
    """Writes the outcome to the cases row and returns the status written ('ready' | 'failed').

    'ready' means at least one chunk is searchable. Whether EVERY page was indexed is carried separately in
    index_report.complete so the UI contract (status values) is unchanged. The extra columns are optional:
    if the proposed migration has not been applied the update is retried without them."""
    client = get_supabase_client()
    searchable = report.chunks_inserted > 0 or report.skipped_existing or report.kept_previous_index
    if searchable:
        base = {
            "status": "ready",
            "pages_processed": report.pages_indexed,
            "total_pages": max(report.total_pages, total_pages_hint, report.pages_indexed),
        }
    else:
        base = {
            "status": "failed",
            "rejection_reason": "No text chunks could be extracted or indexed from the document.",
        }
    try:
        client.table("cases").update({**base, "index_report": report.to_dict()}).eq("id", case_id).execute()
    except Exception:
        try:
            client.table("cases").update(base).eq("id", case_id).execute()
        except Exception as e:
            print(f"[document_chunker] could not record index result for {case_id}: {type(e).__name__}")
    return base["status"]
