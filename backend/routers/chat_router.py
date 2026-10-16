"""Chat Router -> backend/routers/chat_router.py
Hybrid (vector + lexical) document retrieval, exact date extraction, law-only gate, vetted web sources,
owner-checked cases, parallel post-steps, honest LLM-down handling, chat-style answers, multi-question messages."""
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
import re
import threading
import time
import uuid

from ai_core.guardrails.input_guard import check_input_safety
from ai_core.guardrails.output_guard import redact_pii
from ai_core.router.adaptive_router import choose_model
from ai_core.router.intent_classifier import classify_intent, REFUSAL_MESSAGE, AUDIENCE_INSTRUCTIONS
from ai_core.rag.embeddings import embed_text
from ai_core.rag.vector_store import search_knowledge_base, search_document_chunks, get_supabase_client
from ai_core.rag.crag_corrector import is_retrieval_sufficient
from ai_core.rag.web_evidence import web_evidence
from ai_core.rag.self_rag import self_reflect
from ai_core.rag.case_text_fallback import search_case_text, answer_date_question, content_tokens
from ai_core.router.domain_gate import greeting_reply
from ai_core.rag.legal_scope import in_scope, suggestions_for, OUT_MSG
from ai_core.rag.section_map import mapping_note
from ai_core.rag.statutes import explicit_lookup, find_sections, statute_sources, statute_text, statute_evidence
from ai_core.router.multi_question import split_questions, merge_answers
from ai_core.formatting.grounding import ground_answer
from ai_core.llm_gateway import call_llm, is_llm_failure
from ai_core.formatting.answer_style import STYLE_GUIDE, tidy_answer
from ai_core.trustagent.claim_extractor import extract_claims
from ai_core.evaluation.llm_judge import (
    judge_claims_against_evidence,
    STATE_GROUNDED, STATE_PARTIALLY_GROUNDED, STATE_CONTRADICTED,
    STATE_NO_EVIDENCE_FOUND, STATE_RETRIEVAL_INSUFFICIENT, STATE_VERIFICATION_PENDING,
)
from ai_core.trustagent.corrector import suggest_department_and_helpline, filter_supported_claims_answer
from ai_core.trustagent.citations import strip_invalid_bracket_citations, check_citations
from trust_log.hash_chain import build_log_entry, get_last_hash, save_log_entry
from backend.auth.supabase_auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)
_ctx = threading.local()  # quiet=True while one part of a multi-question message runs (saved once, merged)

# Owner column in `cases` (set CASE_OWNER_COLUMN="" only if your table has none; then fix the schema).
CASE_OWNER_COLUMN = os.getenv("CASE_OWNER_COLUMN", "user_id")
LANGUAGE_INSTRUCTION = "Detect whether the question is in English, Hindi, or Hinglish and respond in the SAME language/style."
LENGTH_INSTRUCTION = "Keep it as short as the question allows: 2-4 lines for simple questions, a few tidy lines for complex ones."
LLM_DOWN_MSG = "The AI service is busy right now. Please try again in a few seconds."

VERDICT_LABEL = {
    "supported": "verified", "partially_supported": "partial", "contradicted": "contradicted",
    "unverified": "unverified", "verification_pending": "pending",
    STATE_GROUNDED: "verified", STATE_PARTIALLY_GROUNDED: "partial", STATE_CONTRADICTED: "contradicted",
    STATE_NO_EVIDENCE_FOUND: "unverified", STATE_RETRIEVAL_INSUFFICIENT: "unverified",
    STATE_VERIFICATION_PENDING: "pending",
}
META_SUMMARY_PATTERNS = [
    r"\bsummar(y|ize|ise)\b", r"\bwhat is this (document|file|pdf|case)\b", r"\bis this a case\b",
    r"\bwhat'?s this about\b", r"\bbtao.*kya hai\b", r"\bkya hai.*file\b", r"\bsummary\s+btao\b", r"\bsaransh\b",
]
_HI_WORDS = ["kya", "kaun", "kaunsa", "kaunse", "kaunsi", "hai", "hain", "mein", "me", "ne", "ko", "se", "diye", "diya",
             "btao", "batao", "kare", "karein", "rakha", "rakhi", "mera", "meri", "mere", "kab", "hui", "iski", "isme", "tarikh"]
_PERSONAL = re.compile(r"\b(my|me|i|we|our|mera|meri|mere|mujhe|hamara|hamare|humne)\b", re.I)
_TOC = re.compile(r"\.{6,}")  # table-of-contents dotted lines


class QueryRequest(BaseModel):
    query: str
    case_id: str | None = None
    session_id: str | None = None


# ----------------------------------------------------------------------------- helpers
def is_meta_summary_query(query: str) -> bool:
    return any(re.search(p, query.lower()) for p in META_SUMMARY_PATTERNS)


def is_hindi_or_hinglish(query: str) -> bool:
    return bool(re.search(r"[ऀ-ॿ]", query)) or any(re.search(rf"\b{w}\b", query.lower()) for w in _HI_WORDS)


