"""
Chat Router — 4-way routing fix: CASE_SPECIFIC uses only document chunks,
GENERAL_LAW completely ignores the attached document and uses knowledge-
base + CRAG, MIXED combines both with clearly separated evidence/sources,
OUT_OF_DOMAIN refuses. Also: meta-summary-queries get the stored summary
directly (no semantic-retrieval mismatch), and verification distinguishes
genuine "unverified" from infrastructure parse-failures.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import re

from ai_core.guardrails.input_guard import check_input_safety
from ai_core.guardrails.output_guard import redact_pii
from ai_core.router.adaptive_router import choose_model
from ai_core.router.intent_classifier import classify_intent, REFUSAL_MESSAGE, AUDIENCE_INSTRUCTIONS
from ai_core.rag.embeddings import embed_text
from ai_core.rag.vector_store import search_knowledge_base, search_document_chunks, get_supabase_client
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
VERDICT_LABEL = {"supported": "verified", "partially_supported": "partial", "contradicted": "contradicted", "unverified": "unverified", "verification_pending": "pending"}

META_SUMMARY_PATTERNS = [
    r"\bsummar(y|ize|ise)\b", r"\bwhat is this (document|file|pdf|case)\b",
    r"\bis this a case\b", r"\bwhat'?s this about\b", r"\bbtao.*kya hai\b", r"\bkya hai.*file\b",
]


class QueryRequest(BaseModel):
    query: str
    case_id: str | None = None
    session_id: str | None = None


def is_meta_summary_query(query: str) -> bool:
    lowered = query.lower()
    return any(re.search(p, lowered) for p in META_SUMMARY_PATTERNS)


def general_legal_answer(query, model, audience, history=""):
    history_section = f"PREVIOUS MESSAGES (context only, never invent beyond this):\n{history}\n" if history else "(First message in this chat.)\n"
    prompt = f"""You are a legal-information assistant for Indian law (Bharatiya Nyaya Sanhita (BNS), 2023, BNSS 2023, BSA 2023, IPC historical, CrPC, civil law, court procedure).
{LANGUAGE_INSTRUCTION}
{LENGTH_INSTRUCTION}
{AUDIENCE_INSTRUCTIONS[audience]}

{history_section}

CRITICAL LEGAL SAFETY RULES:
1. Do NOT invent, guess, or hallucinate statutory section numbers, case citations, or penalties.
2. If you cannot confirm an exact statutory section number with certainty, explicitly state: "I could not verify the exact statutory provision from the available legal sources."
3. In criminal law, note that the Bharatiya Nyaya Sanhita (BNS), 2023 is in force from 1 July 2024, replacing the Indian Penal Code (IPC), 1860.
4. For fine/sentence figures, add: "Please verify the exact current figure from the latest Bharatiya Nyaya Sanhita (BNS) text."
5. If the question involves an emergency/urgent personal-safety matter, include the relevant official helpline (Police 100/112, Women Helpline 181, Cyber Crime 1930, Child Helpline 1098, NALSA Legal Aid 15100).

QUESTION: {query}

ANSWER:"""
    return call_llm(model, prompt)


def generate_suggestions(query, answer, model):
    prompt = f"""Suggest 3 short follow-up legal questions. ONLY a JSON array of 3 strings.
