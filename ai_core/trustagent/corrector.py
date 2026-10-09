"""
TrustAgent Step 3 — final-answer correction, claim filtering + department/helpline suggestion.
"""
from ai_core.llm_gateway import call_llm
import re

VERDICT_LABELS = {
    "supported": "✅ Verified Against Source",
    "partially_supported": "🟡 Partially Supported -- some details unconfirmed",
    "contradicted": "🔴 Contradicted -- claim conflicts with source",
    "unverified": "⚪ Unverified -- no matching evidence found",
    "verification_pending": "⏳ Verification Pending",
}


def correct_answer(draft_answer: str, case_name: str, overall_verdict: str, jurisdiction_type: str = "unknown") -> str:
    verdict_badge = VERDICT_LABELS.get(overall_verdict, VERDICT_LABELS["unverified"])
    jurisdiction_badge = (
        "✅ Binding in this jurisdiction" if jurisdiction_type == "binding"
        else "⚠️ Persuasive only -- not binding in this jurisdiction" if jurisdiction_type == "persuasive"
        else "ℹ️ Jurisdiction status not available"
    )

    if overall_verdict == "supported":
        return f"{draft_answer}\n\n[Source: {case_name}]\n[Verification: {verdict_badge}]\n[Jurisdiction: {jurisdiction_badge}]"

    if overall_verdict == "contradicted":
        prompt = f"""The following answer CONTRADICTS the source evidence on at
least one point. Rewrite it to remove the contradicted claim and clearly
state this point could not be confirmed.

Original Answer: {draft_answer}"""
        corrected = call_llm("groq/openai/gpt-oss-20b", prompt)
        return f"{corrected}\n\n[Source: {case_name}]\n[Verification: {verdict_badge}]\n[Jurisdiction: {jurisdiction_badge}]"

    if overall_verdict == "partially_supported":
        prompt = f"""The following answer is only PARTIALLY supported by the
evidence. Rewrite it to soften or remove unconfirmed specific details while keeping
confirmed parts intact.

Original Answer: {draft_answer}"""
        corrected = call_llm("groq/openai/gpt-oss-20b", prompt)
        return f"{corrected}\n\n[Source: {case_name}]\n[Verification: {verdict_badge}]\n[Jurisdiction: {jurisdiction_badge}]"

    return (
        f"I could not find sufficient evidence in the available sources to confidently "
        f"answer this specific point. Please consult a qualified lawyer.\n\n[Verification: {verdict_badge}]"
    )


def filter_supported_claims_answer(
    draft_answer: str,
    supported_claims: list[str],
    unsupported_claims: list[str],
    evidence: str,
    query: str = "",
) -> str:
    """
    Constructs a grounded answer retaining ONLY supported claims and removing hallucinated/unverified elements.
    """
    if not supported_claims:
        return f"No supporting evidence was found in the uploaded document regarding {query}."

    prompt = f"""Rewrite the DRAFT ANSWER to include ONLY the factually SUPPORTED claims below.
STRICT RULES:
1. Include all verified facts from SUPPORTED CLAIMS.
2. Completely EXCLUDE and REMOVE all UNSUPPORTED CLAIMS.
3. Do NOT add any new unverified claims or standard legal documents that are not in the evidence.
4. Keep the response factual, concise, and matching the original language style.

QUESTION:
{query}

SUPPORTED CLAIMS (MUST KEEP):
{chr(10).join(f"- {c}" for c in supported_claims)}

UNSUPPORTED CLAIMS (MUST REMOVE):
{chr(10).join(f"- {c}" for c in unsupported_claims) if unsupported_claims else "(None)"}

DRAFT ANSWER:
{draft_answer}

EVIDENCE:
{evidence[:6000]}

REWRITTEN ANSWER:"""
    try:
        rewritten = call_llm("groq/openai/gpt-oss-20b", prompt)
        return rewritten.strip()
    except Exception:
        # Fallback: simple formatted list of supported claims
        bullet_points = "\n".join(f"- {c}" for c in supported_claims)
        return f"Based on the document evidence, the following supported points were found:\n{bullet_points}"


def suggest_department_and_helpline(query: str, model_call_fn) -> str:
    prompt = f"""Based on this legal query, suggest in 1-2 short lines:
(a) which department/authority/court the person should approach, and
(b) a relevant official Indian helpline number if applicable (Police
100/112, Women Helpline 181, Cyber Crime 1930, Consumer Helpline 1915,
Legal Aid via NALSA 15100). If unsure of an exact number, say "contact
your local District Legal Services Authority (DLSA)".

QUERY: {query}

Respond in this format:
Suggested Department: ...
Helpline: ..."""
    return model_call_fn("groq/openai/gpt-oss-20b", prompt)
