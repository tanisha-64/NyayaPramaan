"""
TrustAgent pipeline: verify -> correct -> RE-VERIFY -> check citations -> measurable summary.

Principles
* An answer is only reported as grounded/partially grounded if a verifier actually judged its claims.
  Verifier failure or zero extractable claims means VERIFICATION_PENDING, never GROUNDED.
* A corrected answer is verified again before it is shown. If it cannot be re-verified it is replaced by a
  deterministic list of the claims that were individually judged supported.
* No invented percentages. The only numeric figure is claim_support_ratio, a documented ratio over judged claims.

All LLM-touching steps are injected (extract / judge / correct) so the logic is unit-testable offline.
"""
from dataclasses import dataclass, field
from typing import Callable

from ai_core.evaluation.llm_judge import (
    STATE_GROUNDED, STATE_PARTIALLY_GROUNDED, STATE_CONTRADICTED, STATE_NO_EVIDENCE_FOUND,
    STATE_VERIFICATION_PENDING,
)
from ai_core.guardrails.output_guard import redact_pii
from ai_core.rag.provenance import paragraph_numbers, snippet
from ai_core.trustagent.citations import (
    check_citations, strip_invalid_bracket_citations, ungrounded_specifics,
)
from ai_core.trustagent.claim_extractor import MAX_CLAIMS

PENDING_NOTICE = "⚠️ This answer could not be automatically verified against the sources. Treat it as unverified."
WITHHELD_NOTICE = ("The draft answer conflicted with the source evidence, so it was withheld. "
                   "Please check the cited passages directly or rephrase your question.")
REFUSAL_PREFIX = "no supporting evidence was found"

SUMMARY_METHOD = ("An LLM judge compared each claim in the answer with the retrieved passages. "
                  "claim_support_ratio = (supported + 0.5 x partially supported) / judged claims. "
                  "It measures claim support, not the probability that the answer is correct.")


@dataclass
class TrustResult:
    answer: str
    verdict_state: str
    claim_verdicts: list = field(default_factory=list)
    supported_claims: list = field(default_factory=list)
    unsupported_claims: list = field(default_factory=list)
    removed_claims: list = field(default_factory=list)
    corrected: bool = False
    reverified: bool | None = None          # None = no correction was needed
    correction_method: str | None = None
    is_accurate: bool = True
    issue: str = ""
    citations: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    answer_quality: dict | None = None       # judge rubric (relevance / completeness / should_abstain), if returned
    judge_status: str = "ok"                 # "unavailable" when the judge or claim extraction could not run

    @property
    def verified(self) -> bool:
        return self.verdict_state in (STATE_GROUNDED, STATE_PARTIALLY_GROUNDED) and self.is_accurate


def is_refusal(text: str) -> bool:
    return (text or "").strip().lower().startswith(REFUSAL_PREFIX)


def _sanitize_pages(verdicts: list[dict], retrieved_pages: set[int]) -> list[dict]:
    """Judge-reported page numbers are LLM output: keep only pages that were really retrieved."""
    out = []
    for v in verdicts:
        v = dict(v)
        pages = []
        for p in v.get("page_numbers") or []:
            try:
                pages.append(int(p))
            except (TypeError, ValueError):
                continue
        v["page_numbers"] = sorted({p for p in pages if p in retrieved_pages})
        out.append(v)
    return out


def _judge(extract, judge, query: str, answer: str, evidence: str, retrieved_pages: set[int]) -> dict:
    claims, ok = extract(answer)
    if not ok:
        return {"overall_verdict": STATE_VERIFICATION_PENDING, "claim_verdicts": [], "supported_claims": [],
                "unsupported_claims": [], "is_accurate": True, "issue": "Claim extraction failed.", "claims": []}
    # Claims are model output that is forwarded to the judge (a different provider): same identifier boundary.
    claims = [redact_pii(c.strip()) for c in claims if isinstance(c, str) and c.strip()]
    if not claims:
        # A substantive answer with nothing extractable has NOT been verified.
        return {"overall_verdict": STATE_VERIFICATION_PENDING, "claim_verdicts": [], "supported_claims": [],
                "unsupported_claims": [], "is_accurate": True, "issue": "No verifiable claims were extracted.", "claims": []}
    j = judge(query=query, evidence=evidence, draft_answer=answer, claims=claims)
    j = dict(j)
    j["claim_verdicts"] = _sanitize_pages(j.get("claim_verdicts") or [], retrieved_pages)
    j["claims"] = claims
    return j