Q: {query}
A: {answer[:200]}
JSON:"""
    try:
        raw = call_llm(model, prompt)
        import json
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
        s = json.loads(cleaned)
        return s if isinstance(s, list) else []
    except Exception:
        return []


def get_recent_history(session_id, current_case_id=None, limit=4):
    if not session_id:
        return ""
    client = get_supabase_client()
    try:
        # Cross-document history isolation: verify session's case_id
        if current_case_id:
            sess = client.table("chat_sessions").select("case_id").eq("id", session_id).execute()
            if sess.data:
                sess_case_id = sess.data[0].get("case_id")
                if sess_case_id and str(sess_case_id).lower() != str(current_case_id).lower():
                    return ""
        result = (client.table("chat_messages").select("role, content")
                  .eq("session_id", session_id).order("created_at", desc=True).limit(limit).execute())
        msgs = list(reversed(result.data))
        return "\n".join(f"{m['role'].upper()}: {m['content'][:150]}" for m in msgs)
    except Exception:
        return ""


def ensure_valid_session(session_id, user_id, fallback_title, case_id=None):
    client = get_supabase_client()
    if session_id:
        result = client.table("chat_sessions").select("id, user_id, case_id").eq("id", session_id).execute()
        if result.data and result.data[0]["user_id"] == user_id:
            sess_case_id = result.data[0].get("case_id")
            if case_id and sess_case_id and str(sess_case_id).lower() != str(case_id).lower():
                client.table("chat_sessions").update({"case_id": case_id}).eq("id", session_id).execute()
            return session_id
    new_session = client.table("chat_sessions").insert({"user_id": user_id, "title": fallback_title[:40], "case_id": case_id}).execute()
    return new_session.data[0]["id"]


def save_message(session_id, role, content, sources=None):
    if not session_id:
        return
    client = get_supabase_client()
    client.table("chat_messages").insert({"session_id": session_id, "role": role, "content": content, "sources": sources or []}).execute()
    client.table("chat_sessions").update({"updated_at": "now()"}).eq("id", session_id).execute()


def link_document_to_session(session_id, case_id, filename):
    if not session_id:
        return
    client = get_supabase_client()
    client.table("chat_sessions").update({"case_id": case_id, "case_filename": filename}).eq("id", session_id).execute()


def _verify_and_label(draft: str, evidence: str) -> tuple[str, list]:
    """Returns (overall_status, verdicts). overall_status is one of:
    supported / partially_supported / contradicted / unverified / verification_pending.
    verification_pending means the VERIFIER ITSELF failed (infra issue) --
    distinct from 'unverified' which means evidence genuinely doesn't support."""
    claims, extraction_ok = extract_claims(draft)
    if not extraction_ok or not claims:
        return "verification_pending", []
    verdicts, verification_ok = verify_claims_batch(claims, evidence)
    if not verification_ok:
        return "verification_pending", []
    return summarize_verdicts(verdicts), verdicts


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
    if not safety["is_safe"]:
        return {"blocked": True, "reason": safety["reason"]}

    session_id = ensure_valid_session(request.session_id, user_id, query, case_id=request.case_id)
    save_message(session_id, "user", query)
    history = get_recent_history(session_id, current_case_id=request.case_id)
    model = choose_model(query)

    # ============================================================
    # CORE FIX: classify intent FIRST, regardless of whether a
    # document is attached -- this decides the actual routing.
    # ============================================================
    has_document = bool(request.case_id)
    intent = classify_intent(query, has_document)
    label = intent.get("label", intent.get("query_mode", "GENERAL_LAW"))
    audience = intent.get("audience", "student_public")

    if label == "OUT_OF_DOMAIN" or intent.get("domain") == "out_of_domain":
        save_message(session_id, "assistant", REFUSAL_MESSAGE)
        return {"answer": REFUSAL_MESSAGE, "conclusion": None, "verified": False, "sources": [], "usefulness": "low", "session_id": session_id, "mode": "refused"}

    client = get_supabase_client()
    filename = None
    case_row = None
    doc_status = "ready"
    case_text = ""

    if has_document:
        case_row = client.table("cases").select("filename, summary, status, case_text").eq("id", request.case_id).execute()
        if case_row.data:
            row = case_row.data[0]
            filename = row.get("filename") or "Uploaded Document"
            doc_status = row.get("status") or "ready"
            case_text = row.get("case_text") or ""
            link_document_to_session(session_id, request.case_id, filename)
        else:
            if label in ("CASE_SPECIFIC", "MIXED"):
                answer = "The requested document could not be found. Please select or re-upload a valid document."
                save_message(session_id, "assistant", answer)
                return {"answer": answer, "conclusion": None, "verified": False, "sources": [], "usefulness": "low", "session_id": session_id, "no_documentary_evidence_found": True}

    # ---- Indexing Status Gates ----
    if label in ("CASE_SPECIFIC", "MIXED") and has_document:
        if doc_status == "processing":
            answer = "Document is still being indexed. Please wait a moment and try again."
            save_message(session_id, "assistant", answer)
            return {"answer": answer, "conclusion": None, "verified": False, "sources": [], "usefulness": "low", "session_id": session_id, "indexing_in_progress": True}
        elif doc_status == "failed":
            answer = "Document is not indexed correctly or indexing failed. Please re-upload the document."
            save_message(session_id, "assistant", answer)
            return {"answer": answer, "conclusion": None, "verified": False, "sources": [], "usefulness": "low", "session_id": session_id, "indexing_failed": True}

    # ---- META-SUMMARY SHORTCUT: "summarize this" uses ONLY exact case summary/text ----
    if label == "CASE_SPECIFIC" and has_document and is_meta_summary_query(query):
        stored_summary = case_row.data[0].get("summary", "") if case_row and case_row.data else ""
        if stored_summary and stored_summary.strip() and stored_summary != "Summary generation in progress.":
            final = f"{stored_summary}\n\n[Source: {filename} — full document summary]"
            save_message(session_id, "assistant", final, sources=[filename])
            return {
                "answer": final, "conclusion": None, "usefulness": "high", "verified": True,
                "sources": [{"name": filename, "type": "document", "url": None, "verification_status": "verified", "jurisdiction": None}],
                "session_id": session_id,
            }
        elif case_text:
            from ai_core.rag.summarizer import summarize_case
            generated_summary = summarize_case(case_text[:6000])
            client.table("cases").update({"summary": generated_summary}).eq("id", request.case_id).execute()
            final = f"{generated_summary}\n\n[Source: {filename} — full document summary]"
            save_message(session_id, "assistant", final, sources=[filename])
            return {
                "answer": final, "conclusion": None, "usefulness": "high", "verified": True,
                "sources": [{"name": filename, "type": "document", "url": None, "verification_status": "verified", "jurisdiction": None}],
                "session_id": session_id,
            }

    query_vec = embed_text(query, task_type="RETRIEVAL_QUERY")

    document_evidence, document_sources = "", []
    general_evidence, general_sources = "", []
    from_crag = False

    # ---- Gather DOCUMENT evidence (only if label needs it) ----
    if label in ("CASE_SPECIFIC", "MIXED") and has_document:
        chunk_matches = search_document_chunks(query_vec, request.case_id, match_count=5)
        # Strict defensive guarantee: only keep chunks matching exact requested case_id
        if request.case_id:
            chunk_matches = [
                c for c in chunk_matches
                if "case_id" not in c or str(c.get("case_id", "")).lower() == str(request.case_id).lower()
            ]

        if chunk_matches:
            top_sim = chunk_matches[0].get("similarity") or chunk_matches[0].get("score")
            if top_sim is not None and top_sim < 0.20 and label == "CASE_SPECIFIC":
                topic = query.strip()
                answer = f"No supporting evidence was found in the uploaded document regarding {topic}."
                save_message(session_id, "assistant", answer)
                return {"answer": answer, "conclusion": None, "verified": False, "sources": [], "usefulness": "low", "session_id": session_id, "no_documentary_evidence_found": True}

            document_evidence = "\n".join(c["chunk_text"] for c in chunk_matches)
            document_sources = [
                {"name": f"{filename} — Page {c.get('page_number', 1)}", "type": "document", "url": None,
                 "verification_status": "pending", "jurisdiction": None}
                for c in chunk_matches
            ]
        elif label == "CASE_SPECIFIC":
            topic = query.strip()
            answer = f"No supporting evidence was found in the uploaded document regarding {topic}."
            save_message(session_id, "assistant", answer)
            return {"answer": answer, "conclusion": None, "verified": False, "sources": [], "usefulness": "low", "session_id": session_id, "no_documentary_evidence_found": True}

    # ---- Gather GENERAL_LAW evidence (only if label needs it) ----
    if label in ("GENERAL_LAW", "MIXED"):
        matches = search_knowledge_base(query_vec, query, match_count=3)
        if not is_retrieval_sufficient(matches):
            external = corrective_web_search(query)
            matches = [external] if external else []
            from_crag = bool(external)

        if matches:
            general_evidence = "\n".join(m.get("full_text", "") for m in matches)
            for m in matches:
                if m.get("source_type") == "external_crag":
                    for link in m.get("source_links", [{"title": m.get("display_name", "Web source"), "url": ""}])[:2]:
                        general_sources.append({"name": link.get("title", "Web source")[:60], "type": "web",
                                                  "url": link.get("url") or None, "verification_status": "external", "jurisdiction": None})
                else:
                    general_sources.append({"name": m.get("display_name") or m.get("case_name", "Unknown"),
                                              "type": "statute" if "act_name" in m else "judgment", "url": None,
                                              "verification_status": "pending", "jurisdiction": m.get("jurisdiction_type")})
        elif label == "GENERAL_LAW":
            return _general_fallback(query, model, audience, session_id, history)

    # If MIXED and genuinely nothing found anywhere, fall back to general knowledge
    if not document_evidence and not general_evidence:
        return _general_fallback(query, model, audience, session_id, history)

    combined_evidence = (
        f"=== UPLOADED CASE FACTS ({filename}) ===\n{document_evidence}\n\n=== APPLICABLE INDIAN STATUTORY LAW & PRECEDENTS ===\n{general_evidence}"
        if label == "MIXED" else (document_evidence or general_evidence)
    )
    source_objects = document_sources + general_sources

    if label == "CASE_SPECIFIC":
        history_section = f"CONVERSATION CONTEXT (Never invent case facts beyond the evidence below):\n{history}\n\n" if history else ""
        prompt_instructions = (
            f"You are NyayaPramaan, an evidence-grounded legal assistant for Indian case files.\n"
            f"{LANGUAGE_INSTRUCTION}\n{LENGTH_INSTRUCTION}\n{AUDIENCE_INSTRUCTIONS[audience]}\n\n"
            f"{history_section}"
            f"STRICT CASE-SPECIFIC EVIDENCE CONTRACT:\n"
            f"1. Answer the CURRENT query using ONLY the verified evidence below -- do not add outside information or model memory.\n"
            f"2. STRICT NEGATIVE CONSTRAINT: Do NOT invent, fabricate, or list standard legal documents (such as sale deeds, probate orders, revenue records, tax receipts, utility bills, mutation certificates, affidavits, or commissioner reports) unless explicitly mentioned in the Evidence below.\n"
            f"3. Do NOT extrapolate unstated details: if a document name or person is mentioned without further findings, state ONLY what is written in the Evidence.\n"
            f"4. If the Evidence does NOT contain facts answering the query, reply EXACTLY:\n"
            f"   'No supporting evidence was found in the uploaded document regarding {query}.'\n"
            f"5. Note that Bharatiya Nyaya Sanhita (BNS), 2023 is in force in India from 1 July 2024.\n\n"
            f"EVIDENCE:\n{combined_evidence}\n\n"
            f"CURRENT QUERY: {query}\n\nANSWER:"
        )
    else:
        history_section = f"PREVIOUS MESSAGES:\n{history}\n" if history else ""
        prompt_instructions = (
            f"{LANGUAGE_INSTRUCTION}\n{LENGTH_INSTRUCTION}\n{AUDIENCE_INSTRUCTIONS[audience]}\n\n"
            f"{history_section}"
            f"CRITICAL LEGAL EVIDENCE RULES:\n"
            f"1. Answer the CURRENT query using ONLY the verified evidence below -- do not add outside information.\n"
            f"2. STRICT NEGATIVE CONSTRAINT: Do NOT invent, fabricate, or list standard legal documents or case findings that are not explicitly stated in the Evidence.\n"
            f"3. Note that Bharatiya Nyaya Sanhita (BNS), 2023 is in force in India from 1 July 2024.\n\n"
            f"EVIDENCE:\n{combined_evidence}\n\n"
            f"CURRENT QUERY: {query}\n\nANSWER:"
        )

    draft = call_llm(model, prompt_instructions)

    overall, verdicts = _verify_and_label(draft, combined_evidence)

    # Hard-stop: If in CASE_SPECIFIC mode and the claims are contradicted or completely unverified against document evidence
    if label == "CASE_SPECIFIC" and overall in ("contradicted", "unverified") and len(verdicts) > 0:
        refusal_ans = f"No supporting evidence was found in the uploaded document regarding {query.strip()}."
        save_message(session_id, "assistant", refusal_ans)
        return {
            "answer": refusal_ans,
            "conclusion": None,
            "usefulness": "low",
            "verified": False,
            "sources": [],
            "no_documentary_evidence_found": True,
            "session_id": session_id,
            "routing_label": label,
        }

    if from_crag and overall in ("unverified", "contradicted"):
        return _general_fallback(query, model, audience, session_id, history)

    for s in source_objects:
        if s["verification_status"] == "pending":
            s["verification_status"] = VERDICT_LABEL.get(overall, "unverified")

    final_answer = redact_pii(draft)

    reflection = self_reflect(query, final_answer, combined_evidence)
    judgment = judge_answer(query, final_answer, combined_evidence)
    verified = (overall == "supported") and judgment["is_accurate"]
    quality_note = "" if judgment["is_accurate"] else f"Quality-check note: {judgment['issue']}"

    dept_info = suggest_department_and_helpline(query, call_llm) if label in ("GENERAL_LAW", "MIXED") else None
    suggestions = generate_suggestions(query, final_answer, model)

    save_message(session_id, "assistant", final_answer, sources=[s["name"] for s in source_objects])
    _log(query, final_answer, model, verified)

    conclusion_text = reflection.get("conclusion") if reflection.get("conclusion_needed", True) else None

    return {
        "answer": final_answer,
        "conclusion": conclusion_text,
        "usefulness": reflection.get("usefulness", "medium"),
        "verified": verified,
        "sources": source_objects,
        "quality_note": quality_note,
        "department_suggestion": dept_info,
        "model_used": model,
        "suggestions": suggestions,
        "session_id": session_id,
        "routing_label": label,
    }


