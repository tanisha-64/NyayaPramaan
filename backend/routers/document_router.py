"""
Document Router.

1. Classification runs on the FULL extracted text (not a short preview), so genuine scanned/old judgments are
   not falsely rejected.
2. Heavy page-by-page chunking/embedding runs as a background task so large documents respond fast.
3. Summary + timeline are generated synchronously (one LLM call each) so the user gets a usable response quickly.
4. Every route that touches a case proves the caller owns it BEFORE reading or deleting anything
   (the backend uses the service-role key, which bypasses RLS).
"""
import os
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.concurrency import run_in_threadpool

from ai_core.rag.document_reader import read_case_file_with_gemini, ocr_pdf_sample, NO_TEXT_MESSAGE
from ai_core.rag.summarizer import summarize_case
from ai_core.timeline.extractor import extract_timeline
from ai_core.rag.vector_store import get_supabase_client, invalidate_case_cache
from ai_core.rag.document_chunker import index_pdf, index_case_text, record_index_result, IndexReport
from ai_core.rag.document_classifier import classify_document, REJECTION_MESSAGE
from backend.db.supabase_storage import upload_case_file
from backend.auth.supabase_auth import get_current_user
from backend.rate_limit import limit_user
from backend.security import (
    get_owned_case, clean_uuid, validate_upload, safe_filename, max_upload_bytes, max_cases_per_user,
)

router = APIRouter()

STALE_PROCESSING_MINUTES = int(os.getenv("STALE_PROCESSING_MINUTES", "30"))
STALE_MESSAGE = "Indexing did not finish (the server may have restarted). Please re-upload or re-index the document."