def _summary(verdicts: list[dict], citations: dict, top_similarity, pages_estimated: bool, specifics: list[str],
             claims_capped: bool = False) -> dict:
    counts = {"SUPPORTED": 0, "PARTIALLY_SUPPORTED": 0, "CONTRADICTED": 0, "NOT_VERIFIABLE": 0}
    for v in verdicts:
        counts[v.get("verdict", "NOT_VERIFIABLE")] = counts.get(v.get("verdict", "NOT_VERIFIABLE"), 0) + 1
    total = len(verdicts)
    ratio = round((counts["SUPPORTED"] + 0.5 * counts["PARTIALLY_SUPPORTED"]) / total, 3) if total else None
    return {
        "claims_total": total,
        "supported": counts["SUPPORTED"],
        "partially_supported": counts["PARTIALLY_SUPPORTED"],
        "contradicted": counts["CONTRADICTED"],
        "not_verifiable": counts["NOT_VERIFIABLE"],
        "claim_support_ratio": ratio,
        "citations_cited": citations.get("cited", []),
        "citations_valid": citations.get("valid", []),
        "citations_invalid": citations.get("invalid", []),
        "retrieval_top_similarity": top_similarity,
        "pages_estimated": pages_estimated,
        "ungrounded_specifics": specifics,
        # True when extraction returned its maximum number of claims: later statements in a long answer may not have
        # been checked, so the user-facing status must not be read as covering every sentence.
        "claims_capped": claims_capped,
        "method": SUMMARY_METHOD,
    }


def _supported_claims_answer(supported: list[str]) -> str:
    return "Based on the document evidence, the following points are supported:\n" + "\n".join(f"- {c}" for c in supported)


