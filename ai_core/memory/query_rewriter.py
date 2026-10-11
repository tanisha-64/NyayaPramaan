"""
History-aware follow-up query rewriting.

Turns an elliptical follow-up ("and what about the penalty?", "uska page kaunsa hai?") into a standalone query
using the previous turns of THIS session. Rules that keep it safe:

* Previous turns are used only to resolve references. They are never evidence: the rewritten query goes to
  retrieval, and the answer prompt contains retrieved evidence only (see chat_router).
* The current message is never part of the history it is rewritten against.
* Rewriting is skipped (no LLM call, no drift) unless the message looks like a follow-up.
* The output is validated; on any doubt the ORIGINAL query is used.
"""
import re
from typing import Callable

REWRITE_MODEL = "groq/openai/gpt-oss-20b"
MAX_QUERY_CHARS = 300
MAX_USER_TURN_CHARS = 300
MAX_ASSISTANT_TURN_CHARS = 200
MAX_TURNS = 6   # messages, i.e. about 3 exchanges

_FOLLOWUP_STARTS = (
    "and ", "also ", "what about", "how about", "why", "how so", "then ", "so ", "but ", "what if",
    "can you explain", "explain that", "tell me more", "more about", "elaborate", "which one", "who ",
    "aur ", "or ", "phir", "uska", "uski", "uske", "iska", "iski", "iske", "unka", "unki", "unke",
    "wo ", "woh ", "us ", "is ", "kyun", "kyu ", "kaise", "aur kya",
)
_REFERENCE_WORDS = re.compile(
    r"\b(it|its|that|this|those|these|they|them|their|he|she|his|her|the same|above|earlier|previous|former|latter|"
    r"uska|uski|uske|iska|iski|iske|unka|unki|unke|wo|woh|yeh|ye|isme|usme|pehle)\b", re.IGNORECASE)
_STANDALONE_SIGNALS = re.compile(r"\b(section|dhara|article|bns|bnss|bsa|ipc|crpc|cpc)\s*\.?\s*\d+", re.IGNORECASE)


def looks_like_followup(query: str) -> bool:
    """Cheap deterministic gate. False positives cost one LLM call; false negatives just skip the rewrite."""
    q = (query or "").strip().lower()
    if not q:
        return False
    if _STANDALONE_SIGNALS.search(q) and len(q.split()) > 6:
        return False
    words = q.split()
    if len(words) <= 4:
        return True
    if any(q.startswith(s) for s in _FOLLOWUP_STARTS):
        return True
    return len(words) <= 12 and bool(_REFERENCE_WORDS.search(q))


def format_history_for_rewrite(turns: list[dict]) -> str:
    lines = []
    for t in turns[-MAX_TURNS:]:
        role = "USER" if t.get("role") == "user" else "ASSISTANT"
        limit = MAX_USER_TURN_CHARS if role == "USER" else MAX_ASSISTANT_TURN_CHARS
        content = re.sub(r"\s+", " ", str(t.get("content") or "")).strip()[:limit]
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _clean_rewrite(raw: str, original: str) -> str | None:
    text = (raw or "").strip().strip("`").strip()
    text = re.sub(r"^(rewritten|standalone)?\s*(query|question)?\s*:\s*", "", text, flags=re.IGNORECASE).strip()
    text = text.strip("\"' ")
    if not text or "\n" in text or len(text) > MAX_QUERY_CHARS:
        return None
    if text.lower().startswith(("i cannot", "i can't", "sorry", "as an ai", "i'm currently experiencing")):
        return None
    if len(text) < 3:
        return None
    return text


def rewrite_followup_query(query: str, turns: list[dict], llm: Callable[[str, str], str]) -> dict:
    """Returns {"query": effective_query, "rewritten": bool, "reason": str}. Never raises."""
    original = (query or "").strip()
    if not turns:
        return {"query": original, "rewritten": False, "reason": "no_history"}
    if not looks_like_followup(original):
        return {"query": original, "rewritten": False, "reason": "standalone"}

    history = format_history_for_rewrite(turns)
    if not history:
        return {"query": original, "rewritten": False, "reason": "no_history"}

    prompt = f"""Rewrite the LAST USER MESSAGE as one standalone question, resolving pronouns and omitted
subjects using the PREVIOUS CONVERSATION. The previous conversation is only for resolving references: it is NOT a
source of facts, and you must not add facts, names, dates or section numbers that the user did not say or that
are not needed to resolve a reference.
Rules:
- Keep the user's language (English, Hindi or Hinglish).
- If the message is already self-contained, return it unchanged.
- Output ONLY the rewritten question on a single line. No explanation, no quotes.

PREVIOUS CONVERSATION:
{history}

LAST USER MESSAGE: {original}

STANDALONE QUESTION:"""
    try:
        cleaned = _clean_rewrite(llm(REWRITE_MODEL, prompt), original)
    except Exception:
        return {"query": original, "rewritten": False, "reason": "llm_error"}
    if cleaned is None:
        return {"query": original, "rewritten": False, "reason": "invalid_output"}
    if cleaned.strip().lower() == original.lower():
        return {"query": original, "rewritten": False, "reason": "unchanged"}
    return {"query": cleaned, "rewritten": True, "reason": "rewritten"}
