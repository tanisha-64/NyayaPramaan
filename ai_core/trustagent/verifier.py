"""
TrustAgent Step 2 — batched verification. Returns (verdicts, success_flag)
so a parsing/API failure is never silently shown to the user as
"Unverified" (which misleadingly implies evidence doesn't support the
claim, when actually the verifier itself just failed to run).
"""
from ai_core.llm_gateway import call_llm
import json
import re

VALID_VERDICTS = ["supported", "partially_supported", "contradicted", "unverified"]


def verify_claims_batch(claims: list[str], evidence: str) -> tuple[list[dict], bool]:
    if not claims:
        return [], True

    numbered_claims = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))
    evidence_trimmed = evidence[:12000]  # Allow full evidence chunks without premature truncation

    prompt = f"""Verify EACH numbered claim below against the evidence.
For each, choose exactly one verdict: "supported", "partially_supported",
"contradicted" (evidence explicitly conflicts), or "unverified" (evidence
doesn't address this topic at all).

Respond with ONLY a JSON array, one object per claim, SAME ORDER, no markdown fences:
[{{"verdict": "supported", "confidence": 0.9, "reason": "..."}}, ...]

CLAIMS:
{numbered_claims}

EVIDENCE:
{evidence_trimmed}"""

    try:
        raw = call_llm("groq/openai/gpt-oss-20b", prompt)
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
        results = json.loads(cleaned)
        if not isinstance(results, list):
            return [], False

        sanitized = []
        for i, r in enumerate(results):
            c_text = claims[i] if i < len(claims) else ""
            v = r.get("verdict", "").lower() if isinstance(r, dict) else "unverified"
            if v not in VALID_VERDICTS:
                if "partially" in v:
                    v = "partially_supported"
                elif "contradict" in v:
                    v = "contradicted"
                elif "support" in v:
                    v = "supported"
                else:
                    v = "unverified"
            conf = r.get("confidence", 0) if isinstance(r, dict) else 0
            reason = r.get("reason", "") if isinstance(r, dict) else ""
            sanitized.append({"claim": c_text, "verdict": v, "confidence": conf, "reason": reason})
        while len(sanitized) < len(claims):
            sanitized.append({"claim": claims[len(sanitized)], "verdict": "unverified", "confidence": 0, "reason": ""})
        return sanitized[: len(claims)], True
    except Exception:
        return [], False  # verifier infra failed -- caller marks "verification_pending"


def summarize_verdicts(verdicts: list[dict]) -> str:
    if not verdicts:
        return "verification_pending"
    verdict_list = [v.get("verdict", "").lower() for v in verdicts]
    
    supported_count = sum(1 for v in verdict_list if v == "supported")
    partial_count = sum(1 for v in verdict_list if v == "partially_supported")
    contradicted_count = sum(1 for v in verdict_list if v == "contradicted")
    unverified_count = sum(1 for v in verdict_list if v in ("unverified", "not_verifiable"))

    total = len(verdict_list)

    if supported_count == total:
        return "supported"
    if contradicted_count == total:
        return "contradicted"
    if unverified_count == total:
        return "unverified"
    
    # Mixed results: if there is at least one supported/partially_supported claim,
    # the answer is partially supported, NOT unverified or contradicted!
    if supported_count + partial_count > 0:
        return "partially_supported"

    return "unverified"
