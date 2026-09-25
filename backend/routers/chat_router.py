"""
Chat Router — supports MULTIPLE attached documents per conversation (persisted via session_documents),
never falls back to general knowledge when documents are attached (strict, citation-only, no hallucination in document mode),
and rejects queries against documents that aren't "ready" yet (no premature/incomplete answers).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ai_core.guardrails.input_guard import check_input_safety
from ai_core.guardrails.output_guard import redact_pii
from ai_core.router.adaptive_router import choose_model
from ai_core.router.intent_classifier import classify_intent, REFUSAL_MESSAGE, AUDIENCE_INSTRUCTIONS
from ai_core.rag.embeddings import embed_text
from ai_core.rag.vector_store import (
    search_knowledge_base,
    search_document_chunks_multi,
    get_supabase_client,
    get_case_status,
)
from ai_core.rag.crag_corrector import is_retrieval_sufficient, corrective_web_search
from ai_core.rag.self_rag import self_reflect
from ai_core.llm_gateway import call_llm
from ai_core.trustagent.claim_extractor import extract_claims
from ai_core.trustagent.verifier import verify_claims_batch, summarize_verdicts
from ai_core.evaluation.llm_judge import judge_answer
from ai_core.trustagent.corrector import suggest_department_and_helpline
from trust_log.hash_chain import build_log_entry, get_last_hash, save_log_entry
from backend.auth.supabase_auth import get_current_user

router = APIRouter()

LANGUAGE_INSTRUCTION = "Detect whether the question is in English, Hindi, or Hinglish and respond in the SAME language/style."
LENGTH_INSTRUCTION = "Match answer length to complexity: short and direct for simple questions, fuller (bullet points if listing multiple sections/penalties) for complex ones."

VERDICT_LABEL = {
    "supported": "verified",
    "partially_supported": "partial",
    "contradicted": "contradicted",
    "unverified": "unverified",
}


class QueryRequest(BaseModel):
    query: str
    case_ids: list[str] = []
    case_id: str | None = None
    session_id: str | None = None


def general_legal_answer(query: str, model: str, audience: str, history: str = "") -> str:
    history_section = (
        f"PREVIOUS MESSAGES (context only, never invent beyond this):\n{history}\n"
        if history else "(First message in this chat — no earlier context.)\n"
    )
    prompt = f"""You are an Indian legal intelligence assistant (covering IPC, BNS, CrPC, BNSS, CPC, Constitution, and court procedure).
{LANGUAGE_INSTRUCTION}
{LENGTH_INSTRUCTION}
{AUDIENCE_INSTRUCTIONS[audience]}

{history_section}

INSTRUCTIONS:
- Directly provide a factually accurate, structured legal answer.
- Do NOT add repetitive robotic introductions or disclaimers about being an AI.
- Cite exact section numbers where applicable.

QUESTION: {query}

ANSWER:"""
    return call_llm(model, prompt)


def generate_suggestions(query: str, answer: str, model: str) -> list[str]:
    prompt = f"""Suggest 3 short follow-up legal questions. ONLY a JSON array of 3 strings.
