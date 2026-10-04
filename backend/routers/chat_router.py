
"""

Chat Router — Guardrails -> Intent Classifier -> Adaptive Router -> RAG ->

CRAG -> General-fallback (with helpline) -> TrustAgent -> Self-RAG ->

LLM-Judge -> structured colored-citations -> per-user isolated history.

"""

from fastapi import APIRouter, Depends

from pydantic import BaseModel



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

from ai_core.trustagent.corrector import suggest_department_and_helpline

from ai_core.evaluation.llm_judge import judge_answer

from trust_log.hash_chain import build_log_entry, get_last_hash, save_log_entry

from backend.auth.supabase_auth import get_current_user



router = APIRouter()



LANGUAGE_INSTRUCTION = "Detect whether the question is in English, Hindi, or Hinglish and respond in the SAME language/style."

LENGTH_INSTRUCTION = "Match answer length to complexity: short and direct for simple questions, fuller (bullet points if listing multiple sections/penalties) for complex ones."

VERDICT_LABEL = {"supported": "verified", "partially_supported": "partial", "contradicted": "contradicted", "unverified": "unverified"}





class QueryRequest(BaseModel):

    query: str

    case_id: str | None = None

    session_id: str | None = None





def general_legal_answer(query, model, audience, history=""):

    history_section = f"PREVIOUS MESSAGES (context only, never invent beyond this):\n{history}\n" if history else "(First message in this chat.)\n"

    prompt = f"""You are a legal-information assistant for Indian law (IPC, BNS, CrPC, BNSS, civil law, court procedure).

{LANGUAGE_INSTRUCTION}

{LENGTH_INSTRUCTION}

{AUDIENCE_INSTRUCTIONS[audience]}



{history_section}



CRITICAL: If asked about earlier messages, use ONLY the section above.

Be precise with section numbers. If the question involves an emergency or

urgent personal-safety matter, include the relevant official helpline

(Police 100/112, Women Helpline 181, Cyber Crime 1930, Child Helpline

1098, NALSA Legal Aid 15100) in your answer.



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

        import json, re

        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())

        s = json.loads(cleaned)

        return s if isinstance(s, list) else []

    except Exception:

        return []





def get_recent_history(session_id, limit=4):

    if not session_id:

        return ""

    client = get_supabase_client()

    try:

        result = (client.table("chat_messages").select("role, content")

                  .eq("session_id", session_id).order("created_at", desc=True).limit(limit).execute())

        msgs = list(reversed(result.data))

        return "\n".join(f"{m['role'].upper()}: {m['content'][:150]}" for m in msgs)

    except Exception:

        return ""





def ensure_valid_session(session_id, user_id, fallback_title):

    client = get_supabase_client()

    if session_id:

        result = client.table("chat_sessions").select("id, user_id").eq("id", session_id).execute()

        if result.data and result.data[0]["user_id"] == user_id:

            return session_id

    new_session = client.table("chat_sessions").insert({"user_id": user_id, "title": fallback_title[:40]}).execute()

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



    session_id = ensure_valid_session(request.session_id, user_id, query)

    save_message(session_id, "user", query)

    history = get_recent_history(session_id)

    model = choose_model(query)

    query_vec = embed_text(query, task_type="RETRIEVAL_QUERY")



    # ---- MODE A: a document is attached ----

    if request.case_id:

        client = get_supabase_client()

        case_row = client.table("cases").select("filename").eq("id", request.case_id).execute()

        filename = case_row.data[0]["filename"] if case_row.data else "document"

        link_document_to_session(session_id, request.case_id, filename)



        audience = "student_public"

        chunk_matches = search_document_chunks(query_vec, request.case_id, match_count=4)

        if not chunk_matches:

            answer = (

                "I could not find relevant content in the attached document for this "

                "question. If you just uploaded it, it may still be indexing -- please "

                "try again in a moment."

            )

            save_message(session_id, "assistant", answer)

            return {"answer": answer, "conclusion": answer, "verified": False, "sources": [], "usefulness": "low", "session_id": session_id}



        evidence = "\n".join(c["chunk_text"] for c in chunk_matches)

        source_objects = [

            {"name": f"{filename} — Page {c['page_number']}", "type": "document", "url": None,

             "verification_status": "pending", "jurisdiction": None}

            for c in chunk_matches

        ]

        primary_name = source_objects[0]["name"]

        from_crag = False



    # ---- MODE B: no document ----

    else:

        intent = classify_intent(query)

        if intent["domain"] == "out_of_domain":

            save_message(session_id, "assistant", REFUSAL_MESSAGE)

            return {"answer": REFUSAL_MESSAGE, "conclusion": REFUSAL_MESSAGE, "verified": False, "sources": [], "usefulness": "low", "session_id": session_id, "mode": "refused"}

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

                    source_objects.append({"name": link.get("title", "Web source")[:60], "type": "web",

                                            "url": link.get("url") or None, "verification_status": "external", "jurisdiction": None})

            else:

                source_objects.append({"name": m.get("display_name") or m.get("case_name", "Unknown"),

                                        "type": "statute" if "act_name" in m else "judgment", "url": None,

                                        "verification_status": "pending", "jurisdiction": m.get("jurisdiction_type")})

        primary_name = source_objects[0]["name"] if source_objects else "Unknown"



    history_section = f"PREVIOUS MESSAGES:\n{history}\n" if history else ""

    draft = call_llm(

        model,

        f"{LANGUAGE_INSTRUCTION}\n{LENGTH_INSTRUCTION}\n{AUDIENCE_INSTRUCTIONS[audience]}\n\n{history_section}\nAnswer the CURRENT query using ONLY this evidence -- do not add outside information.\n\nEvidence: {evidence}\n\nCURRENT QUERY: {query}",

    )



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



    dept_info = suggest_department_and_helpline(query, call_llm) if not request.case_id else None

    suggestions = generate_suggestions(query, final_answer, model)



    save_message(session_id, "assistant", final_answer, sources=[s["name"] for s in source_objects])

    _log(query, final_answer, model, verified)



    return {

        "answer": final_answer, "conclusion": reflection["conclusion"], "usefulness": reflection["usefulness"],

        "verified": verified, "sources": source_objects, "quality_note": quality_note,

        "department_suggestion": dept_info, "model_used": model, "suggestions": suggestions, "session_id": session_id,

    }





def _general_fallback(query, model, audience, session_id, history):

    general_answer = general_legal_answer(query, model, audience, history=history)

    general_answer = redact_pii(general_answer)

    reflection = self_reflect(query, general_answer, "(general knowledge, no specific evidence)")

    suggestions = generate_suggestions(query, general_answer, model)

    final = f"{general_answer}\n\n[ℹ️ General Legal Information — not verified against our case/statute database.]"

    save_message(session_id, "assistant", final)

    _log(query, general_answer, model, verified=False)

    return {"answer": final, "conclusion": reflection["conclusion"], "usefulness": reflection["usefulness"],

            "verified": False, "sources": [], "mode": "general_knowledge", "model_used": model,

            "suggestions": suggestions, "session_id": session_id}





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

