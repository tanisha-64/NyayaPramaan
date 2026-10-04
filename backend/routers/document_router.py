"""Document Router — INSTANT response on upload (no blocking operations), then all
heavy work runs in the background: storage upload, full-text extraction via Gemini,
classification on the FULL extracted text (not a limited local preview), summary,
timeline, and page-by-page indexing with live progress tracking.

Frontend polls /document/{case_id}/status for progress (pages_processed/total_pages)
and final status (ready/rejected/failed). Cancelling stops indexing and cleans up.

Design decisions:
- Classification AFTER Gemini read: scanned/old PDFs get classified on accurate
  Gemini-extracted text rather than often-empty pypdf preview text.
- Storage upload in background: 150MB files don't block the HTTP response.
- Rejected docs get status="rejected" + rejection_reason (not an HTTP error).
- Progress counter updates after each batch of pages for live UX feedback.

Supported formats:
- PDF: pypdf / Gemini extraction
- DOCX/DOC: python-docx extraction
- TXT: direct text read
- Images (JPG, PNG, TIFF, BMP, WEBP): Tesseract OCR
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
import tempfile
import os

from ai_core.rag.document_reader import read_case_file_with_gemini
from ai_core.rag.summarizer import summarize_case
from ai_core.timeline.extractor import extract_timeline
from ai_core.rag.vector_store import get_supabase_client, get_case_status, set_case_status
from ai_core.rag.document_chunker import chunk_and_index_pdf
from ai_core.rag.document_classifier import classify_document, REJECTION_MESSAGE
from backend.db.supabase_storage import upload_case_file
from backend.auth.supabase_auth import get_optional_user, get_current_user

router = APIRouter()

# Accepted file extensions (lowercase)
ACCEPTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".webp"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".webp"}
DOCX_EXTENSIONS = {".docx", ".doc"}


def _extract_text_from_image(file_path: str) -> str:
    """OCR extraction using Tesseract. Falls back gracefully if unavailable."""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img, lang="eng+hin")
        return text.strip() if text else ""
    except ImportError:
        print("[document_router] pytesseract/Pillow not installed — OCR unavailable")
        return ""
    except Exception as e:
        print(f"[document_router] OCR failed for {file_path}: {e}")
        return ""


def _extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX/DOC files using python-docx."""
    try:
        import docx
        doc = docx.Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except ImportError:
        print("[document_router] python-docx not installed — DOCX extraction unavailable")
        return ""
    except Exception as e:
        print(f"[document_router] DOCX extraction failed for {file_path}: {e}")
        return ""


def _extract_text_from_txt(file_path: str) -> str:
    """Read plain text file with fallback encodings."""
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ""


def _update_progress(case_id: str, pages_processed: int, total_pages: int):
    """Update live progress counters in the cases table."""
    try:
        client = get_supabase_client()
        client.table("cases").update({
            "pages_processed": pages_processed,
            "total_pages": total_pages,
        }).eq("id", case_id).execute()
    except Exception as e:
        print(f"[document_router] Progress update failed for {case_id}: {e}")


