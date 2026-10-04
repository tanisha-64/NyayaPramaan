"""
TrustAgent Step 2 -- Verification (4-level verdict, BATCHED)
Verifies ALL claims in a SINGLE LLM call with exact evidence citations.
"""
from ai_core.llm_gateway import call_llm
import json
import re

VALID_VERDICTS = ["SUPPORTED", "PARTIALLY SUPPORTED", "CONTRADICTED", "INSUFFICIENT EVIDENCE"]


def verify_claims_batch(claims: list[str], evidence: str) -> list[dict]:
    """Verifies a list of claims against evidence in ONE LLM call."""
    if not claims:
        return []

    numbered_claims = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))
    prompt = f"""Verify EACH numbered claim below against the provided legal evidence.
For each claim, choose exactly one status: "SUPPORTED", "PARTIALLY SUPPORTED", "CONTRADICTED", or "INSUFFICIENT EVIDENCE".
Extract the exact supporting excerpt or mention (e.g. "Section 302 IPC", "Judgment Page 4", "FIR Paragraph 3").

Respond with ONLY a JSON array of objects in the SAME ORDER:
[
  {{
    "claim": "...",
    "status": "SUPPORTED",
    "evidence": "Exact excerpt or section/page reference from evidence",
    "source": "Document or Statute name"
  }}
]

CLAIMS:
{numbered_claims}

LEGAL EVIDENCE:
{evidence}"""

    raw = call_llm("groq/openai/gpt-oss-20b", prompt)
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())

    try:
        results = json.loads(cleaned)
        sanitized = []
        for i, r in enumerate(results):
            raw_status = (r.get("status") or r.get("verdict") or "INSUFFICIENT EVIDENCE").upper().replace("_", " ")
            if "PARTIAL" in raw_status:
                status = "PARTIALLY SUPPORTED"
            elif "SUPPORT" in raw_status:
                status = "SUPPORTED"
            elif "CONTRADICT" in raw_status:
                status = "CONTRADICTED"
            else:
                status = "INSUFFICIENT EVIDENCE"
            
            sanitized.append({
                "claim": r.get("claim") or (claims[i] if i < len(claims) else ""),
                "status": status,
                "evidence": r.get("evidence") or (r.get("reason") if status == "SUPPORTED" else "No direct evidence passage found"),
                "source": r.get("source") or "Legal Knowledge Base / Case Record",
            })
        while len(sanitized) < len(claims):
            idx = len(sanitized)
            sanitized.append({
                "claim": claims[idx],
                "status": "INSUFFICIENT EVIDENCE",
                "evidence": "Could not locate explicit supporting evidence.",
                "source": "Legal Knowledge Base",
            })
        return sanitized[: len(claims)]
    except Exception:
        return [
            {
                "claim": c,
                "status": "INSUFFICIENT EVIDENCE",
                "evidence": "Verification could not parse detailed claim citations.",
                "source": "Legal Knowledge Base",
            }
            for c in claims
        ]


def summarize_verdicts(verdicts: list[dict]) -> str:
    statuses = [v.get("status", "").upper() for v in verdicts]
    if "CONTRADICTED" in statuses:
        return "contradicted"
    if "INSUFFICIENT EVIDENCE" in statuses or "UNVERIFIED" in statuses:
        if any(s == "SUPPORTED" for s in statuses):
            return "partially_supported"
        return "unverified"
    if "PARTIALLY SUPPORTED" in statuses:
        return "partially_supported"
    return "supported"