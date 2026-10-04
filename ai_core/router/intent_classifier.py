
"""Intent Classifier — strict legal-domain guardrail + audience detection."""

import json

import re

from ai_core.llm_gateway import call_llm



CLASSIFIER_MODEL = "groq/openai/gpt-oss-20b"



REFUSAL_MESSAGE = (

    "I'm a legal-domain assistant and only answer questions related to "

    "Indian law, legal rights, court procedure, or specific "

    "cases/documents. Please ask me something related to law."

)



AUDIENCE_INSTRUCTIONS = {

    "professional": (

        "Write for a legal professional: use precise legal terminology, "

        "cite exact section numbers, and include procedural nuance."

    ),

    "student_public": (

        "Write for a student or citizen: use simple, plain language, "

        "briefly define any legal term you must use, and keep a friendly tone."

    ),

}





def classify_intent(query: str) -> dict:

    prompt = f"""Classify this question on two dimensions. Respond with ONLY this JSON:

{{"domain": "legal", "audience": "professional"}}



domain: "legal" if about law, legal rights, court procedure, IPC/BNS/

statutes, a legal case/document, or the justice system. "out_of_domain" if

unrelated to law entirely.



audience: "professional" if legal-professional terminology/strategy is used.

"student_public" if it sounds like a citizen/student wanting simple explanation.



QUESTION: {query}



JSON:"""

    try:

        raw = call_llm(CLASSIFIER_MODEL, prompt)

        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())

        result = json.loads(cleaned)

        domain = result.get("domain", "legal")

        audience = result.get("audience", "student_public")

        if domain not in ("legal", "out_of_domain"):

            domain = "legal"

        if audience not in ("professional", "student_public"):

            audience = "student_public"

        return {"domain": domain, "audience": audience}

    except Exception:

        return {"domain": "legal", "audience": "student_public"}