def _general_fallback(query, model, audience, session_id, history):
    general_answer = general_legal_answer(query, model, audience, history=history)
    general_answer = redact_pii(general_answer)
    reflection = self_reflect(query, general_answer, "(general knowledge, no specific evidence)")
    suggestions = generate_suggestions(query, general_answer, model)
    final = f"{general_answer}\n\n[ℹ️ General Legal Information — not verified against our case/statute database.]"
    save_message(session_id, "assistant", final)
    _log(query, general_answer, model, verified=False)
    conclusion_text = reflection.get("conclusion") if reflection.get("conclusion_needed", True) else None
    return {
        "answer": final,
        "conclusion": conclusion_text,
        "usefulness": reflection.get("usefulness", "medium"),
        "verified": False,
        "sources": [],
        "mode": "general_knowledge",
        "routing_label": "GENERAL_LAW",
        "model_used": model,
        "suggestions": suggestions,
        "session_id": session_id,
    }


def _log(query, answer, model, verified):
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
    return client.table("chat_sessions").insert({"user_id": user.id, "title": body.title}).execute().data[0]

@router.get("/sessions")
def list_sessions(user=Depends(get_current_user)):
    client = get_supabase_client()
    return (client.table("chat_sessions").select("id, title, updated_at, pinned")
            .eq("user_id", user.id).order("pinned", desc=True).order("updated_at", desc=True).execute().data)

@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str, user=Depends(get_current_user)):
    client = get_supabase_client()
    session_info = client.table("chat_sessions").select("case_id, case_filename").eq("id", session_id).eq("user_id", user.id).execute()
    messages = (client.table("chat_messages").select("role, content, sources, created_at")
                .eq("session_id", session_id).order("created_at").execute().data)
    return {
        "messages": messages,
        "case_id": session_info.data[0]["case_id"] if session_info.data else None,
        "case_filename": session_info.data[0]["case_filename"] if session_info.data else None,
    }

@router.patch("/sessions/{session_id}")
def update_session(session_id: str, body: SessionUpdate, user=Depends(get_current_user)):
    client = get_supabase_client()
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if updates:
        client.table("chat_sessions").update(updates).eq("id", session_id).eq("user_id", user.id).execute()
    return {"updated": True}

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, user=Depends(get_current_user)):
    client = get_supabase_client()
    client.table("chat_sessions").delete().eq("id", session_id).eq("user_id", user.id).execute()
    return {"deleted": True}