def general_legal_answer(query, model, audience, history=""):
    hist = f"PREVIOUS MESSAGES (context only, never invent beyond this):\n{history}\n" if history else ""
    return call_llm(model, f"""You are a legal-information assistant for Indian law (Bharatiya Nyaya Sanhita (BNS) 2023, BNSS 2023, BSA 2023, IPC historical, CrPC, civil law, court procedure).
{LANGUAGE_INSTRUCTION}
{LENGTH_INSTRUCTION}
{AUDIENCE_INSTRUCTIONS[audience]}
{STYLE_GUIDE}
If the user describes a personal situation, answer in this order: (1) one caring sentence, (2) what the law generally
provides, (3) practical next steps, (4) which authority or helpline to approach. Never invent section numbers.
{hist}
CRITICAL LEGAL SAFETY RULES:
1. Do NOT invent, guess, or hallucinate statutory section numbers, case citations, or penalties.
2. If you cannot confirm an exact section number with certainty, say: "I could not verify the exact statutory provision from the available legal sources."
3. In criminal law, note that the Bharatiya Nyaya Sanhita (BNS), 2023 is in force from 1 July 2024, replacing the IPC, 1860.
4. For fine/sentence figures add: "Please verify the exact current figure from the latest BNS text."
5. For an emergency/personal-safety matter include the relevant official helpline (Police 112, Women 181, Cyber Crime 1930, Child 1098, NALSA Legal Aid 15100).

QUESTION: {query}

ANSWER:""")


def generate_suggestions(query, answer, model):
    return suggestions_for(query)


def get_recent_history(session_id, current_case_id=None, limit=4):
    if not session_id:
        return ""
    client = get_supabase_client()
    try:
        if current_case_id:
            sess = client.table("chat_sessions").select("case_id").eq("id", session_id).execute()
            sc = sess.data[0].get("case_id") if sess.data else None
            if sc and str(sc).lower() != str(current_case_id).lower():
                return ""
        res = (client.table("chat_messages").select("role, content").eq("session_id", session_id)
               .order("created_at", desc=True).limit(limit).execute())
        return "\n".join(f"{m['role'].upper()}: {m['content'][:150]}" for m in reversed(res.data))
    except Exception:
        return ""


def ensure_valid_session(session_id, user_id, fallback_title, case_id=None):
    client = get_supabase_client()
    if session_id:
        res = client.table("chat_sessions").select("id, user_id, case_id").eq("id", session_id).execute()
        if res.data and res.data[0]["user_id"] == user_id:
            sc = res.data[0].get("case_id")
            if case_id and sc and str(sc).lower() != str(case_id).lower():
                client.table("chat_sessions").update({"case_id": case_id}).eq("id", session_id).execute()
            return session_id
    return client.table("chat_sessions").insert(
        {"user_id": user_id, "title": fallback_title[:40], "case_id": case_id}).execute().data[0]["id"]


def save_message(session_id, role, content, sources=None):
    if not session_id or getattr(_ctx, "quiet", False):
        return
    client = get_supabase_client()
    client.table("chat_messages").insert(
        {"session_id": session_id, "role": role, "content": content, "sources": sources or []}).execute()
    client.table("chat_sessions").update({"updated_at": "now()"}).eq("id", session_id).execute()


def link_document_to_session(session_id, case_id, filename):
    if session_id:
        get_supabase_client().table("chat_sessions").update(
            {"case_id": case_id, "case_filename": filename}).eq("id", session_id).execute()


def _load_case(client, case_id: str, user_id: str):
    """Fetch the case row ONLY if it belongs to this user."""
    q = client.table("cases").select("filename, summary, status, case_text").eq("id", case_id)
    if CASE_OWNER_COLUMN:
        q = q.eq(CASE_OWNER_COLUMN, user_id)
    res = q.execute()
    return res.data[0] if res.data else None


def _reply(session_id, label, answer, save=True, sources=None, **extra):
    """Standard response; `extra` overrides any default key."""
    if save:
        save_message(session_id, "assistant", answer, sources=sources)
    return {"answer": answer, "conclusion": None, "verified": False, "sources": sources or [], "usefulness": "low",
            "session_id": session_id, "routing_label": label, **extra}


# ----------------------------------------------------------------------------- real pages, summary sampling
_PAGES_CACHE: dict[str, list] = {}
_SUMMARIES: dict[str, str] = {}


def _load_pages(client, case_id: str):
    """[(page_number, text)] from document_chunks (case_text has no page markers). Cached; empty never cached."""
    if case_id in _PAGES_CACHE:
        return _PAGES_CACHE[case_id]
    try:
        res = (client.table("document_chunks").select("page_number, chunk_text")
               .eq("case_id", case_id).order("page_number").limit(3000).execute())
        by_page: dict[int, list[str]] = {}
        for r in res.data or []:
            if r.get("page_number") is not None:
                by_page.setdefault(int(r["page_number"]), []).append(r.get("chunk_text") or "")
    except Exception as e:  # noqa: BLE001
        logger.warning("load pages failed: %s", type(e).__name__)
        return None
    pages = [(pn, "\n".join(t)) for pn, t in sorted(by_page.items())]
    if not pages:
        return None
    if len(_PAGES_CACHE) > 20:
        _PAGES_CACHE.clear()
    _PAGES_CACHE[case_id] = pages
    return pages


