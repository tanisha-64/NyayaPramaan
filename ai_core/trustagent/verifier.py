
"""TrustAgent Step 2 — batched 4-level claim verification."""

from ai_core.llm_gateway import call_llm

import json

import re



VALID_VERDICTS = ["supported", "partially_supported", "contradicted", "unverified"]





def verify_claims_batch(claims: list[str], evidence: str) -> list[dict]:

    if not claims:

        return []

    numbered_claims = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))

    prompt = f"""Verify EACH numbered claim below against the evidence.

For each, choose exactly one verdict: "supported", "partially_supported",

"contradicted" (evidence explicitly conflicts), or "unverified" (evidence

doesn't address this topic at all -- not the same as contradiction).



Respond with ONLY a JSON array, one object per claim, SAME ORDER:

[{{"verdict": "supported", "confidence": 0, "reason": ""}}, ...]



CLAIMS:

{numbered_claims}



EVIDENCE: {evidence}"""

    raw = call_llm("groq/openai/gpt-oss-20b", prompt)

    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())

    try:

        results = json.loads(cleaned)

        sanitized = []

        for r in results:

            v = r.get("verdict")

            if v not in VALID_VERDICTS:

                v = "unverified"

            sanitized.append({"verdict": v, "confidence": r.get("confidence", 0), "reason": r.get("reason", "")})

        while len(sanitized) < len(claims):

            sanitized.append({"verdict": "unverified", "confidence": 0, "reason": "parse-mismatch"})

        return sanitized[: len(claims)]

    except Exception:

        return [{"verdict": "unverified", "confidence": 0, "reason": "Could not parse"} for _ in claims]





def summarize_verdicts(verdicts: list[dict]) -> str:

    verdict_list = [v.get("verdict") for v in verdicts]

    if "contradicted" in verdict_list:

        return "contradicted"

    if "unverified" in verdict_list:

        return "unverified"

    if "partially_supported" in verdict_list:

        return "partially_supported"

    return "supported"