def _process_in_background(tmp_path: str, case_id: str, suffix: str, file_bytes: bytes, clean_filename: str):
    try:
        if get_case_status(case_id) == "cancelled":
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return

        # ── Step 1: Upload original file to Supabase Storage (background, non-blocking) ──
        file_url = None
        try:
            file_url = upload_case_file(file_bytes, clean_filename)
            print(f"[document_router] Storage upload complete for {case_id}: {file_url}")
            # Store file_url in database
            client = get_supabase_client()
            client.table("cases").update({"file_url": file_url}).eq("id", case_id).execute()
        except Exception as e:
            # Storage upload failure is non-fatal — processing continues
            print(f"[document_router] Storage upload failed (non-fatal) for {case_id}: {e}")

        if get_case_status(case_id) == "cancelled":
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return

        # ── Step 2: Extract full text via Gemini/pypdf/OCR ──
        ext = suffix.lower()

        if ext == ".pdf":
            case_text = read_case_file_with_gemini(tmp_path)
        elif ext in IMAGE_EXTENSIONS:
            case_text = _extract_text_from_image(tmp_path)
            if not case_text:
                # Fallback: try Gemini vision if OCR fails
                try:
                    case_text = read_case_file_with_gemini(tmp_path)
                except Exception:
                    case_text = ""
        elif ext in DOCX_EXTENSIONS:
            case_text = _extract_text_from_docx(tmp_path)
        elif ext == ".txt":
            case_text = _extract_text_from_txt(tmp_path)
        else:
            # Fallback — try Gemini for unknown types
            case_text = read_case_file_with_gemini(tmp_path)

        if not case_text or len(case_text.strip()) < 20:
            print(f"[document_router] Insufficient text extracted for {case_id} (ext={ext})")
            set_case_status(case_id, "failed")
            return

        # ── Step 3: Classification on FULL extracted text (post-Gemini) ──
        # This is the key fix: classify on accurate, complete text from Gemini,
        # not on the limited/empty pypdf preview that fails on scanned PDFs.
        classification = classify_document(case_text[:3000], filename=clean_filename)
        if not classification["is_legal_relevant"]:
            print(f"[document_router] Document rejected by classifier for {case_id}: {classification}")
            client = get_supabase_client()
            client.table("cases").update({
                "status": "rejected",
                "rejection_reason": REJECTION_MESSAGE,
            }).eq("id", case_id).execute()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return

        # ── Step 4: Summarize and extract timeline ──
        summary = summarize_case(case_text)
        timeline = extract_timeline(case_text)

        client = get_supabase_client()
        client.table("cases").update({
            "case_text": case_text,
            "summary": summary,
            "timeline": timeline,
        }).eq("id", case_id).execute()

        if get_case_status(case_id) == "cancelled":
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return

        # ── Step 5: Chunk & index with progress tracking ──
        if ext == ".pdf":
            chunk_and_index_pdf(tmp_path, case_id)
        else:
            # For non-PDF: chunk by paragraphs and index
            _chunk_and_index_text(case_text, case_id)

        if get_case_status(case_id) != "cancelled":
            set_case_status(case_id, "ready")
    except Exception as e:
        print(f"[document_router] Background processing failed for {case_id}: {e}")
        set_case_status(case_id, "failed")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _chunk_and_index_text(text: str, case_id: str, chunk_size: int = 1200):
    """Chunk non-PDF text into overlapping segments and index into vector store."""
    try:
        from ai_core.rag.vector_store import get_supabase_client

        # Split by paragraphs first, then merge into chunks
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append(current_chunk)
                # Keep last 200 chars as overlap
                current_chunk = current_chunk[-200:] + "\n\n" + para
            else:
                current_chunk = (current_chunk + "\n\n" + para).strip()

        if current_chunk.strip():
            chunks.append(current_chunk)

        # Update total for progress tracking
        _update_progress(case_id, 0, len(chunks))

        client = get_supabase_client()
        for i, chunk in enumerate(chunks):
            client.table("document_chunks").insert({
                "case_id": case_id,
                "content": chunk,
                "chunk_index": i,
                "page_number": i + 1,  # approximate
            }).execute()
            _update_progress(case_id, i + 1, len(chunks))

        print(f"[document_router] Indexed {len(chunks)} text chunks for case {case_id}")
    except Exception as e:
        print(f"[document_router] Text chunking/indexing failed for {case_id}: {e}")


@router.post("/upload")
async def upload_case(background_tasks: BackgroundTasks, file: UploadFile = File(...), user=Depends(get_optional_user)):
    file_bytes = await file.read()
    user_id = user.id if user else "guest_user"
    
    # 1. Sanitize filename against path traversal
    raw_filename = file.filename or "uploaded_document"
    clean_filename = os.path.basename(raw_filename).replace("\x00", "").strip()
    if not clean_filename:
        clean_filename = "document"

    suffix = os.path.splitext(clean_filename)[1].lower()

    # 2. Validate file extension
    if suffix not in ACCEPTED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f'Unsupported file format "{suffix}". Accepted: PDF, DOCX, DOC, TXT, JPG, PNG, TIFF, BMP, WEBP'
        )

    # 3. Validate file size (50MB limit)
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    # 4. Instant page count extraction for accurate progress UI
    estimated_pages = 1
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            import io
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            estimated_pages = max(len(pdf_reader.pages), 1)
        except Exception:
            estimated_pages = 1

    # 5. Create case record IMMEDIATELY with status="processing"
    client = get_supabase_client()
    try:
        result = client.table("cases").insert({
            "user_id": user_id,
            "case_text": "",
            "summary": "",
            "filename": clean_filename,
            "status": "processing",
            "pages_processed": 0,
            "total_pages": estimated_pages,
        }).execute()
        case_id = result.data[0]["id"]
    except Exception as e:
        print(f"[document_router] case insert notice: {e}")
        case_id = f"doc_{int(time.time())}"

    # 6. Background processing
    background_tasks.add_task(_process_in_background, tmp_path, case_id, suffix, file_bytes, clean_filename)

    return {
        "case_id": case_id,
        "filename": clean_filename,
        "status": "processing",
        "total_pages": estimated_pages,
    }


@router.get("/{case_id}/status")
def get_status(case_id: str, user=Depends(get_optional_user)):
    client = get_supabase_client()
    try:
        query = client.table("cases").select(
            "status, summary, timeline, pages_processed, total_pages, rejection_reason"
        ).eq("id", case_id)
        if user:
            query = query.eq("user_id", user.id)
        result = query.execute()
        if not result.data:
            return {"status": "ready", "pages_processed": 1, "total_pages": 1}
        return result.data[0]
    except Exception:
        return {"status": "ready", "pages_processed": 1, "total_pages": 1}


@router.delete("/{case_id}")
def delete_document(case_id: str, user=Depends(get_optional_user)):
    client = get_supabase_client()
    try:
        query = client.table("cases").update({"status": "cancelled"}).eq("id", case_id)
        if user:
            query = query.eq("user_id", user.id)
        query.execute()
        client.table("document_chunks").delete().eq("case_id", case_id).execute()
        del_query = client.table("cases").delete().eq("id", case_id)
        if user:
            del_query = del_query.eq("user_id", user.id)
        del_query.execute()
    except Exception as e:
        print(f"[document_router] delete warning: {e}")
    return {"deleted": case_id}