def _spread(t: str, n: int = 8, w: int = 1100) -> str:
    """n slices spread over the WHOLE text (not just the first pages) for summaries."""
    if len(t) <= n * w:
        return t
    step = (len(t) - w) // (n - 1)
    return "\n...\n".join(t[i * step: i * step + w] for i in range(n))


# ----------------------------------------------------------------------------- retrieval
_INDEXING: set[str] = set()
_INDEXING_LOCK = threading.Lock()


def _index_in_background(case_id: str, case_text: str):
    """Self-heal: build document_chunks for this case without blocking the user."""
    with _INDEXING_LOCK:
        if case_id in _INDEXING:
            return
        _INDEXING.add(case_id)

    def _job():
        try:
            from ai_core.rag.document_chunker import chunk_text_into_pages
            logger.info("background index case_id=%s chunks=%s", case_id, chunk_text_into_pages(case_text, case_id))
        except Exception as e:  # noqa: BLE001
            logger.warning("background index failed case_id=%s err=%s", case_id, type(e).__name__)
        finally:
            with _INDEXING_LOCK:
                _INDEXING.discard(case_id)

    threading.Thread(target=_job, daemon=True).start()


def _rrf(lists: list[list[dict]], limit: int = 8, k: int = 60) -> list[dict]:
    scores, items = {}, {}
    for lst in lists:
        for rank, c in enumerate(lst):
            key = (c.get("page_number"), (c.get("chunk_text") or "")[:100])
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            items.setdefault(key, c)
    return [items[key] for key in sorted(scores, key=scores.get, reverse=True)[:limit]]


def _hybrid_retrieve(query: str, case_id: str, case_text: str, pages=None):
    """(chunks, info) from vector search + lexical search over the whole file, RRF-fused. Never raises."""
    sem, vec_ok = [], True
    try:
        sem = search_document_chunks(embed_text(query, task_type="RETRIEVAL_QUERY"), case_id,
                                     match_count=8, query_text=query) or []
        sem = [c for c in sem if str(c.get("case_id", case_id)).lower() == str(case_id).lower()]
    except Exception as e:  # noqa: BLE001
        vec_ok = False
        logger.warning("semantic retrieval failed: %s", type(e).__name__)
    lex = search_case_text(case_text, query, k=4, pages=pages) if (case_text or pages) else []
    if not sem and case_text:
        _index_in_background(case_id, case_text)
    fused = [c for c in _rrf([sem, lex], limit=10) if not _TOC.search(c.get("chunk_text") or "")][:8]
    out, total = [], 0
    for c in fused:  # cap evidence size (fast prompts, free-tier token limits)
        n = len(c.get("chunk_text") or "")
        if total + n > 9000 and out:
            break
        out.append(c)
        total += n
    scores = [float(c.get("similarity", 0) or 0) for c in sem]
    return out, {"semantic": len(sem), "lexical": len(lex), "semantic_ok": vec_ok,
                 "top_semantic": max(scores) if scores else None}


def _loc(c: dict, idx: int) -> str:
    return f"Page {c['page_number']}" if c.get("page_number") else f"Section {idx + 1}"


def _evidence_text(chunks: list[dict]) -> str:
    return "\n\n".join(f"[{_loc(c, i)}]\n{c.get('chunk_text', '')}" for i, c in enumerate(chunks))


# ----------------------------------------------------------------------------- sources contract
_CLAIM_LABEL = {"SUPPORTED": "verified", "PARTIALLY_SUPPORTED": "partial", "CONTRADICTED": "contradicted"}


def _claim_page_status(claim_verdicts) -> dict:
    rank, out = {"verified": 3, "partial": 2, "contradicted": 1}, {}
    for cv in claim_verdicts or []:
        lab = _CLAIM_LABEL.get(cv.get("verdict"))
        for p in (cv.get("page_numbers") or []) if lab else []:
            if rank[lab] > rank.get(out.get(p), 0):
                out[p] = lab
    return out


def build_document_sources(filename: str, chunks: list[dict], answer: str, claim_verdicts, verdict_state) -> list[dict]:
    """One entry per page/section actually used; never blank, never 'everything unverified'."""
    cited = {int(n) for n in re.findall(r"\[Page\s*(\d+)\]", answer or "", re.I)}
    cs = _claim_page_status(claim_verdicts)

    def pick(pred):
        seen, out = set(), []
        for i, c in enumerate(chunks):
            key = c.get("page_number") or f"s{i}"
            if key not in seen and pred(c):
                seen.add(key)
                out.append((i, c))
        return out

    chosen = pick(lambda c: c.get("page_number") in cited or c.get("page_number") in cs) or pick(lambda c: True)[:3]
    sources = []
    for i, c in chosen:
        pg = c.get("page_number")
        if pg in cs:
            status = cs[pg]
        elif verdict_state == STATE_VERIFICATION_PENDING:
            status = "pending"
        elif pg in cited:
            status = {STATE_GROUNDED: "verified", STATE_PARTIALLY_GROUNDED: "partial"}.get(verdict_state, "unverified")
        else:
            status = "unverified"
        s = {"name": f"{filename} — {_loc(c, i)}", "type": "document", "url": None, "verification_status": status,
             "jurisdiction": None, "page": pg, "excerpt": (c.get("chunk_text") or "")[:500]}
        if not pg:
            s["section"] = _loc(c, i)
        sources.append(s)
    return sources


