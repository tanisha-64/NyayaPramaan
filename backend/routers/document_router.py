"""
Document Router — THE CORE FIX:
1. Classification now runs on the FULL Gemini-extracted text (not a short local preview), so genuine scanned/old judgments are no longer falsely rejected.
2. Heavy page-by-page chunking/embedding runs as a background task, so large (100+ page) documents respond fast instead of blocking the request.
3. Summary + timeline are generated synchronously (fast, one Gemini call each) so the user gets a usable response quickly.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
import tempfile
import os

from ai_core.rag.document_reader import read_case_file_with_gemini
from ai_core.rag.summarizer import summarize_case
from ai_core.timeline.extractor import extract_timeline
from ai_core.rag.vector_store import get_supabase_client
from ai_core.rag.document_chunker import chunk_and_index_pdf
from ai_core.rag.document_classifier import classify_document, REJECTION_MESSAGE
from backend.db.supabase_storage import upload_case_file
from backend.auth.supabase_auth import get_current_user

# Naye Domain Gate aur LLM imports
from ai_core.router.domain_gate import is_legal_document
from ai_core.llm_gateway import call_llm

router = APIRouter()

def _background_index_pages(tmp_path: str, case_id: str, suffix: str, case_text: str = ""):
    """Runs AFTER the response has been sent -- indexes pages for Q&A and updates status."""
    client = get_supabase_client()
    try:
        pages_indexed = 0
        total_pages = 0
        if suffix.lower() == ".pdf":
            pages_indexed = chunk_and_index_pdf(tmp_path, case_id)
            try:
                from pypdf import PdfReader
                reader = PdfReader(tmp_path)
                total_pages = len(reader.pages)
            except Exception:
                total_pages = pages_indexed

            # If local pypdf/OCR yielded 0 pages on scanned PDF, fallback to Gemini-extracted text
            if pages_indexed == 0 and case_text and len(case_text.strip()) > 0:
                from ai_core.rag.document_chunker import chunk_text_into_pages
                pages_indexed = chunk_text_into_pages(case_text, case_id)
                total_pages = max(1, pages_indexed)
        elif case_text and len(case_text.strip()) > 0:
            # Non-PDF text fallback chunking (e.g. .txt, .docx)
            from ai_core.rag.document_chunker import chunk_text_into_pages
            pages_indexed = chunk_text_into_pages(case_text, case_id)
            total_pages = max(1, pages_indexed)

        if pages_indexed > 0:
            client.table("cases").update({
                "status": "ready",
                "pages_processed": pages_indexed,
                "total_pages": max(total_pages, pages_indexed)
            }).eq("id", case_id).execute()
        else:
            client.table("cases").update({
                "status": "failed",
                "rejection_reason": "No text chunks could be extracted or indexed from the document."
            }).eq("id", case_id).execute()
    except Exception as e:
        print(f"[document_router] Background indexing failed for {case_id}: {e}")
        try:
            client.table("cases").update({
                "status": "failed",
                "rejection_reason": str(e)
            }).eq("id", case_id).execute()
        except Exception:
            pass
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/upload")
async def upload_case(background_tasks: BackgroundTasks, file: UploadFile = File(...), user=Depends(get_current_user)):
    try:
        file_bytes = await file.read()
        suffix = os.path.splitext(file.filename)[1]

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # 1. Read document text
        case_text = read_case_file_with_gemini(tmp_path)
        
        # ----------------------------------------------------
        # NEW LEGAL DOMAIN GATE CHECK
        # ----------------------------------------------------
        if not case_text or not is_legal_document(case_text, lambda p: call_llm("groq/openai/gpt-oss-20b", p)):
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise HTTPException(
                status_code=422, 
                detail="Only legal documents (judgments, petitions, FIRs, notices, contracts, acts, law assignments) are accepted."
            )

        # 2. Classify on extracted text + filename
        classification = classify_document(case_text[:4000], filename=file.filename)
        if not classification["is_legal_relevant"]:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise HTTPException(status_code=422, detail=REJECTION_MESSAGE)

        # 3. Store file + create case record with explicit processing status
        file_url = upload_case_file(file_bytes, file.filename)
        client = get_supabase_client()
        result = client.table("cases").insert({
            "user_id": user.id,
            "filename": file.filename,
            "case_text": case_text,
            "summary": "",
            "status": "processing",
            "pages_processed": 0,
            "total_pages": 0,
        }).execute()
        case_id = result.data[0]["id"]

        # 4. Fast synchronous summary + timeline
        try:
            summary = summarize_case(case_text)
        except Exception:
            summary = "Summary generation in progress."

        try:
            timeline = extract_timeline(case_text)
        except Exception:
            timeline = ""

        client.table("cases").update({"summary": summary}).eq("id", case_id).execute()

        # 5. Background indexing with status tracking
        background_tasks.add_task(_background_index_pages, tmp_path, case_id, suffix, case_text)

        return {
            "case_id": case_id,
            "file_url": file_url,
            "filename": file.filename,
            "summary": summary,
            "timeline": timeline,
            "document_type": classification["document_type"],
            "status": "processing",
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[document_router ERROR] upload_case failed: {e}")
        raise HTTPException(status_code=500, detail=f"Document processing error: {str(e)}")


@router.get("/{case_id}/status")
def get_document_status(case_id: str, user=Depends(get_current_user)):
    client = get_supabase_client()
    result = client.table("cases").select("status, summary, pages_processed, total_pages, rejection_reason").eq("id", case_id).eq("user_id", user.id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")
    row = result.data[0]
    return {
        "status": row.get("status") or "ready",
        "summary": row.get("summary") or "",
        "timeline": row.get("timeline") or "",
        "pages_processed": row.get("pages_processed") or 0,
        "total_pages": row.get("total_pages") or 0,
        "rejection_reason": row.get("rejection_reason"),
    }


@router.delete("/{case_id}")
def delete_document(case_id: str, user=Depends(get_current_user)):
    client = get_supabase_client()
    owned = client.table("cases").select("id").eq("id", case_id).eq("user_id", user.id).execute()
    if not owned.data:
        raise HTTPException(status_code=404, detail="Document not found")
    client.table("document_chunks").delete().eq("case_id", case_id).execute()
    client.table("cases").delete().eq("id", case_id).eq("user_id", user.id).execute()
    return {"deleted": case_id}