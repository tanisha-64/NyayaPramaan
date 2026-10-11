"""
Corrective RAG (CRAG) for the selected-case retrieval path.

assess_retrieval()   - grades what was retrieved using measurable signals (never an LLM opinion):
                         top_similarity   best semantic (pgvector cosine) similarity among the chunks, if any
                         term_coverage    share of the question's content terms that appear in the top chunks
                         identifiers_ok   numbers in the question (registration no., year, amount) found verbatim
corrective_retrieve() - when the grade is not STRONG: (1) broaden the candidate set, (2) retrieve again with
                         LLM-generated alternative phrasings of the same question (handles Hinglish and
                         paraphrase), then re-grade. Bounded: at most one broaden and one expansion round.

Grades
  STRONG      enough of the question is covered by the evidence and semantic similarity (if known) is decent
  WEAK        something relevant-looking was found but coverage / similarity is low: answer only with caveats and
              let claim verification decide
  IRRELEVANT  semantic similarity is very low AND the evidence shares almost no terms with the question: abstain
  EMPTY       nothing retrieved

The numeric thresholds are heuristics, exposed as constants and logged with every request ([RETRIEVAL_DIAGNOSTICS])
so they can be calibrated against real traffic in staging. They are NOT claimed to be optimal.
"""
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Callable

from ai_core.rag.lexical import tokens

STRONG, WEAK, IRRELEVANT, EMPTY = "strong", "weak", "irrelevant", "empty"

IRRELEVANT_MAX_SIMILARITY = 0.15    # unchanged from the pre-CRAG abstention rule
IRRELEVANT_MAX_COVERAGE = 0.34
STRONG_MIN_COVERAGE = 0.60
STRONG_MIN_SIMILARITY = 0.35
TOP_N_FOR_COVERAGE = 3
WIDE_K = 10                          # final candidate cap after correction (keeps the evidence prompt bounded)
MAX_EXPANSIONS = 2


@dataclass
class RetrievalAssessment:
    quality: str
    top_similarity: float | None = None
    term_coverage: float | None = None
    identifiers_ok: bool | None = None
    missing_terms: list = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["missing_terms"] = d["missing_terms"][:8]
        return d


def _original_words(query: str, missing_stems: set[str]) -> list[str]:
    """The user's own words behind the missing stems (so messages say 'harassment', not 'harass')."""
    out, seen = [], set()
    for w in re.findall(r"\w+", query or "", flags=re.UNICODE):
        stem = tokens(w)
        if stem and stem[0] in missing_stems and stem[0] not in seen:
            seen.add(stem[0])
            out.append(w)
    return out


def _identifiers(query: str) -> set[str]:
    return {t for t in tokens(query) if t.isdigit() and len(t) >= 3}


def assess_retrieval(query: str, chunks: list[dict], extra_queries: list[str] | None = None) -> RetrievalAssessment:
    if not chunks:
        return RetrievalAssessment(EMPTY, reason="no chunks were retrieved for this case")

    sims = [c["similarity"] for c in chunks if isinstance(c.get("similarity"), (int, float))]
    top_sim = max(sims) if sims else None

    top_text_tokens = set()
    for c in chunks[:TOP_N_FOR_COVERAGE]:
        top_text_tokens.update(tokens(c.get("chunk_text", "")))

    best_cov, best_missing = None, []
    for q in [query] + list(extra_queries or []):
        q_terms = set(tokens(q))
        if not q_terms:
            continue
        missing = q_terms - top_text_tokens
        cov = 1 - len(missing) / len(q_terms)
        if best_cov is None or cov > best_cov:
            best_cov, best_missing = cov, _original_words(q, missing)

    ids = _identifiers(query)
    all_tokens = set()
    for c in chunks:
        all_tokens.update(tokens(c.get("chunk_text", "")))
    identifiers_ok = (ids <= all_tokens) if ids else None

    sim_low = top_sim is not None and top_sim < IRRELEVANT_MAX_SIMILARITY
    cov_low = best_cov is None or best_cov < IRRELEVANT_MAX_COVERAGE
    if sim_low and cov_low:
        return RetrievalAssessment(IRRELEVANT, top_sim, best_cov, identifiers_ok, best_missing,
                                   "very low semantic similarity and almost no shared terms with the question")
    if (best_cov is not None and best_cov >= STRONG_MIN_COVERAGE
            and (top_sim is None or top_sim >= STRONG_MIN_SIMILARITY) and identifiers_ok is not False):
        return RetrievalAssessment(STRONG, top_sim, best_cov, identifiers_ok, best_missing, "question terms are covered by the evidence")
    reasons = []
    if best_cov is None or best_cov < STRONG_MIN_COVERAGE:
        reasons.append("only part of the question's terms appear in the retrieved passages")
    if top_sim is not None and top_sim < STRONG_MIN_SIMILARITY:
        reasons.append("semantic similarity is modest")
    if identifiers_ok is False:
        reasons.append("a number named in the question was not found in any retrieved passage")
    return RetrievalAssessment(WEAK, top_sim, best_cov, identifiers_ok, best_missing, "; ".join(reasons) or "partial match")