# ----------------------------------------------------------------------------- post steps (parallel)
def _post_steps(query, answer, evidence, model, want_dept):
    def safe(fut, default):
        try:
            return fut.result(timeout=45)
        except Exception as e:  # noqa: BLE001
            logger.warning("post-step failed: %s", type(e).__name__)
            return default

    with ThreadPoolExecutor(max_workers=3) as ex:
        f_ref = ex.submit(self_reflect, query, answer, evidence)
        f_sug = ex.submit(generate_suggestions, query, answer, model)
        f_dep = ex.submit(suggest_department_and_helpline, query, call_llm) if want_dept else None
        return (safe(f_ref, {"usefulness": "medium", "conclusion": None, "conclusion_needed": False}),
                safe(f_sug, []), safe(f_dep, None) if f_dep else None)


def _plain(key: str, query: str) -> str:
    hi = is_hindi_or_hinglish(query)
    if key == "no_evidence":
        return (f"Is document me '{query.strip()}' se jude koi supporting evidence nahi mile." if hi
                else f"No supporting evidence was found in the uploaded document regarding {query.strip()}.")
    return ("Is sawal ka bharosemand jawab dene ke liye document se zaroori hissa nahi mil paya. "
            "Kripya sawal thoda aur specific karke poochhiye." if hi else
            "I could not find a passage in this document that reliably answers that. "
            "Try rephrasing with a name, date or keyword from the document.")


# ----------------------------------------------------------------------------- endpoint
@router.post("/ask")
def ask_legal_question(request: QueryRequest, response: Response, user=Depends(get_current_user)):
    request_id, t0 = uuid.uuid4().hex[:12], time.perf_counter()
    try:
        parts = split_questions(request.query)
        result = (_handle_multi(request, user.id, parts, request_id) if len(parts) > 1
                  else _handle_ask(request, user.id, request_id=request_id))
        result["request_id"] = request_id
        result["latency_ms"] = int((time.perf_counter() - t0) * 1000)
        logger.info("chat ask done request_id=%s routing=%s verdict=%s sources=%d ms=%d", request_id,
                    result.get("routing_label", "?"), result.get("verdict_state", "?"),
                    len(result.get("sources") or []), result["latency_ms"])
        return result
    except Exception as e:  # noqa: BLE001
        logger.exception("chat ask failed request_id=%s error_type=%s", request_id, type(e).__name__)
        response.status_code = 500
        return {"answer": "Something went wrong. Please try again.", "verified": False,
                "sources": [], "error": True, "request_id": request_id}


