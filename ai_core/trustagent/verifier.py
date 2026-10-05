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
    evidence_trimmed = evidence[:4000]  # keep prompt size manageable for reliable JSON output

    prompt = f"""Verify EACH numbered claim below against the evidence.
For each, choose exactly one verdict: "supported", "partially_supported",
"contradicted" (evidence explicitly conflicts), or "unverified" (evidence
doesn't address this topic at all).

Respond with ONLY a JSON array, one object per claim, SAME ORDER, no markdown fences:
[{{"verdict": "supported", "confidence": 0}}, ...]

CLAIMS:
{numbered_claims}

EVIDENCE: {evidence_trimmed}"""

    try:
        raw = call_llm("groq/openai/gpt-oss-20b", prompt)
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
        results = json.loads(cleaned)
        if not isinstance(results, list):
            return [], False

        sanitized = []
        for r in results:
            v = r.get("verdict") if isinstance(r, dict) else None
            if v not in VALID_VERDICTS:
                v = "unverified"
            sanitized.append({"verdict": v, "confidence": r.get("confidence", 0) if isinstance(r, dict) else 0})
        while len(sanitized) < len(claims):
            sanitized.append({"verdict": "unverified", "confidence": 0})
        return sanitized[: len(claims)], True
    except Exception:
        return [], False  # verifier infra failed -- caller marks "verification_pending"


def summarize_verdicts(verdicts: list[dict]) -> str:
    if not verdicts:
        return "verification_pending"
    verdict_list = [v.get("verdict") for v in verdicts]
    if "contradicted" in verdict_list:
        return "contradicted"
    if "unverified" in verdict_list:
        return "unverified"
    if "partially_supported" in verdict_list:
        return "partially_supported"
    return "supported"