def _merge(primary: list[dict], extra: list[dict], cap: int) -> tuple[list[dict], int]:
    """Union keeping `primary` order first; returns (merged[:cap], number of NEW chunks added)."""
    def key_of(c):
        return str(c["id"]) if c.get("id") is not None else f"{c.get('page_number')}|{(c.get('chunk_text') or '')[:80]}"

    seen = {key_of(c) for c in primary}
    merged = list(primary)
    added = 0
    for c in extra:
        key = key_of(c)
        if key in seen:
            continue
        seen.add(key)
        merged.append(c)
        added += 1
    return merged[:cap], added


def expand_query(query: str, llm: Callable[[str, str], str], model: str = "groq/openai/gpt-oss-20b") -> list[str]:
    """Up to MAX_EXPANSIONS alternative search phrasings (English) of the SAME question. Never raises."""
    prompt = f"""Rewrite this question about an Indian legal case file as up to {MAX_EXPANSIONS} alternative search queries in
English that would find the answer inside the document. Keep every name, number and date exactly as written. Do not add
facts, laws or names the question does not contain. Return ONLY a JSON array of short strings.

QUESTION: {query}

JSON:"""
    try:
        raw = llm(model, prompt)
        cleaned = re.sub(r"^```json\s*|\s*```$", "", (raw or "").strip())
        data = json.loads(cleaned)
        if not isinstance(data, list):
            return []
        out = []
        for item in data:
            if isinstance(item, str) and 3 <= len(item.strip()) <= 160 and item.strip().lower() != query.strip().lower():
                out.append(item.strip())
        return out[:MAX_EXPANSIONS]
    except Exception:
        return []


def corrective_retrieve(
    *,
    query: str,
    initial: list[dict],
    search: Callable[[str, int], list[dict]],      # (query_text, k) -> chunks for the SELECTED case only
    expand: Callable[[str], list[str]],
    k: int = 8,
) -> tuple[list[dict], RetrievalAssessment, list[dict]]:
    """Returns (chunks, assessment, actions). `search` must already be bound to one authorised case."""
    chunks = list(initial)
    assessment = assess_retrieval(query, chunks)
    actions: list[dict] = []
    if assessment.quality == STRONG:
        return chunks, assessment, actions

    # 1. broaden: same question, larger candidate set
    try:
        wide = search(query, WIDE_K)
        chunks, added = _merge(chunks, wide, WIDE_K)
        actions.append({"action": "broaden", "k": WIDE_K, "added": added})
        assessment = assess_retrieval(query, chunks)
    except Exception as e:
        actions.append({"action": "broaden", "error": type(e).__name__})
    if assessment.quality == STRONG:
        return chunks, assessment, actions

    # 2. expand: alternative phrasings of the same question (paraphrase / Hinglish -> English terms)
    alts = expand(query)[:MAX_EXPANSIONS]
    total_added = 0
    for alt in alts:
        try:
            chunks, added = _merge(chunks, search(alt, k), WIDE_K)
            total_added += added
        except Exception as e:
            actions.append({"action": "expand", "error": type(e).__name__})
    if alts:
        actions.append({"action": "expand", "queries": len(alts), "added": total_added})
        assessment = assess_retrieval(query, chunks, extra_queries=alts)
    return chunks, assessment, actions
