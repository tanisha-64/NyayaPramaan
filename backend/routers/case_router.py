from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from ai_core.rag.vector_store import get_supabase_client, invalidate_case_cache
from ai_core.timeline.extractor import extract_timeline
from ai_core.llm_gateway import call_llm
from ai_core.rag.summarizer import prepare_text_for_llm
from backend.auth.supabase_auth import get_current_user
from backend.rate_limit import limit_user
from backend.security import get_owned_case, clean_uuid

router = APIRouter()


MAX_NOTES_CHARS = 20000


class NotesPayload(BaseModel):
    notes: str = Field(max_length=MAX_NOTES_CHARS)


@router.get("/list")
def list_cases(user=Depends(get_current_user)):
    client = get_supabase_client()
    result = (client.table("cases").select("id, summary, filename, status, created_at")
              .eq("user_id", user.id).order("created_at", desc=True).execute())
    return result.data


@router.get("/{case_id}")
def get_case(case_id: str, user=Depends(get_current_user)):
    client = get_supabase_client()
    result = client.table("cases").select("*").eq("id", clean_uuid(case_id)).eq("user_id", user.id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Case not found")
    case = result.data[0]
    if not case.get("timeline") and case.get("case_text"):
        case["timeline"] = extract_timeline(case["case_text"])
    return case


@router.put("/{case_id}/notes")
def save_case_notes(case_id: str, payload: NotesPayload, user=Depends(get_current_user)):
    client = get_supabase_client()
    result = client.table("cases").update({"notes": payload.notes}).eq("id", clean_uuid(case_id)).eq("user_id", user.id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"status": "success", "notes": payload.notes}


@router.get("/{case_id}/brief")
def generate_case_brief(case_id: str, user=Depends(limit_user("brief"))):     # one LLM call per request: rate-limited
    client = get_supabase_client()
    result = client.table("cases").select("*").eq("id", clean_uuid(case_id)).eq("user_id", user.id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Case not found")
    case = result.data[0]
    case_text = (case.get("case_text") or "").replace(chr(12), chr(10))
    if not case_text or len(case_text.strip()) < 50:
        return {
            "title": case.get("filename", "Case Brief"),
            "summary": case.get("summary", "No text available for analysis."),
            "facts": "Document processing or insufficient text.",
            "issues": "None identified.",
            "statutes": "None identified.",
            "ratio": "N/A",
            "holding": "N/A",
        }

    prompt = f"""You are a senior Indian High Court advocate. Generate an executive Legal Case Brief for the following case text.
Structure your response in strict Markdown format with the following headings:

# CASE BRIEF: [Case Name or File Name]

## 1. Executive Summary
[2-3 sentences concise summary]

## 2. Material Facts
[Chronological bullet points of key facts]

## 3. Core Legal Issues Framed
[Legal questions for determination]

## 4. Statutory Provisions & Sections Invoked
[List of relevant IPC, BNS, CrPC, BNSS, CPC, Constitution, or Specific Acts]

## 5. Ratio Decidendi & Legal Analysis
[The core principle and court's reasoning]

## 6. Operative Order & Holding
[Final disposition, relief granted/dismissed]

CASE TEXT:
{prepare_text_for_llm(case_text)[:6000]}
"""
    try:
        brief_markdown = call_llm("groq/openai/gpt-oss-20b", prompt)
    except Exception:
        brief_markdown = f"# CASE BRIEF: {case.get('filename')}\n\n## Summary\n{case.get('summary', 'Summary unavailable.')}"

    return {
        "case_id": case_id,
        "filename": case.get("filename", "Case Brief"),
        "brief_markdown": brief_markdown,
        "timeline": case.get("timeline") or extract_timeline(case_text)
    }


@router.delete("/clear/all")
def clear_all_cases(user=Depends(get_current_user)):
    client = get_supabase_client()
    user_cases = client.table("cases").select("id").eq("user_id", user.id).execute().data or []
    case_ids = [c["id"] for c in user_cases]
    if case_ids:
        client.table("document_chunks").delete().in_("case_id", case_ids).execute()
        client.table("session_documents").delete().in_("case_id", case_ids).execute()
        client.table("cases").delete().eq("user_id", user.id).execute()
        for _cid in case_ids:
            invalidate_case_cache(_cid)
    return {"status": "success", "cleared_count": len(case_ids)}


@router.delete("/{case_id}")
def delete_case(case_id: str, user=Depends(get_current_user)):
    client = get_supabase_client()
    cid = get_owned_case(client, case_id, user.id)["id"]     # ownership BEFORE any destructive call
    client.table("document_chunks").delete().eq("case_id", cid).execute()
    client.table("session_documents").delete().eq("case_id", cid).execute()
    client.table("cases").delete().eq("id", cid).eq("user_id", user.id).execute()
    invalidate_case_cache(cid)
    return {"deleted": cid}
