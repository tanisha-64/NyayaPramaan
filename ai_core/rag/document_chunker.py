"""
Document Chunker — processes pages in batches (batch-embedding = fast),
falls back to free local OCR when pypdf extraction is empty (scanned pages),
supports cooperative cancellation (checks case status before each batch),
and updates live progress counters (pages_processed / total_pages) in the
cases table so the frontend can show "Processing 87/152 pages".
"""
from pypdf import PdfReader
from ai_core.rag.embeddings import embed_texts_batch
from ai_core.rag.vector_store import insert_document_chunks_batch, get_case_status, get_supabase_client
from ai_core.rag.ocr_fallback import ocr_page

BATCH_SIZE = 20


def _update_progress(case_id: str, pages_processed: int, total_pages: int):
    """Update live progress counters in the cases table."""
    try:
        client = get_supabase_client()
        client.table("cases").update({
            "pages_processed": pages_processed,
            "total_pages": total_pages,
        }).eq("id", case_id).execute()
    except Exception as e:
        # Progress update failure is non-fatal — processing continues
        print(f"[document_chunker] Progress update failed for {case_id}: {e}")


def chunk_and_index_pdf(file_path: str, case_id: str) -> int:
    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    pages_indexed = 0

    # Set initial total so frontend knows the denominator immediately
    _update_progress(case_id, 0, total_pages)

    for batch_start in range(0, total_pages, BATCH_SIZE):
        # Cooperative cancellation check
        if get_case_status(case_id) == "cancelled":
            print(f"[document_chunker] Case {case_id} cancelled, stopping indexing.")
            return pages_indexed

        batch_end = min(batch_start + BATCH_SIZE, total_pages)
        batch_pages: list[tuple[int, str]] = []

        for i in range(batch_start, batch_end):
            page_number = i + 1
            try:
                text = reader.pages[i].extract_text() or ""
            except Exception:
                text = ""

            if len(text.strip()) < 20:
                # Scanned or image-only page -- free local OCR fallback, no API call
                text = ocr_page(file_path, page_number)

            if len(text.strip()) >= 20:
                batch_pages.append((page_number, text))

        if batch_pages:
            texts = [t for (_, t) in batch_pages]
            try:
                embeddings = embed_texts_batch(texts)
                insert_document_chunks_batch(case_id, batch_pages, embeddings)
                pages_indexed += len(batch_pages)
            except Exception as e:
                print(f"[document_chunker] Batch {batch_start}-{batch_end} failed: {e}")
                continue

        # Update progress after each batch so frontend shows live page count
        _update_progress(case_id, min(batch_end, total_pages), total_pages)

    return pages_indexed


def get_document_preview(file_path: str, max_chars: int = 1500) -> str:
    """Fast preview extraction for classification without full-document parsing."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for idx, page in enumerate(reader.pages[:5]):
            page_text = page.extract_text() or ""
            if len(page_text.strip()) < 20:
                page_text = ocr_page(file_path, idx + 1)
            text += " " + page_text
            if len(text) >= max_chars:
                break
        return text[:max_chars].strip()
    except Exception as e:
        print(f"[document_chunker] preview extraction fallback: {e}")
        return ""