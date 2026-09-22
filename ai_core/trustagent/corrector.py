"""
TrustAgent Step 3 -- Correction (4-level verdict aware)
Rewrites the draft answer, attaching a citation, a verification badge,
and a jurisdiction-status badge where applicable.
"""
from ai_core.llm_gateway import call_llm

VERDICT_LABELS = {
    "supported": "✅ Verified Against Source",
    "partially_supported": "🟡 Partially Supported -- some details unconfirmed",
    "contradicted": "🔴 Contradicted -- claim conflicts with source",
    "unverified": "⚪ Unverified -- no matching evidence found",
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
least one point. Rewrite it to remove the contradicted claim entirely and
clearly state that this point could not be confirmed.

Original Answer: {draft_answer}"""
        corrected = call_llm("groq/openai/gpt-oss-20b", prompt)
        return f"{corrected}\n\n[Source: {case_name}]\n[Verification: {verdict_badge}]\n[Jurisdiction: {jurisdiction_badge}]"

    if overall_verdict == "partially_supported":
        prompt = f"""The following answer is only PARTIALLY supported by the
evidence -- some specific details (like exact numbers or conditions) could not
be confirmed. Rewrite it to soften those specific unconfirmed details while
keeping the confirmed parts intact.

Original Answer: {draft_answer}"""
        corrected = call_llm("groq/openai/gpt-oss-20b", prompt)
        return f"{corrected}\n\n[Source: {case_name}]\n[Verification: {verdict_badge}]\n[Jurisdiction: {jurisdiction_badge}]"

    # unverified
    return (
        f"I could not find sufficient evidence in the available sources to confidently "
        f"answer this specific point. Please consult a qualified lawyer for advice on "
        f"this matter.\n\n[Verification: {verdict_badge}]"
    )


def suggest_department_and_helpline(query: str, model_call_fn) -> str:
    """Suggests which authority/department to approach and relevant helpline."""
    prompt = f"""Based on this legal query, suggest in 1-2 short lines:
(a) which department/authority/court the person should approach, and
(b) a relevant official Indian helpline number if applicable (e.g. Police
100/112, Women Helpline 181, Cyber Crime 1930, Consumer Helpline 1915,
Legal Aid via NALSA 15100). If unsure of an exact number, say "contact
your local District Legal Services Authority (DLSA)" instead of guessing.

QUERY: {query}

Respond in this format:
Suggested Department: ...
Helpline: ..."""
    return model_call_fn("groq/openai/gpt-oss-20b", prompt)