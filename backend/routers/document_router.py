"""
Document Router — FAST classification via a small page-preview slice (no full-document
read needed just to classify), then returns immediately with status="processing" while the
heavy work (full read, summary, timeline, page-by-page indexing) runs in the background.
Frontend polls /document/{case_id}/status. Cancelling stops indexing and cleans up.
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


def _quick_preview_text(tmp_path: str, suffix: str) -> str:
    """Fast preview for classification without waiting for a full document read."""
    if suffix.lower() == ".pdf":
        return get_document_preview(tmp_path)
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

        case_text = read_case_file_with_gemini(tmp_path)
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

        if suffix.lower() == ".pdf":
            chunk_and_index_pdf(tmp_path, case_id)

        if get_case_status(case_id) != "cancelled":
            set_case_status(case_id, "ready")
    except Exception as e:
        print(f"[document_router] Background processing failed for {case_id}: {e}")
        set_case_status(case_id, "failed")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/upload")
async def upload_case(background_tasks: BackgroundTasks, file: UploadFile = File(...), user=Depends(get_current_user)):
    file_bytes = await file.read()
    suffix = os.path.splitext(file.filename)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    # FAST classification (local pypdf/OCR preview, no full-document API call)
    preview_text = _quick_preview_text(tmp_path, suffix)
    classification = classify_document(preview_text, filename=file.filename)
    if not classification["is_legal_relevant"]:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(status_code=422, detail=REJECTION_MESSAGE)

    file_url = upload_case_file(file_bytes, file.filename)

    client = get_supabase_client()
    result = client.table("cases").insert({
        "user_id": user.id,
        "case_text": "",
        "summary": "",
        "filename": file.filename,
        "status": "processing",
    }).execute()
    case_id = result.data[0]["id"]

    background_tasks.add_task(_process_in_background, tmp_path, case_id, suffix)

    return {
        "case_id": case_id,
        "file_url": file_url,
        "filename": file.filename,
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