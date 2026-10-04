
"""TrustAgent Step 3 — final-answer correction + department/helpline suggestion."""

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

least one point. Rewrite it to remove the contradicted claim and clearly

state this point could not be confirmed.



Original Answer: {draft_answer}"""

        corrected = call_llm("groq/openai/gpt-oss-20b", prompt)

        return f"{corrected}\n\n[Source: {case_name}]\n[Verification: {verdict_badge}]\n[Jurisdiction: {jurisdiction_badge}]"



    if overall_verdict == "partially_supported":

        prompt = f"""The following answer is only PARTIALLY supported by the

evidence. Rewrite it to soften unconfirmed specific details while keeping

confirmed parts intact.



Original Answer: {draft_answer}"""

        corrected = call_llm("groq/openai/gpt-oss-20b", prompt)

        return f"{corrected}\n\n[Source: {case_name}]\n[Verification: {verdict_badge}]\n[Jurisdiction: {jurisdiction_badge}]"



    return (

        f"I could not find sufficient evidence in the available sources to confidently "

        f"answer this specific point. Please consult a qualified lawyer.\n\n[Verification: {verdict_badge}]"

    )





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

