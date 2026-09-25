"""Document Router — FAST classification via a small page-preview slice (no full-document
read needed just to classify), then returns immediately with status="processing" while the
heavy work (full read, summary, timeline, page-by-page indexing) runs in the background.
Frontend polls /document/{case_id}/status. Cancelling stops indexing and cleans up.

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
from ai_core.rag.document_chunker import chunk_and_index_pdf, get_document_preview
from ai_core.rag.document_classifier import classify_document, REJECTION_MESSAGE
from backend.db.supabase_storage import upload_case_file
from backend.auth.supabase_auth import get_current_user

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


def _quick_preview_text(tmp_path: str, suffix: str) -> str:
    """Fast preview for classification without waiting for a full document read."""
    ext = suffix.lower()
    if ext == ".pdf":
        return get_document_preview(tmp_path)
    if ext in IMAGE_EXTENSIONS:
        return _extract_text_from_image(tmp_path)[:1500]
    if ext in DOCX_EXTENSIONS:
        return _extract_text_from_docx(tmp_path)[:1500]
    # TXT and others — direct read
    try:
        with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(1500)
    except Exception:
        return ""


def _process_in_background(tmp_path: str, case_id: str, suffix: str):
    try:
        if get_case_status(case_id) == "cancelled":
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return

        ext = suffix.lower()

        # Extract text based on file type
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

        # Chunk & index for PDF (page-based chunking)
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

        client = get_supabase_client()
        for i, chunk in enumerate(chunks):
            client.table("document_chunks").insert({
                "case_id": case_id,
                "content": chunk,
                "chunk_index": i,
                "page_number": i + 1,  # approximate
            }).execute()

        print(f"[document_router] Indexed {len(chunks)} text chunks for case {case_id}")
    except Exception as e:
        print(f"[document_router] Text chunking/indexing failed for {case_id}: {e}")


@router.post("/upload")
async def upload_case(background_tasks: BackgroundTasks, file: UploadFile = File(...), user=Depends(get_current_user)):
    file_bytes = await file.read()
    
    # 1. Sanitize filename against path traversal (e.g. ../../etc/passwd)
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

    # 4. FAST classification (local pypdf/OCR preview, no full-document API call)
    preview_text = _quick_preview_text(tmp_path, suffix)
    classification = classify_document(preview_text, filename=clean_filename)
    if not classification["is_legal_relevant"]:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise HTTPException(status_code=422, detail=REJECTION_MESSAGE)

    file_url = upload_case_file(file_bytes, clean_filename)

    client = get_supabase_client()
    result = client.table("cases").insert({
        "user_id": user.id,
        "case_text": "",
        "summary": "",
        "filename": clean_filename,
        "status": "processing",
    }).execute()
    case_id = result.data[0]["id"]

    background_tasks.add_task(_process_in_background, tmp_path, case_id, suffix)

    return {
        "case_id": case_id,
        "file_url": file_url,
        "filename": clean_filename,
        "status": "processing",
        "document_type": classification["document_type"],
    }


@router.get("/{case_id}/status")
def get_status(case_id: str, user=Depends(get_current_user)):
    client = get_supabase_client()
    result = client.table("cases").select("status, summary, timeline").eq("id", case_id).eq("user_id", user.id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Case not found")
    return result.data[0]


@router.delete("/{case_id}")
def delete_document(case_id: str, user=Depends(get_current_user)):
    client = get_supabase_client()
    # Mark cancelled FIRST so any running background worker exits quickly
    client.table("cases").update({"status": "cancelled"}).eq("id", case_id).eq("user_id", user.id).execute()
    client.table("document_chunks").delete().eq("case_id", case_id).execute()
    client.table("cases").delete().eq("id", case_id).eq("user_id", user.id).execute()
    return {"deleted": case_id}