def verify_and_correct(
    *,
    query: str,
    draft: str,
    evidence: str,
    retrieved_pages: set[int],
    extract: Callable[[str], tuple[list, bool]],
    judge: Callable[..., dict],
    correct: Callable[..., str],
    top_similarity=None,
    pages_estimated: bool = False,
) -> TrustResult:
    if is_refusal(draft):
        return TrustResult(answer=draft, verdict_state=STATE_NO_EVIDENCE_FOUND, is_accurate=False,
                           summary=_summary([], {}, top_similarity, pages_estimated, []))

    first = _judge(extract, judge, query, draft, evidence, retrieved_pages)
    state = first.get("overall_verdict", STATE_VERIFICATION_PENDING)
    answer = draft
    verdicts = first["claim_verdicts"]
    supported = list(first.get("supported_claims") or [])
    unsupported = list(first.get("unsupported_claims") or [])
    result = TrustResult(answer=answer, verdict_state=state, claim_verdicts=verdicts, supported_claims=supported,
                         unsupported_claims=unsupported, is_accurate=first.get("is_accurate", True),
                         issue=first.get("issue", ""), answer_quality=first.get("answer_quality"),
                         judge_status="unavailable" if state == STATE_VERIFICATION_PENDING else "ok")

    if state == STATE_PARTIALLY_GROUNDED:
        if not supported:
            result.verdict_state = STATE_NO_EVIDENCE_FOUND
        elif unsupported:
            result.removed_claims = unsupported
            result.corrected = True
            corrected = ""
            try:
                corrected = (correct(draft, supported, unsupported, evidence, query) or "").strip()
            except Exception:
                corrected = ""
            second = _judge(extract, judge, query, corrected, evidence, retrieved_pages) if corrected else None
            if second and second.get("overall_verdict") == STATE_GROUNDED:
                result.answer, result.reverified, result.correction_method = corrected, True, "llm_rewrite"
                result.claim_verdicts = second["claim_verdicts"]
                result.answer_quality = second.get("answer_quality") or result.answer_quality
                result.supported_claims, result.unsupported_claims = second.get("supported_claims", []), []
            else:
                # Rewrite could not be confirmed (still unsupported content, or the verifier failed): show only
                # the claims that were individually judged supported, verbatim.
                result.answer, result.reverified, result.correction_method = (
                    _supported_claims_answer(supported), True, "supported_claims_only")
                result.claim_verdicts = [v for v in verdicts if v.get("verdict") in ("SUPPORTED", "PARTIALLY_SUPPORTED")]
                result.unsupported_claims = []
    elif state == STATE_CONTRADICTED:
        result.answer = WITHHELD_NOTICE
        result.removed_claims = unsupported
    elif state == STATE_VERIFICATION_PENDING:
        result.answer = f"{draft}\n\n{PENDING_NOTICE}"
        result.is_accurate = True

    if result.verdict_state in (STATE_GROUNDED, STATE_PARTIALLY_GROUNDED):
        cites = check_citations(result.answer, retrieved_pages)
        if cites["invalid"]:
            result.answer = strip_invalid_bracket_citations(result.answer, cites["invalid"])
            cites = {**cites, "invalid": check_citations(result.answer, retrieved_pages)["invalid"],
                     "removed": cites["invalid"]}
        # A cited page that WAS retrieved can still be the wrong page for the claim it is attached to. When the judge
        # attributed claims to pages, flag cited pages that no supported claim is attributed to. Flag only: judge page
        # attributions are model output and can be incomplete, so this never deletes text.
        backing = {p for v in result.claim_verdicts if v.get("verdict") in ("SUPPORTED", "PARTIALLY_SUPPORTED")
                   for p in (v.get("page_numbers") or [])}
        cites["not_backed"] = sorted(set(cites.get("valid", [])) - backing) if backing else []
        result.citations = cites
    else:
        result.citations = check_citations("", retrieved_pages)

    specifics = ungrounded_specifics(result.answer, evidence) if result.verdict_state in (STATE_GROUNDED, STATE_PARTIALLY_GROUNDED) else []
    result.summary = _summary(result.claim_verdicts, result.citations, top_similarity, pages_estimated, specifics,
                              claims_capped=len(first.get("claims") or []) >= MAX_CLAIMS)
    return result


def build_document_sources(filename: str, chunks: list[dict], result: TrustResult, status_label: str,
                           pages_estimated: bool = False) -> list[dict]:
    """One source per distinct page. A page is 'verified' if it backs a SUPPORTED claim, 'partial' if it only backs
    PARTIALLY_SUPPORTED claims; pages that back nothing keep the overall status label so the UI does not overstate.
    Each source also carries its provenance: document, page, explicit paragraph numbers found in the passage text (may
    be empty) and a short verbatim excerpt. All of it comes from the retrieved chunks, none from a model."""
    backing: dict[int, str] = {}
    for v in result.claim_verdicts:
        verdict = v.get("verdict")
        for p in v.get("page_numbers") or []:
            if verdict == "SUPPORTED":
                backing[p] = "verified"
            elif verdict == "PARTIALLY_SUPPORTED" and backing.get(p) != "verified":
                backing[p] = "partial"
    cited_valid = set(result.citations.get("valid", []))
    seen: set = set()
    sources = []
    for c in chunks:
        page = c.get("page_number")
        key = page if page else ("nopage", len(seen))
        if key in seen:
            continue
        seen.add(key)
        name = f"{filename} — Page {page}" if page else filename
        status = backing.get(page) or ("partial" if page in cited_valid else status_label)
        on_page = [x.get("chunk_text", "") for x in chunks if x.get("page_number") == page] if page else [c.get("chunk_text", "")]
        paras = sorted({n for t in on_page for n in paragraph_numbers(t)})
        sources.append({"name": name, "type": "document", "url": None, "verification_status": status,
                        "jurisdiction": None, "page_number": page,
                        "document": filename, "page_estimated": bool(pages_estimated) if page else None,
                        "paragraphs": paras, "snippet": snippet(c.get("chunk_text", "")),
                        "supports_claim": page in backing})
    # Pages that actually back claims first.
    sources.sort(key=lambda s: (not s["supports_claim"], s["page_number"] or 10**9))
    return sources