def _background_index_pages(tmp_path: str, case_id: str, suffix: str, case_text: str = "", force: bool = False):
    """Runs AFTER the response has been sent -- indexes pages for Q&A and records an honest status."""
    try:
        report = IndexReport()
        if suffix.lower() == ".pdf":
            report = index_pdf(tmp_path, case_id)
            # Scanned PDF where local extraction/OCR produced nothing: fall back to the extracted text.
            if report.chunks_inserted == 0 and not report.kept_previous_index and case_text.strip():
                fallback = index_case_text(case_text, case_id, force=force)
                fallback.total_pages = max(fallback.total_pages, report.total_pages)
                report = fallback
        elif case_text.strip():
            report = index_case_text(case_text, case_id, force=force)
        else:
            report.error = "empty_text"

        if report.error == "index_in_progress":
            print(f"[INDEX_RESULT] case_id={case_id} status=deferred reason=index_in_progress")
            return        # another indexer is working on this case and will record the outcome
        status = record_index_result(case_id, report, total_pages_hint=report.total_pages)
        print(f"[INDEX_RESULT] case_id={case_id} status={status} report={report.to_dict()}")
    except Exception as e:
        print(f"[document_router] Background indexing failed for {case_id}: {type(e).__name__}")
        try:
            get_supabase_client().table("cases").update({
                "status": "failed",
                "rejection_reason": "Indexing failed unexpectedly. Please re-upload the document.",
            }).eq("id", case_id).execute()
        except Exception:
            pass
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def _remove_quietly(path: str | None):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def _process_upload(background_tasks: BackgroundTasks, raw_filename, file_bytes: bytes, user):
    """Blocking part of an upload (Supabase, LLM, file IO). Runs in a worker thread so it cannot stall the event loop."""
    tmp_path = None
    handed_to_background = False
    try:
        suffix = validate_upload(raw_filename, file_bytes)
        filename = safe_filename(raw_filename)

        client = get_supabase_client()
        try:
            owned = client.table("cases").select("id", count="exact").eq("user_id", user.id).limit(1).execute()
            if isinstance(owned.count, int) and owned.count >= max_cases_per_user():
                raise HTTPException(status_code=429, detail="Document limit reached. Please delete older documents first.")
        except HTTPException:
            raise
        except Exception:
            pass   # quota lookup must never block an upload

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # 1. Read document text
        case_text = read_case_file_with_gemini(tmp_path)
        if case_text == NO_TEXT_MESSAGE:
            if suffix != ".pdf":
                raise HTTPException(status_code=422, detail="No readable text could be extracted from this file.")
            case_text = ""       # scanned PDF: local OCR during indexing may still recover it; never store the placeholder as content

        # 2. Classify the document's CONTENT. A scan with no text layer is sampled with local OCR so it can still be
        #    judged on what it says; if nothing readable comes out, it is rejected rather than guessed from its name.
        classify_text = case_text
        if not classify_text.strip() and suffix == ".pdf":
            classify_text = ocr_pdf_sample(tmp_path)
        classification = classify_document(classify_text, filename=filename)
        if not classification["is_legal_relevant"]:
            print(f"[document_router] upload rejected: decision={classification['decision']} reason={classification['reason']}")
            raise HTTPException(status_code=422, detail=classification.get("message") or REJECTION_MESSAGE)

        # 3. Store file + create case record with explicit processing status
        file_url = upload_case_file(file_bytes, filename)
        result = client.table("cases").insert({
            "user_id": user.id,
            "filename": filename,
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
            timeline = extract_timeline(case_text)     # deterministic, evidence-linked (date + sentence + page)
        except Exception:
            timeline = ""

        client.table("cases").update({"summary": summary}).eq("id", case_id).execute()
        if timeline:
            try:    # the `timeline` column predates this change in some deployments; never fail an upload over it
                client.table("cases").update({"timeline": timeline}).eq("id", case_id).execute()
            except Exception:
                pass

        # 5. Background indexing with status tracking (the task removes the temp file)
        background_tasks.add_task(_background_index_pages, tmp_path, case_id, suffix, case_text)
        handed_to_background = True

        return {
            "case_id": case_id,
            "file_url": file_url,
            "filename": filename,
            "summary": summary,
            "timeline": timeline,
            "document_type": classification["document_type"],
            "status": "processing",
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[document_router ERROR] upload_case failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Document processing error. Please try again.")
    finally:
        if not handed_to_background:
            _remove_quietly(tmp_path)


@router.post("/upload")
async def upload_case(background_tasks: BackgroundTasks, file: UploadFile = File(...), user=Depends(limit_user("upload"))):
    file_bytes = await file.read(max_upload_bytes() + 1)      # never buffer more than limit+1 bytes
    return await run_in_threadpool(_process_upload, background_tasks, file.filename, file_bytes, user)


def _is_stale(created_at) -> bool:
    try:
        ts = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - ts).total_seconds() > STALE_PROCESSING_MINUTES * 60
    except (ValueError, TypeError):
        return False


@router.get("/{case_id}/status")
def get_document_status(case_id: str, user=Depends(get_current_user)):
    client = get_supabase_client()
    cid = clean_uuid(case_id)
    result = (client.table("cases").select("status, summary, pages_processed, total_pages, rejection_reason, created_at")
              .eq("id", cid).eq("user_id", user.id).execute())
    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")
    row = result.data[0]
    status = row.get("status") or "ready"
    reason = row.get("rejection_reason")

    # A background task killed by a restart would otherwise leave the document 'processing' forever.
    if status == "processing" and _is_stale(row.get("created_at")):
        status, reason = "failed", STALE_MESSAGE
        try:
            client.table("cases").update({"status": status, "rejection_reason": reason}).eq("id", cid).eq("user_id", user.id).execute()
        except Exception:
            pass

    def optional_column(column):
        """Columns that may not exist in every deployment (added by later migrations): absent => None."""
        try:
            res = client.table("cases").select(column).eq("id", cid).eq("user_id", user.id).execute()
            return res.data[0].get(column) if res.data and isinstance(res.data[0], dict) else None
        except Exception:
            return None

    index_report = optional_column("index_report")
    index_report = index_report if isinstance(index_report, dict) else None
    timeline = (row.get("timeline") or optional_column("timeline") or "") if status == "ready" else ""

    # 'ready' means searchable. Whether EVERY page with text was indexed is reported separately, so a partial index is
    # never presented as complete.
    indexing_complete = index_report.get("complete") if index_report else None
    index_warning = None
    if status == "ready" and indexing_complete is False:
        index_warning = (f"Only {index_report.get('pages_indexed', 0)} of {index_report.get('pages_with_text', 0)} pages "
                         f"with text were indexed; answers may miss content. Use re-index to retry.")

    return {
        "status": status,
        "summary": row.get("summary") or "",
        "timeline": timeline,
        "pages_processed": row.get("pages_processed") or 0,
        "total_pages": row.get("total_pages") or 0,
        "rejection_reason": reason,
        "index_report": index_report,
        "indexing_complete": indexing_complete,
        **({"index_warning": index_warning} if index_warning else {}),
    }


@router.post("/{case_id}/reindex")
def reindex_document(case_id: str, background_tasks: BackgroundTasks, user=Depends(limit_user("reindex"))):
    """Rebuilds the search index from the stored text. Safe: the existing index is replaced only on success."""
    client = get_supabase_client()
    case = get_owned_case(client, case_id, user.id, columns="id, case_text")
    if not (case.get("case_text") or "").strip():
        raise HTTPException(status_code=422, detail="No stored text is available to re-index. Please re-upload the document.")
    client.table("cases").update({"status": "processing"}).eq("id", case["id"]).eq("user_id", user.id).execute()
    background_tasks.add_task(_background_index_pages, "", case["id"], ".txt", case["case_text"], True)
    return {"case_id": case["id"], "status": "processing"}


@router.delete("/{case_id}")
def delete_document(case_id: str, user=Depends(get_current_user)):
    client = get_supabase_client()
    case = get_owned_case(client, case_id, user.id)      # ownership BEFORE any destructive call
    cid = case["id"]
    client.table("document_chunks").delete().eq("case_id", cid).execute()
    client.table("session_documents").delete().eq("case_id", cid).execute()
    client.table("cases").delete().eq("id", cid).eq("user_id", user.id).execute()
    invalidate_case_cache(cid)
    return {"deleted": cid}
