"""
Document Chunker — batch-embeds pages (1 API call per ~20 pages, not per
page) for speed, with OCR fallback and Gemini full-text fallback for scanned
pages that pypdf can't extract text from.
"""
from pypdf import PdfReader
from ai_core.rag.embeddings import embed_texts_batch
from ai_core.rag.vector_store import insert_document_chunks_batch

BATCH_SIZE = 20


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


def chunk_text_into_pages(case_text: str, case_id: str, chunk_size: int = 1500) -> int:
    """Fallback chunker for scanned PDFs where local pypdf extracted 0 text, using Gemini extracted case_text."""
    if not case_text or not case_text.strip():
        return 0
    
    text = case_text.strip()
    chunks = []
    # Split by paragraphs or double newlines where possible
    paragraphs = text.split("\n\n")
    current_chunk = ""
    page_num = 1

    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append((page_num, current_chunk.strip()))
            page_num += 1
            current_chunk = para + "\n\n"
        else:
            current_chunk += para + "\n\n"

    if current_chunk.strip():
        chunks.append((page_num, current_chunk.strip()))

    if not chunks:
        return 0

    texts = [t for (_, t) in chunks]
    try:
        embeddings = embed_texts_batch(texts)
        insert_document_chunks_batch(case_id, chunks, embeddings)
        return len(chunks)
    except Exception as e:
        print(f"[document_chunker] chunk_text_into_pages failed for {case_id}: {e}")
        return 0


def chunk_and_index_pdf(file_path: str, case_id: str) -> int:
    try:
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
    except Exception as e:
        print(f"[document_chunker] PdfReader failed to open {file_path}: {e}")
        return 0

    pages_indexed = 0

    for batch_start in range(0, total_pages, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_pages)
        batch_pages: list[tuple[int, str]] = []

        for i in range(batch_start, batch_end):
            page_number = i + 1
            try:
                text = reader.pages[i].extract_text() or ""
            except Exception:
                text = ""

            if len(text.strip()) < 20:
                text = _try_ocr(file_path, page_number)

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

    return pages_indexed
