"""
LLM-as-a-Judge — independent verifier judging claim-level factual grounding against retrieved evidence.
Never acts as the source of truth, but verifies generated claims against documentary evidence.
"""
import json
import re
from ai_core.llm_gateway import call_llm

JUDGE_MODEL = "gemini/gemini-3.6-flash"

# Canonical Phase 2.1 Verdict States
STATE_GROUNDED = "GROUNDED"
STATE_PARTIALLY_GROUNDED = "PARTIALLY_GROUNDED"
STATE_CONTRADICTED = "CONTRADICTED"
STATE_NO_EVIDENCE_FOUND = "NO_EVIDENCE_FOUND"
STATE_RETRIEVAL_INSUFFICIENT = "RETRIEVAL_INSUFFICIENT"
STATE_VERIFICATION_PENDING = "VERIFICATION_PENDING"

VALID_CLAIM_VERDICTS = {"SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED", "NOT_VERIFIABLE"}


def judge_claims_against_evidence(
    query: str,
    evidence: str,
    draft_answer: str,
    claims: list[str] | None = None,
) -> dict:
    """
    Evaluates each claim in the draft answer against the retrieved evidence.
    Returns claim-level verdicts and overall verdict without hiding individual claim failures.
    """
    if claims is None or len(claims) == 0:
        from ai_core.trustagent.claim_extractor import extract_claims
        extracted, ok = extract_claims(draft_answer)
        if not ok:
            return {
                "claim_verdicts": [],
                "overall_verdict": STATE_VERIFICATION_PENDING,
                "is_accurate": True,
                "issue": "Claim extraction failed (infrastructure issue).",
                "supported_claims": [],
                "unsupported_claims": [],
            }
        claims = extracted

    if not claims:
        # Genuinely no factual claims to evaluate (e.g. greeting or meta query)
        return {
            "claim_verdicts": [],
            "overall_verdict": STATE_GROUNDED,
            "is_accurate": True,
            "issue": "",
            "supported_claims": [],
            "unsupported_claims": [],
        }

    numbered_claims = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))
    # Provide generous evidence window up to 12000 chars to avoid false truncation
    evidence_trimmed = evidence[:12000]

    prompt = f"""You are an independent legal fact-verification judge.
Evaluate EACH claim in the DRAFT ANSWER against the provided EVIDENCE for the given QUESTION.

CRITICAL RULES:
1. For EACH claim, determine its verdict:
   - "SUPPORTED": Factually substantiated by the evidence passages.
   - "PARTIALLY_SUPPORTED": Core fact is supported but some details are unstated in the evidence.
   - "CONTRADICTED": Evidence directly contradicts or disproves the claim.
   - "NOT_VERIFIABLE": Evidence does not mention or support this claim.
2. Note evidence snippet indices / IDs and page numbers where found.
3. Provide a brief reason for each claim.
4. Respond with ONLY valid JSON (no markdown formatting, no code fences):

{{
  "claim_verdicts": [
    {{
      "claim": "...",
      "verdict": "SUPPORTED",
      "evidence_ids": ["1"],
      "page_numbers": [1],
      "reason": "..."
    }}
  ],
  "is_accurate": true,
  "issue": ""
}}

QUESTION:
{query}

CLAIMS:
{numbered_claims}

DRAFT ANSWER:
{draft_answer[:2000]}

EVIDENCE:
{evidence_trimmed}

JSON:"""

    try:
        raw = call_llm(JUDGE_MODEL, prompt)
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
        parsed = json.loads(cleaned)

        raw_verdicts = parsed.get("claim_verdicts", [])
        if not isinstance(raw_verdicts, list) or (not raw_verdicts and "is_accurate" in parsed):
            is_acc = bool(parsed.get("is_accurate", True))
            overall_state = STATE_GROUNDED if is_acc else STATE_NO_EVIDENCE_FOUND
            return {
                "claim_verdicts": [{"claim": c, "verdict": "SUPPORTED" if is_acc else "NOT_VERIFIABLE", "page_numbers": [], "evidence_ids": [], "reason": ""} for c in claims],
                "overall_verdict": overall_state,
                "is_accurate": is_acc,
                "issue": parsed.get("issue", ""),
                "supported_claims": claims if is_acc else [],
                "unsupported_claims": [] if is_acc else claims,
            }

        sanitized_verdicts = []
        supported_claims = []
        unsupported_claims = []

        for idx, c in enumerate(claims):
            matched = raw_verdicts[idx] if idx < len(raw_verdicts) and isinstance(raw_verdicts[idx], dict) else {}
            v = str(matched.get("verdict", "NOT_VERIFIABLE")).strip().upper()
            if v not in VALID_CLAIM_VERDICTS:
                v = "NOT_VERIFIABLE"

            ev_ids = matched.get("evidence_ids", [])
            page_nums = matched.get("page_numbers", [])
            reason = matched.get("reason", "")

            claim_obj = {
                "claim": c,
                "verdict": v,
                "evidence_ids": ev_ids if isinstance(ev_ids, list) else [],
                "page_numbers": page_nums if isinstance(page_nums, list) else [],
                "reason": reason,
            }
            sanitized_verdicts.append(claim_obj)

            if v in ("SUPPORTED", "PARTIALLY_SUPPORTED"):
                supported_claims.append(c)
            else:
                unsupported_claims.append(c)

        # Compute overall state
        verdict_values = [sv["verdict"] for sv in sanitized_verdicts]
        all_supported = all(v == "SUPPORTED" for v in verdict_values)
        all_contradicted = all(v == "CONTRADICTED" for v in verdict_values)
        all_unsupported = all(v in ("NOT_VERIFIABLE", "CONTRADICTED") for v in verdict_values)
        has_some_supported = any(v in ("SUPPORTED", "PARTIALLY_SUPPORTED") for v in verdict_values)

        if all_supported:
            overall = STATE_GROUNDED
        elif all_contradicted:
            overall = STATE_CONTRADICTED
        elif has_some_supported:
            overall = STATE_PARTIALLY_GROUNDED
        elif all_unsupported:
            overall = STATE_NO_EVIDENCE_FOUND
        else:
            overall = STATE_PARTIALLY_GROUNDED

        is_accurate = bool(parsed.get("is_accurate", True)) and (overall in (STATE_GROUNDED, STATE_PARTIALLY_GROUNDED))

        return {
            "claim_verdicts": sanitized_verdicts,
            "overall_verdict": overall,
            "is_accurate": is_accurate,
            "issue": parsed.get("issue", ""),
            "supported_claims": supported_claims,
            "unsupported_claims": unsupported_claims,
        }
    except Exception as e:
        # On JSON or API failure, must be VERIFICATION_PENDING, never NO_EVIDENCE_FOUND
        return {
            "claim_verdicts": [],
            "overall_verdict": STATE_VERIFICATION_PENDING,
            "is_accurate": True,
            "issue": f"Verification infrastructure encountered an error: {str(e)}",
            "supported_claims": [],
            "unsupported_claims": [],
        }


def judge_answer(query: str, answer: str, evidence: str) -> dict:
    """
    Backward-compatible evaluator returning overall accuracy and structured judgment.
    """
    judgment = judge_claims_against_evidence(query=query, evidence=evidence, draft_answer=answer)
    return {
        "is_accurate": judgment.get("is_accurate", True),
        "is_helpful": True,
        "issue": judgment.get("issue", ""),
        "overall_verdict": judgment.get("overall_verdict", STATE_GROUNDED),
        "claim_verdicts": judgment.get("claim_verdicts", []),
    }
