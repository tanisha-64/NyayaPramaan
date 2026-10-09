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


def chunk_text_into_pages(case_text: str, case_id: str, chunk_size: int = 1000, overlap: int = 150) -> int:
    """
    Fallback chunker for scanned PDFs/un-indexed documents using extracted case_text.
    Idempotent: safely checks if chunks already exist to avoid creating duplicate rows.
    """
    if not case_text or not case_text.strip() or not case_id:
        return 0

    from ai_core.rag.vector_store import get_supabase_client
    try:
        client = get_supabase_client()
        existing = client.table("document_chunks").select("id").eq("case_id", case_id).limit(1).execute()
        if existing.data and len(existing.data) > 0:
            # Already indexed -- do not duplicate!
            return len(existing.data)
    except Exception as e_check:
        print(f"[document_chunker] Chunks existence check skipped: {e_check}")
    
    text = case_text.strip()
    chunks = []
    
    # Check if text contains explicit page markers like '[Page X]' or 'Page X of Y'
    import re
    page_splits = re.split(r'(?:\[Page\s*(\d+)\]|--- Page\s*(\d+)\s*---|Page\s+(\d+)\s+of\s+\d+)', text, flags=re.IGNORECASE)
    
    if len(page_splits) > 3:
        # Structured pages found
        current_page = 1
        for section in page_splits:
            if not section:
                continue
            if section.isdigit():
                current_page = int(section)
            else:
                section_text = section.strip()
                if not section_text:
                    continue
                # Split section into chunks if too long
                for i in range(0, len(section_text), chunk_size - overlap):
                    chunk_slice = section_text[i:i + chunk_size].strip()
                    if len(chunk_slice) >= 30:
                        chunks.append((current_page, chunk_slice))
    else:
        # Natural language split by paragraphs or sliding window with approximate page estimation (~1800 chars per page)
        raw_paras = [p.strip() for p in re.split(r'\n{2,}|\n', text) if p.strip()]
        current_chunk = ""
        current_char_offset = 0

        for para in raw_paras:
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                page_est = max(1, (current_char_offset // 1800) + 1)
                chunks.append((page_est, current_chunk.strip()))
                # keep overlap from end of current_chunk
                current_chunk = current_chunk[-overlap:] + " " + para if overlap > 0 else para
            else:
                current_chunk = (current_chunk + " " + para).strip()
            current_char_offset += len(para)

        if current_chunk.strip():
            page_est = max(1, (current_char_offset // 1800) + 1)
            chunks.append((page_est, current_chunk.strip()))

    if not chunks:
        return 0

    texts = [t for (_, t) in chunks]
    try:
        embeddings = embed_texts_batch(texts)
        insert_document_chunks_batch(case_id, chunks, embeddings)
        
        # Update case status to ready
        try:
            max_page = max(p for (p, _) in chunks) if chunks else 1
            client.table("cases").update({
                "status": "ready",
                "pages_processed": len(chunks),
                "total_pages": max_page
            }).eq("id", case_id).execute()
        except Exception:
            pass

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
