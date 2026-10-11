"""
Self-RAG — self-critique layer. Now also decides whether a conclusion
box genuinely adds value (skips it for already-short/direct answers to
avoid redundant "In Short" on every single response).
"""
import json
import re
from ai_core.llm_gateway import call_llm

REFLECTION_MODEL = "gemini/gemini-3.6-flash"


def self_reflect(query: str, answer: str, evidence: str) -> dict:
    prompt = f"""You just generated this ANSWER using the given EVIDENCE for
the QUERY. Respond with ONLY this JSON:
{{"usefulness": "high", "conclusion": "one clear sentence", "conclusion_needed": true}}

usefulness: "high"/"medium"/"low" based on how sufficient the evidence was.
conclusion: ONE short, direct sentence answering the user's core question.
conclusion_needed: false if the ANSWER itself is ALREADY short and direct
(e.g. under 3 sentences, no tables/lists) such that a separate "In Short"
box would just repeat it -- true otherwise (e.g. when the answer is a
table, a multi-paragraph explanation, or a list).

QUERY: {query}
ANSWER: {answer}
EVIDENCE: {evidence}

JSON:"""
    try:
        raw = call_llm(REFLECTION_MODEL, prompt)
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
        result = json.loads(cleaned)
        usefulness = result.get("usefulness", "medium")
        if usefulness not in ("high", "medium", "low"):
            usefulness = "medium"
        return {
            "usefulness": usefulness,
            "conclusion": result.get("conclusion", ""),
            "conclusion_needed": bool(result.get("conclusion_needed", True)),
        }
    except Exception:
        return {"usefulness": "medium", "conclusion": "", "conclusion_needed": False}


# ---------------------------------------------------------------------------------------------------------------
# Self-RAG style control loop (bounded to ONE extra round).
#
# After an answer has been generated and its claims judged against the evidence, decide whether the problem is
# "the answer says things the retrieved passages do not support" AND "the case file might contain support we did not
# retrieve". If so, search the SELECTED case again using the unsupported claims themselves as queries, and only
# regenerate if genuinely new, relevant passages were found. The regenerated answer is verified from scratch and is
# kept only if it is not worse than the first one.
# ---------------------------------------------------------------------------------------------------------------

_RETRY_STATES = ("PARTIALLY_GROUNDED", "NO_EVIDENCE_FOUND")
_STATE_RANK = {"GROUNDED": 4, "PARTIALLY_GROUNDED": 3, "VERIFICATION_PENDING": 2, "NO_EVIDENCE_FOUND": 1,
               "CONTRADICTED": 0, "RETRIEVAL_INSUFFICIENT": 0}
MAX_CLAIM_QUERIES = 3
MIN_NEW_CHUNK_COVERAGE = 0.5


def should_retry_retrieval(verdict_state: str, unsupported_claims: list[str], already_retried: bool) -> bool:
    return (not already_retried) and verdict_state in _RETRY_STATES and bool(unsupported_claims)


def retrieve_for_claims(unsupported_claims: list[str], search, seen_ids: set, k: int = 4) -> list[dict]:
    """New, relevant chunks of the selected case for claims the first pass could not support.
    `search(query_text, k)` must be bound to the authorised case. A chunk counts as relevant only if it matched the
    claim's wording well (lexical coverage) or contains an identifier from it."""
    found, seen = [], set(seen_ids)
    for claim in unsupported_claims[:MAX_CLAIM_QUERIES]:
        try:
            hits = search(claim, k)
        except Exception:
            continue
        for c in hits:
            key = str(c.get("id"))
            if c.get("id") is None or key in seen:
                continue
            if (c.get("lexical_coverage") or 0) >= MIN_NEW_CHUNK_COVERAGE or (c.get("identifier_match") or 0) > 0:
                seen.add(key)
                found.append(c)
    return found


def is_not_worse(new_state: str, old_state: str) -> bool:
    return _STATE_RANK.get(new_state, 0) >= _STATE_RANK.get(old_state, 0)


def is_better(new_state: str, old_state: str, new_removed: int = 0, old_removed: int = 0) -> bool:
    """Adopt the regenerated answer only if it is strictly better: a better verdict, or the same verdict with fewer
    claims removed. Equal-or-worse never replaces the first answer."""
    new_rank, old_rank = _STATE_RANK.get(new_state, 0), _STATE_RANK.get(old_state, 0)
    return new_rank > old_rank or (new_rank == old_rank and new_removed < old_removed)