Q: {query}
A: {answer[:200]}
JSON:"""
    try:
        raw = call_llm(model, prompt)
        import json, re
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
        s = json.loads(cleaned)
        return s if isinstance(s, list) else []
    except Exception:
        return []


def get_recent_history(session_id: str | None, limit: int = 4) -> str:
    if not session_id:
        return ""
    client = get_supabase_client()
    try:
        result = (
            client.table("chat_messages")
            .select("role, content")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        msgs = list(reversed(result.data))
        return "\n".join(f"{m['role'].upper()}: {m['content'][:150]}" for m in msgs)
    except Exception:
        return ""


def ensure_valid_session(session_id: str | None, user_id: str, fallback_title: str) -> str:
    client = get_supabase_client()
    if session_id:
        result = client.table("chat_sessions").select("id, user_id").eq("id", session_id).execute()
        if result.data and result.data[0]["user_id"] == user_id:
            return session_id
    new_session = client.table("chat_sessions").insert({
        "user_id": user_id,
        "title": fallback_title[:40],
    }).execute()
    return new_session.data[0]["id"]


def save_message(session_id: str | None, role: str, content: str, sources: list | None = None):
    if not session_id:
        return
    client = get_supabase_client()
    client.table("chat_messages").insert({
        "session_id": session_id,
        "role": role,
        "content": content,
        "sources": sources or [],
    }).execute()
    client.table("chat_sessions").update({"updated_at": "now()"}).eq("id", session_id).execute()


def link_document_to_session(session_id: str | None, case_id: str, filename: str):
    if not session_id or not case_id:
        return
    client = get_supabase_client()
    try:
        existing = client.table("session_documents").select("id").eq("session_id", session_id).eq("case_id", case_id).execute()
        if not existing.data:
            client.table("session_documents").insert({
                "session_id": session_id,
                "case_id": case_id,
                "filename": filename,
            }).execute()
    except Exception as e:
        print(f"[chat_router] link_document_to_session warning: {e}")


@router.post("/ask")
def ask_legal_question(request: QueryRequest, user=Depends(get_current_user)):
    try:
        return _handle_ask(request, user.id)
    except Exception as e:
        print(f"[chat/ask ERROR] {e}")
        return {"answer": "Something went wrong. Please try again.", "verified": False, "sources": [], "error": True}


def _handle_ask(request: QueryRequest, user_id: str):
    query = request.query
    safety = check_input_safety(query)
    
    session_id = ensure_valid_session(request.session_id, user_id, query)
    save_message(session_id, "user", query)

    # 1. Prompt Injection / Jailbreak Safety Guard
    if not safety["is_safe"]:
        block_msg = "I cannot process queries attempting system instruction override or manipulation. Please ask a valid question related to Indian law or your case documents."
        save_message(session_id, "assistant", block_msg)
        return {
            "answer": block_msg,
            "conclusion": block_msg,
            "verified": False,
            "sources": [],
            "usefulness": "low",
            "session_id": session_id,
            "mode": "blocked",
        }

    history = get_recent_history(session_id)
    model = choose_model(query)
    query_vec = embed_text(query, task_type="RETRIEVAL_QUERY")

    # Combine case_ids list and singular case_id for backward compatibility
    effective_case_ids = list(request.case_ids)
    if request.case_id and request.case_id not in effective_case_ids:
        effective_case_ids.append(request.case_id)

    # ---- MODE A: one or more documents attached (Court Case / FIR / Contract / Judgment) ----
    if effective_case_ids:
        client = get_supabase_client()
        # Strict readiness check -- NEVER answer against an unready document
        not_ready = [cid for cid in effective_case_ids if get_case_status(cid) != "ready"]
        if not_ready:
            answer = "One or more attached documents are still being processed. Please wait a moment before asking about them."
            save_message(session_id, "assistant", answer)
            return {
                "answer": answer,
                "conclusion": answer,
                "verified": False,
                "sources": [],
                "usefulness": "low",
                "session_id": session_id,
            }

        # Link attached docs to session
        for cid in effective_case_ids:
            try:
                case_row = client.table("cases").select("filename").eq("id", cid).execute()
                fname = case_row.data[0]["filename"] if (case_row.data and case_row.data[0].get("filename")) else "document"
                link_document_to_session(session_id, cid, fname)
            except Exception:
                pass

        audience = "student_public"
        chunk_matches = search_document_chunks_multi(query_vec, effective_case_ids, match_count=6)
        source_objects = []

        if not chunk_matches:
            # Fallback to case summary and text directly from cases table so query is NEVER rejected
            case_data = client.table("cases").select("filename, summary, case_text").in_("id", effective_case_ids).execute().data or []
            fallback_text_parts = []
            for cd in case_data:
                fname = cd.get("filename", "Document")
                summary_text = cd.get("summary", "")
                raw_text = (cd.get("case_text") or "")[:10000]
                content = f"Document: {fname}\nSummary: {summary_text}\nContent:\n{raw_text}"
                fallback_text_parts.append(content)
                source_objects.append({
                    "name": f"{fname} (Case Document)",
                    "type": "document",
                    "url": None,
                    "verification_status": "pending",
                    "jurisdiction": None,
                })
            if fallback_text_parts:
                evidence = "\n\n---\n\n".join(fallback_text_parts)
            else:
                answer = "I could not find relevant content in the attached document(s) for this question."
                save_message(session_id, "assistant", answer)
                return {
                    "answer": answer,
                    "conclusion": answer,
                    "verified": False,
                    "sources": [],
                    "usefulness": "low",
                    "session_id": session_id,
                }
        else:
            evidence = "\n".join(c["chunk_text"] for c in chunk_matches)
            source_objects = [
                {
                    "name": f"{c.get('filename', 'Document')} — Page {c.get('page_number', 1)}",
                    "type": "document",
                    "url": None,
                    "verification_status": "pending",
                    "jurisdiction": None,
                }
                for c in chunk_matches
            ]
        from_crag = False

    # ---- MODE B: no document -- domain guardrail + RAG/CRAG/general ----
    else:
        intent = classify_intent(query)
        if intent["domain"] == "out_of_domain":
            save_message(session_id, "assistant", REFUSAL_MESSAGE)
            return {
                "answer": REFUSAL_MESSAGE,
                "conclusion": REFUSAL_MESSAGE,
                "verified": False,
                "sources": [],
                "usefulness": "low",
                "session_id": session_id,
                "mode": "refused",
            }

        audience = intent["audience"]
        matches = search_knowledge_base(query_vec, query, match_count=3)
        from_crag = False
        if not is_retrieval_sufficient(matches):
            external = corrective_web_search(query)
            matches = [external] if external else []
            from_crag = bool(external)

        if not matches:
            return _general_fallback(query, model, audience, session_id, history)

        evidence = "\n".join(m.get("full_text", "") for m in matches)
        source_objects = []
        for m in matches:
            if m.get("source_type") == "external_crag":
                for link in m.get("source_links", [{"title": m.get("display_name", "Web source"), "url": ""}])[:2]:
                    source_objects.append({
                        "name": link.get("title", "Web source")[:60],
                        "type": "web",
                        "url": link.get("url") or None,
                        "verification_status": "external",
                        "jurisdiction": None,
                    })
            else:
                source_objects.append({
                    "name": m.get("display_name") or m.get("case_name", "Unknown"),
                    "type": "statute" if "act_name" in m else "judgment",
                    "url": None,
                    "verification_status": "pending",
                    "jurisdiction": m.get("jurisdiction_type"),
                })

    # ---- Draft + TrustAgent (shared) ----
    history_section = f"PREVIOUS MESSAGES:\n{history}\n" if history else ""
    
    if effective_case_ids:
        doc_prompt = f"""You are analyzing the user's attached legal/case document(s).
{LANGUAGE_INSTRUCTION}
{LENGTH_INSTRUCTION}
{AUDIENCE_INSTRUCTIONS[audience]}