def _handle_multi(request: QueryRequest, user_id: str, parts: list[str], request_id: str | None = None):
    """Several questions in one message: answer each on its own (in parallel), then merge into one reply."""
    query = (request.query or "").strip()
    safety = check_input_safety(query)
    if not safety["is_safe"]:
        return {"blocked": True, "reason": safety["reason"]}
    session_id = ensure_valid_session(request.session_id, user_id, query, case_id=request.case_id)
    save_message(session_id, "user", query)

    def one(part):
        _ctx.quiet = True  # the user message and the merged answer are saved once, below
        try:
            return _handle_ask(QueryRequest(query=part, case_id=request.case_id, session_id=session_id), user_id, request_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("multi part failed: %s", type(e).__name__)
            return {"answer": "Something went wrong with this question. Please ask it again.", "verified": False}
        finally:
            _ctx.quiet = False

    with ThreadPoolExecutor(max_workers=len(parts)) as ex:
        results = list(ex.map(one, parts))
    merged = merge_answers(parts, results, STATE_PARTIALLY_GROUNDED)
    merged["session_id"] = session_id
    save_message(session_id, "assistant", merged["answer"], sources=merged["sources"])
    return merged


def _handle_ask(request: QueryRequest, user_id: str, request_id: str | None = None):
    query = (request.query or "").strip()
    safety = check_input_safety(query)
    if not safety["is_safe"]:
        return {"blocked": True, "reason": safety["reason"]}

    session_id = ensure_valid_session(request.session_id, user_id, query, case_id=request.case_id)
    save_message(session_id, "user", query)
    history = get_recent_history(session_id, current_case_id=request.case_id)
    if not request.case_id and not in_scope(query):
        return _reply(session_id, "OUT_OF_DOMAIN", OUT_MSG, usefulness=None, verdict_state="NOT_APPLICABLE", mode="refused")
    model = choose_model(query)
    has_document = bool(request.case_id)
    intent = classify_intent(query, has_document)
    label = intent.get("label", "GENERAL_LAW")
    audience = intent.get("audience", "student_public")
    doc_label = label in ("CASE_SPECIFIC", "MIXED")

    if label == "GREETING":
        return _reply(session_id, label, greeting_reply(is_hindi_or_hinglish(query)), usefulness=None,
                      verdict_state="NOT_APPLICABLE", mode="greeting", suggestions=[
                          "What is the punishment for theft under BNS?",
                          "My landlord is not returning my deposit, what can I do?", "How do I file an FIR?"])
    if label == "OUT_OF_DOMAIN":
        return _reply(session_id, label, REFUSAL_MESSAGE, usefulness=None, verdict_state="NOT_APPLICABLE", mode="refused")

    client = get_supabase_client()
    filename, doc_status, case_text, row = None, "ready", "", None
    if has_document:
        row = _load_case(client, request.case_id, user_id)
        if row:
            filename = row.get("filename") or "Uploaded Document"
            doc_status = row.get("status") or "ready"
            case_text = row.get("case_text") or ""
            link_document_to_session(session_id, request.case_id, filename)
        elif doc_label:
            return _reply(session_id, label, "The requested document could not be found. "
                          "Please select or re-upload a valid document.", no_documentary_evidence_found=True)

    if doc_label and row:  # indexing status gates
        if doc_status == "processing":
            return _reply(session_id, label, "Document is still being indexed. Please wait a moment and try again.",
                          indexing_in_progress=True)
        if doc_status == "failed":
            return _reply(session_id, label, "Document is not indexed correctly or indexing failed. "
                          "Please re-upload the document.", indexing_failed=True)

    # ---- META-SUMMARY: summarise slices of the WHOLE file (cached), else the stored summary
    if doc_label and row and is_meta_summary_query(query):
        summary = _SUMMARIES.get(request.case_id) or ""
        if not summary and case_text:
            try:
                from ai_core.rag.summarizer import summarize_case
                summary = summarize_case(_spread(case_text)) or ""
                if summary and not is_llm_failure(summary):
                    _SUMMARIES[request.case_id] = summary
                else:
                    summary = ""
            except Exception as e:  # noqa: BLE001
                logger.warning("summary generation failed: %s", type(e).__name__)
        if not summary:
            summary = (row.get("summary") or "").strip()
            summary = "" if summary == "Summary generation in progress." else summary
        if summary and not is_llm_failure(summary):
            src = [{"name": f"{filename} — Summary", "type": "document", "url": None,
                    "verification_status": "unverified", "jurisdiction": None,
                    "section": "Full-document summary", "excerpt": summary[:500]}]
            return _reply(session_id, label, f"{summary}\n\n📄 Source: {filename} (full-document summary)",
                          sources=src, usefulness="high", verdict_state=STATE_VERIFICATION_PENDING)

    # ---- DATE / HEARING / YEAR questions: exact extraction, no LLM
    if label == "CASE_SPECIFIC" and row and case_text:
        dated = answer_date_question(query, case_text, hinglish=is_hindi_or_hinglish(query),
                                     pages=_load_pages(client, request.case_id))
        if dated is not None:
            events = dated["events"]
            src = [{"name": f"{filename} — Page {e['page']}" if e.get("page") else f"{filename} — Document text",
                    "type": "document", "url": None, "verification_status": "verified", "jurisdiction": None,
                    "page": e.get("page"), "excerpt": e["sentence"][:300],
                    **({} if e.get("page") else {"section": "Document text"})} for e in events[:8]]
            return _reply(session_id, label, dated["answer"], sources=src, usefulness="high" if events else "low",
                          verified=bool(events), verdict_state=STATE_GROUNDED if events else STATE_NO_EVIDENCE_FOUND,
                          claim_verdicts=[], retrieval_method="exact_extraction", suggestions=[],
                          no_documentary_evidence_found=not events)

    # ---- gather DOCUMENT evidence
    document_evidence, document_chunks = "", []
    general_evidence, general_sources, from_crag = "", [], False

    if doc_label and row:
        document_chunks, info = _hybrid_retrieve(query, request.case_id, case_text,
                                                 pages=_load_pages(client, request.case_id))
        logger.info("[RETRIEVAL] request_id=%s case_id=%s chunks=%d info=%s pages=%s", request_id, request.case_id,
                    len(document_chunks), info, [c.get("page_number") for c in document_chunks])
        if document_chunks:
            weak = info["lexical"] == 0 and info["top_semantic"] is not None and info["top_semantic"] < 0.15
            if weak and label == "CASE_SPECIFIC":
                return _reply(session_id, label, _plain("no_evidence", query), no_documentary_evidence_found=True,
                              verdict_state=STATE_NO_EVIDENCE_FOUND)
            document_evidence = _evidence_text(document_chunks)
        elif label == "CASE_SPECIFIC":
            return _reply(session_id, label, _plain("retrieval", query), retrieval_insufficient=True,
                          verdict_state=STATE_RETRIEVAL_INSUFFICIENT)

    # ---- gather GENERAL evidence: official statute table -> knowledge base -> real web pages
    if label in ("GENERAL_LAW", "MIXED"):
        rows = find_sections(client, query)
        if explicit_lookup(query):  # "section 303 BNS": answer ONLY from the official text, never from model memory
            hi = is_hindi_or_hinglish(query)
            if not rows:
                ex = explicit_lookup(query)
                msg = (f"{ex[0]} Section {ex[1]} abhi hamare verified statute database me nahi hai, isliye main andaza nahi lagaunga."
                       if hi else f"{ex[0]} Section {ex[1]} is not in our verified statute database yet, so I won't guess it. "
                                  "Please check the official text on India Code.")
                msg += mapping_note(client, ex[0], ex[1], hi)
                return _reply(session_id, label, msg, verdict_state=STATE_NO_EVIDENCE_FOUND)
            r = rows[0]
            head = f"📌 {r['act_name']} — Section {r['section']}" + (f": {r['heading']}" if r.get("heading") else "")
            body = (f"{head}\n\n{statute_text(r)}\n\n📄 Verbatim from the source PDF ({r['source_url'].split('/')[2]}), page {r.get('page')}."
                    + mapping_note(client, r["act"], r["section"], hi))
            return _reply(session_id, label, body,
                          sources=statute_sources(rows), usefulness="high", verified=True, verdict_state=STATE_GROUNDED)
        if rows:
            general_evidence = "\n\n".join(f"{r['act_name']} Section {r['section']} ({r.get('heading')}): {statute_evidence(r)}" for r in rows)
            general_sources += statute_sources(rows, status="pending")
        try:
            matches = search_knowledge_base(embed_text(query, task_type="RETRIEVAL_QUERY"), query, match_count=3)
        except Exception as e:  # noqa: BLE001
            logger.warning("kb search failed: %s", type(e).__name__)
            matches = []
        if not rows and not is_retrieval_sufficient(matches):
            external = web_evidence(query, lambda p: call_llm(model, p))   # real page text + quoted passages
            matches, from_crag = ([external] if external else []), bool(external)
        if matches:
            general_evidence = (general_evidence + "\n" if general_evidence else "") + "\n".join(m.get("full_text", "") for m in matches)
            for m in matches:
                if m.get("source_type") == "external_crag":
                    for link in m.get("source_links", [{"title": m.get("display_name", "Web source"), "url": ""}])[:2]:
                        general_sources.append({"name": (link.get("title") or "Web source")[:60], "type": "web",
                                                "url": link.get("url") or None, "verification_status": "external",
                                                "jurisdiction": "India", "section": link.get("organization") or "Web",
                                                "excerpt": link.get("quote") or ""})
                else:
                    general_sources.append({"name": m.get("display_name") or m.get("case_name") or "Legal source",
                                            "type": "statute" if "act_name" in m else "judgment", "url": None,
                                            "verification_status": "pending", "jurisdiction": m.get("jurisdiction_type")})

    if not document_evidence and not general_evidence:
        return _general_fallback(query, model, audience, session_id, history)

    evidence = (f"=== UPLOADED CASE FACTS ({filename}) ===\n{document_evidence}\n\n"
                f"=== APPLICABLE INDIAN STATUTORY LAW & PRECEDENTS ===\n{general_evidence}"
                if label == "MIXED" else (document_evidence or general_evidence))

    hist = f"CONVERSATION CONTEXT (never invent beyond the evidence below):\n{history}\n\n" if history else ""
    head = f"{LANGUAGE_INSTRUCTION}\n{LENGTH_INSTRUCTION}\n{AUDIENCE_INSTRUCTIONS[audience]}\n{STYLE_GUIDE}\n{hist}"
    tail = f"EVIDENCE:\n{evidence}\n\nCURRENT QUERY: {query}\n\nANSWER:"
    if label == "CASE_SPECIFIC":
        prompt = (f"You are NyayaPramaan, an evidence-grounded legal assistant for Indian case files.\n{head}"
                  f"STRICT CASE-SPECIFIC EVIDENCE CONTRACT:\n"
                  f"1. Answer ONLY from the evidence below. No outside information, no model memory.\n"
                  f"2. Cite the page after each fact like [Page 3]. Use only pages shown in the evidence headers.\n"
                  f"3. Do NOT invent documents, dates, names or findings that are not in the evidence.\n"
                  f"4. If a person/document is only mentioned, say only what is written.\n"
                  f"5. If the evidence does not answer the question, reply EXACTLY: "
                  f"'No supporting evidence was found in the uploaded document regarding {query}.'\n\n{tail}")
    elif label == "MIXED":
        prompt = (f"{head}Answer in three short parts using the evidence ONLY:\n"
                  f"📄 Case facts (cite [Page N]) / ⚖️ Legal rule / 👉 How it applies.\n"
                  f"Never mix case facts with statute text; never invent facts or section numbers.\n\n{tail}")
    else:
        prompt = (f"{head}1. Answer the CURRENT query using ONLY the evidence below.\n"
                  f"2. Do NOT invent section numbers, cases or findings that are not in the evidence.\n"
                  f"3. BNS 2023 is in force from 1 July 2024.\n\n{tail}")

    draft = call_llm(model, prompt)
    if is_llm_failure(draft):
        return _reply(session_id, label, LLM_DOWN_MSG, save=False, verdict_state=STATE_VERIFICATION_PENDING,
                      llm_unavailable=True)

    # ---- TrustAgent: claim extraction + LLM-as-judge against the evidence
    claims, extraction_ok = extract_claims(draft)
    judgment = judge_claims_against_evidence(query=query, evidence=evidence, draft_answer=draft,
                                             claims=claims if (extraction_ok and claims) else [])
    verdict_state = judgment.get("overall_verdict", STATE_VERIFICATION_PENDING)
    supported, unsupported = judgment.get("supported_claims", []), judgment.get("unsupported_claims", [])
    claim_verdicts = judgment.get("claim_verdicts", [])

    retrieved_pages = {int(c["page_number"]) for c in document_chunks if c.get("page_number") is not None}
    for cv in claim_verdicts:  # a claim may only point at pages that were really retrieved
        ok = set()
        for page in cv.get("page_numbers") or []:
            try:
                if int(page) in retrieved_pages:
                    ok.add(int(page))
            except (TypeError, ValueError):
                pass
        cv["page_numbers"] = sorted(ok)

    final_draft = draft
    if label == "CASE_SPECIFIC" or from_crag:  # keep only the claims the evidence supports
        if verdict_state == STATE_PARTIALLY_GROUNDED:
            if not supported:
                verdict_state = STATE_NO_EVIDENCE_FOUND
            elif unsupported:
                final_draft = filter_supported_claims_answer(draft, supported, unsupported, evidence, query)
        if label == "CASE_SPECIFIC" and verdict_state == STATE_NO_EVIDENCE_FOUND:
            return _reply(session_id, label, _plain("no_evidence", query), no_documentary_evidence_found=True,
                          verdict_state=STATE_NO_EVIDENCE_FOUND)
    if from_crag and verdict_state in (STATE_NO_EVIDENCE_FOUND, STATE_CONTRADICTED):
        return _general_fallback(query, model, audience, session_id, history)

    # ---- final text + sources
    final_answer = redact_pii(final_draft)
    if retrieved_pages:
        final_answer = strip_invalid_bracket_citations(final_answer, check_citations(final_answer, retrieved_pages)["invalid"])
    final_answer = tidy_answer(final_answer)
    if label == "GENERAL_LAW":  # drop any section/number/Act that is not in the evidence
        final_answer = ground_answer(final_answer, evidence)
        if not final_answer:
            return _general_fallback(query, model, audience, session_id, history)

    doc_sources = (build_document_sources(filename, document_chunks, final_answer, claim_verdicts, verdict_state)
                   if document_chunks else [])
    for s in general_sources:
        if s.get("verification_status") in ("pending", "external"):
            s["verification_status"] = VERDICT_LABEL.get(verdict_state, "unverified")
    sources = doc_sources + general_sources

    reflection, suggestions, dept = _post_steps(
        query, final_answer, evidence, model,
        want_dept=label in ("GENERAL_LAW", "MIXED") and bool(_PERSONAL.search(query)))
    if label == "GENERAL_LAW" and reflection.get("conclusion"):
        reflection["conclusion"] = ground_answer(reflection["conclusion"], evidence) or None
    accurate = judgment.get("is_accurate", True)
    verified = verdict_state in (STATE_GROUNDED, STATE_PARTIALLY_GROUNDED) and accurate
    _log(query, final_answer, model, verified)
    return _reply(session_id, label, final_answer, sources=sources,
                  conclusion=reflection.get("conclusion") if reflection.get("conclusion_needed", True) else None,
                  usefulness=reflection.get("usefulness", "medium"), verified=verified, verdict_state=verdict_state,
                  claim_verdicts=claim_verdicts, quality_note="" if accurate or not judgment.get("issue") else f"Quality-check note: {judgment['issue']}",
                  department_suggestion=dept, model_used=model, suggestions=suggestions)


def _no_source(query, session_id):
    hi = is_hindi_or_hinglish(query)
    msg = ("Is sawal ke liye mujhe koi official source nahi mila, isliye main andaze se jawab nahi dunga. India Code "
           "(indiacode.nic.in) par dekhein ya vakil se poochhein.\n\n☎️ Helplines: Emergency 112 · NALSA Legal Aid 15100 · "
           "Women 181 · Cyber Crime 1930 · Child 1098" if hi else
           "I could not find an official source for this, so I won't answer from memory. Please check India Code "
           "(indiacode.nic.in) or ask a lawyer.\n\n☎️ Helplines: Emergency 112 · NALSA Legal Aid 15100 · Women 181 · "
           "Cyber Crime 1930 · Child 1098")
    return _reply(session_id, "GENERAL_LAW", msg, usefulness=None, verdict_state="NOT_APPLICABLE", mode="no_source")


def _general_fallback(query, model, audience, session_id, history):
    if os.getenv("ALLOW_MEMORY_GUIDANCE", "0") != "1":     # default: never answer a legal question from model memory
        return _no_source(query, session_id)
    ans = general_legal_answer(query, model, audience, history=history)
    if is_llm_failure(ans):
        return _reply(session_id, "GENERAL_LAW", LLM_DOWN_MSG, save=False, verdict_state=STATE_VERIFICATION_PENDING,
                      llm_unavailable=True)
    ans = ground_answer(tidy_answer(redact_pii(ans)))  # no evidence -> sections, days, amounts, Acts are removed
    if not ans:
        ans = ("Mujhe iske specific provisions ka verified source nahi mila. Kripya India Code par official text dekhein "
               "ya kisi vakil se poochhein." if is_hindi_or_hinglish(query) else
               "I could not find a verified source for the specifics of this. Please check the official text on India Code or ask a lawyer.")
    reflection, suggestions, _ = _post_steps(query, ans, "(general knowledge, no specific evidence)", model, want_dept=False)
    if reflection.get("conclusion"):
        reflection["conclusion"] = ground_answer(reflection["conclusion"]) or None
    _log(query, ans, model, verified=False)
    card = [{"name": f"AI-generated guidance — {model.split('/')[-1]}", "type": "ai", "url": None,
             "verification_status": "unverified", "jurisdiction": None, "section": "No verified legal source found",
             "excerpt": "Written by the AI without a matching statute or judgment. Specific sections, deadlines, amounts "
                        "and Act names were removed because they could not be verified."}]
    return _reply(session_id, "GENERAL_LAW",
                  f"{ans}\n\nℹ️ General guidance — no verified source found. Please confirm with a lawyer or the official text.",
                  sources=card,
                  conclusion=reflection.get("conclusion") if reflection.get("conclusion_needed", True) else None,
                  usefulness=reflection.get("usefulness", "medium"), verdict_state="GENERAL_INFO",
                  mode="general_knowledge", model_used=model, suggestions=suggestions)


def _log(query, answer, model, verified):
    try:
        entry = build_log_entry({"query": query, "verified": verified, "model": model}, get_last_hash())
        save_log_entry(entry, query=query, response=answer, verified=verified, model_used=model)
    except Exception as e:  # noqa: BLE001  (audit-log failure must never break an answer)
        logger.warning("audit log failed: %s", type(e).__name__)


# ----------------------------------------------------------------------------- diagnostics
@router.get("/debug/case/{case_id}")
def debug_case(case_id: str, user=Depends(get_current_user)):
    """Why do my document follow-ups fail? Owner-only, counts only (no content)."""
    client = get_supabase_client()
    row = _load_case(client, case_id, user.id)
    if not row:
        return {"found": False}
    info = {"found": True, "status": row.get("status"), "case_text_chars": len(row.get("case_text") or ""),
            "has_summary": bool(row.get("summary"))}
    try:
        info["chunks_in_db"] = client.table("document_chunks").select("id", count="exact").eq(
            "case_id", case_id).limit(1).execute().count
    except Exception as e:  # noqa: BLE001
        info["chunks_in_db"] = f"error: {type(e).__name__}"
    try:
        client.rpc("match_document_chunks", {"query_embedding": [0.0] * 768, "target_case_id": case_id,
                                              "match_count": 1}).execute()
        info["rpc_match_document_chunks"] = "ok"
    except Exception as e:  # noqa: BLE001
        info["rpc_match_document_chunks"] = f"MISSING/ERROR: {str(e)[:120]}"
    return info


# ----------------------------------------------------------------------------- sessions
class SessionCreate(BaseModel):
    title: str = "New Chat"


class SessionUpdate(BaseModel):
    title: str | None = None
    pinned: bool | None = None


@router.post("/sessions")
def create_session(body: SessionCreate, user=Depends(get_current_user)):
    return get_supabase_client().table("chat_sessions").insert({"user_id": user.id, "title": body.title}).execute().data[0]


@router.get("/sessions")
def list_sessions(user=Depends(get_current_user)):
    return (get_supabase_client().table("chat_sessions").select("id, title, updated_at, pinned")
            .eq("user_id", user.id).order("pinned", desc=True).order("updated_at", desc=True).execute().data)


@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str, user=Depends(get_current_user)):
    client = get_supabase_client()
    info = (client.table("chat_sessions").select("case_id, case_filename")
            .eq("id", session_id).eq("user_id", user.id).execute())
    if not info.data:
        return {"messages": [], "case_id": None, "case_filename": None}
    msgs = (client.table("chat_messages").select("role, content, sources, created_at")
            .eq("session_id", session_id).order("created_at").execute().data)
    return {"messages": msgs, "case_id": info.data[0]["case_id"], "case_filename": info.data[0]["case_filename"]}


@router.patch("/sessions/{session_id}")
def update_session(session_id: str, body: SessionUpdate, user=Depends(get_current_user)):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if updates:
        get_supabase_client().table("chat_sessions").update(updates).eq("id", session_id).eq("user_id", user.id).execute()
    return {"updated": True}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, user=Depends(get_current_user)):
    get_supabase_client().table("chat_sessions").delete().eq("id", session_id).eq("user_id", user.id).execute()
    return {"deleted": True}