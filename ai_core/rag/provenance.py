"""
Evidence provenance: where in the original document a retrieved passage came from.

Pages are stored per chunk (document_chunks.page_number). Paragraph numbers are NOT stored anywhere; they are read from
the chunk text itself, where the chunker keeps every explicit paragraph marker ("12. The appellant ...") at the start of
a line. Only markers actually present in the text are reported, so nothing is invented: a chunk that continues a
paragraph begun on an earlier chunk reports no paragraph rather than a guessed one, and consumers say so.
"""
import re

PARA_START = re.compile(r"^\s*\(?(\d{1,3})[.)]\s+\S")
_PARA_START_ML = re.compile(r"(?m)^\s*\(?(\d{1,3})[.)]\s+\S")
SNIPPET_CHARS = 200


def starts_paragraph(unit: str) -> bool:
    return bool(PARA_START.match(unit or ""))


def paragraph_numbers(text: str) -> list[int]:
    """Explicit paragraph numbers whose marker begins a line in the text, in order of appearance, de-duplicated."""
    seen, out = set(), []
    for m in _PARA_START_ML.finditer(text or ""):
        n = int(m.group(1))
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def snippet(text: str, limit: int = SNIPPET_CHARS) -> str:
    flat = re.sub(r"\s+", " ", text or "").strip()
    return flat if len(flat) <= limit else flat[:limit].rsplit(" ", 1)[0] + "…"


def locate(chunk: dict, filename: str | None = None, pages_estimated: bool = False) -> dict:
    """Citation location for one retrieved chunk. Every field comes from stored data or the chunk text."""
    page = chunk.get("page_number")
    paras = paragraph_numbers(chunk.get("chunk_text", ""))
    return {
        "document": filename,
        "page": page,
        "page_estimated": bool(pages_estimated) if page else None,
        "paragraphs": paras,
        "paragraph_note": None if paras else "no explicit paragraph number in this passage",
        "snippet": snippet(chunk.get("chunk_text", "")),
    }