{history_section}
TASK: Answer the user's question accurately using the attached document evidence below.
If the user asks for a summary or overview, provide a structured summary highlighting the key facts, parties involved, legal sections/issues, and findings/orders.
Do NOT state that information is missing if it is present in the document evidence.

DOCUMENT EVIDENCE:
{evidence}

USER QUESTION: {query}

ANSWER:"""
        draft = call_llm(model, doc_prompt)
    else:
        general_prompt = f"""{LANGUAGE_INSTRUCTION}
{LENGTH_INSTRUCTION}
{AUDIENCE_INSTRUCTIONS[audience]}

{history_section}
Answer the CURRENT query using ONLY this legal evidence -- do not invent ungrounded sections.

Evidence: {evidence}

CURRENT QUERY: {query}

ANSWER:"""
        draft = call_llm(model, general_prompt)

    claims = extract_claims(draft)
    verdicts = verify_claims_batch(claims, evidence)
    overall = summarize_verdicts(verdicts)

    if from_crag and overall in ("unverified", "contradicted"):
        return _general_fallback(query, model, audience, session_id, history)

    for s in source_objects:
        if s["verification_status"] == "pending":
            s["verification_status"] = VERDICT_LABEL.get(overall, "unverified")

    final_answer = redact_pii(draft)
    reflection = self_reflect(query, final_answer, evidence)
    judgment = judge_answer(query, final_answer, evidence)
    verified = (overall == "supported") and judgment["is_accurate"]
    quality_note = "" if judgment["is_accurate"] else f"Quality-check note: {judgment['issue']}"
    dept_info = suggest_department_and_helpline(query, call_llm) if not effective_case_ids else None
    suggestions = generate_suggestions(query, final_answer, model)

    save_message(session_id, "assistant", final_answer, sources=[s["name"] for s in source_objects])
    _log(query, final_answer, model, verified)

    return {
        "answer": final_answer,
        "conclusion": reflection["conclusion"],
        "usefulness": reflection["usefulness"],
        "verified": verified,
        "sources": source_objects,
        "quality_note": quality_note,
        "department_suggestion": dept_info,
        "model_used": model,
        "suggestions": suggestions,
        "session_id": session_id,
    }


def _general_fallback(query: str, model: str, audience: str, session_id: str | None, history: str):
    general_answer = general_legal_answer(query, model, audience, history=history)
    general_answer = redact_pii(general_answer)
    reflection = self_reflect(query, general_answer, "(general knowledge, no specific evidence)")
    suggestions = generate_suggestions(query, general_answer, model)
    save_message(session_id, "assistant", general_answer)
    _log(query, general_answer, model, verified=False)
    return {
        "answer": general_answer,
        "conclusion": reflection["conclusion"],
        "usefulness": reflection["usefulness"],
        "verified": False,
        "sources": [],
        "mode": "general_knowledge",
        "model_used": model,
        "suggestions": suggestions,
        "session_id": session_id,
    }



def _log(query: str, answer: str, model: str, verified: bool):
    previous_hash = get_last_hash()
    event = {"query": query, "verified": verified, "model": model}
    log_entry = build_log_entry(event, previous_hash)
    save_log_entry(log_entry, query=query, response=answer, verified=verified, model_used=model)


class SessionCreate(BaseModel):
    title: str = "New Chat"


class SessionUpdate(BaseModel):
    title: str | None = None
    pinned: bool | None = None


@router.post("/sessions")
def create_session(body: SessionCreate, user=Depends(get_current_user)):
    client = get_supabase_client()
    res = client.table("chat_sessions").insert({"user_id": user.id, "title": body.title}).execute()
    return res.data[0] if res.data else {"id": "", "title": body.title}


@router.get("/sessions")
def list_sessions(user=Depends(get_current_user)):
    client = get_supabase_client()
    return (
        client.table("chat_sessions")
        .select("id, title, updated_at, pinned")
        .eq("user_id", user.id)
        .order("pinned", desc=True)
        .order("updated_at", desc=True)
        .execute()
        .data or []
    )


@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str, user=Depends(get_current_user)):
    client = get_supabase_client()
    docs = []
    try:
        doc_res = client.table("session_documents").select("case_id, filename").eq("session_id", session_id).execute()
        docs = doc_res.data or []
    except Exception as e:
        print(f"[chat_router] get_session_messages docs warning: {e}")

    messages = (
        client.table("chat_messages")
        .select("role, content, sources, created_at")
        .eq("session_id", session_id)
        .order("created_at")
        .execute()
        .data or []
    )
    return {"messages": messages, "documents": docs}


@router.patch("/sessions/{session_id}")
def update_session(session_id: str, body: SessionUpdate, user=Depends(get_current_user)):
    client = get_supabase_client()
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if updates:
        client.table("chat_sessions").update(updates).eq("id", session_id).eq("user_id", user.id).execute()
    return {"updated": True}


@router.delete("/sessions/clear/all")
def clear_all_chat_sessions(user=Depends(get_current_user)):
    client = get_supabase_client()
    try:
        user_sessions = client.table("chat_sessions").select("id").eq("user_id", user.id).execute().data or []
        session_ids = [s["id"] for s in user_sessions]
        if session_ids:
            client.table("chat_messages").delete().in_("session_id", session_ids).execute()
            client.table("session_documents").delete().in_("session_id", session_ids).execute()
            client.table("chat_sessions").delete().eq("user_id", user.id).execute()
        return {"status": "success", "cleared_sessions": len(session_ids)}
    except Exception as e:
        print(f"[chat_router] clear_all_chat_sessions error: {e}")
        return {"status": "error", "detail": str(e)}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, user=Depends(get_current_user)):
    client = get_supabase_client()
    try:
        # Delete dependent messages and session documents first to ensure foreign key safety
        client.table("chat_messages").delete().eq("session_id", session_id).execute()
    except Exception as e:
        print(f"[chat_router] delete chat_messages warning: {e}")

    try:
        client.table("session_documents").delete().eq("session_id", session_id).execute()
    except Exception as e:
        print(f"[chat_router] delete session_documents warning: {e}")

    client.table("chat_sessions").delete().eq("id", session_id).eq("user_id", user.id).execute()
    return {"deleted": True}