
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





def _heuristic_precheck(lowered: str) -> dict | None:

    # 1. Non-legal / Out-of-domain signals

    out_of_domain_words = [

        "recipe", "cake", "bake", "poem", "poetry", "joke", "song", "lyrics",

        "weather", "cricket", "ipl", "football", "movie", "actor", "actress",

        "horoscope", "astrology", "bluetooth", "wifi", "gameplay", "gaming",

        "reverse string", "javascript tutorial", "python script"

    ]

    has_legal_terms = any(w in lowered for w in ["court", "case", "law", "dhara", "section", "fir", "bail", "bns", "ipc", "crpc", "act", "rights", "petition", "judge", "advocate"])



    if any(w in lowered for w in out_of_domain_words) and not has_legal_terms:
        return {
            "domain": "out_of_domain",
            "query_mode": "OUT_OF_DOMAIN",
            "requires_case_context": False,
            "requires_statutory_law": False,
            "jurisdiction": "India",
            "audience": "student_public",
        }




    has_case_mention = any(k in lowered for k in [

        "uploaded pdf", "uploaded document", "uploaded case", "attached document",

        "this document", "is document", "is case", "plaintiff's title", "plaintiff ka title",

        "mere case", "mere uploaded", "is file me", "in this case", "petitioner's argument"

    ])



    has_law_mention = any(k in lowered for k in [

        "dhara", "section", "ipc", "bns", "crpc", "bnss", "bsa", "act", "law",

        "adverse possession", "bail", "fir", "punishment", "penalty", "offence", "right"

    ])



    if has_case_mention and has_law_mention:

        return {

            "domain": "legal",

            "query_mode": "MIXED",

            "requires_case_context": True,

            "requires_statutory_law": True,

            "jurisdiction": "India",

            "audience": "student_public",

        }



    if has_case_mention and not has_law_mention:

        return {

            "domain": "legal",

            "query_mode": "CASE_SPECIFIC",

            "requires_case_context": True,

            "requires_statutory_law": False,

            "jurisdiction": "India",

            "audience": "student_public",

        }



    if has_law_mention and not has_case_mention:

        # Check audience signal

        is_pro = any(p in lowered for p in ["jurisdiction", "sub-section", "appellant", "respondent", "ratio decidendi", "obiter"])

        return {

            "domain": "legal",

            "query_mode": "GENERAL_LAW",

            "requires_case_context": False,

            "requires_statutory_law": True,

            "jurisdiction": "India",

            "audience": "professional" if is_pro else "student_public",

        }



    return None





def classify_intent(query: str) -> dict:

    lowered = query.lower().strip()

    pre = _heuristic_precheck(lowered)

    if pre is not None:

        return pre



    prompt = f"""You are a query classifier for an Indian legal domain AI assistant.

Classify this user question across domain, query_mode, and audience.



Modes:

- "CASE_SPECIFIC": refers specifically to an uploaded case/document, evidence, parties or facts in a document.

- "GENERAL_LAW": asks general Indian legal questions (IPC, BNS, CrPC, BNSS, statutes, legal sections, definitions, rights, court procedures).

- "MIXED": asks how general Indian law or sections apply to facts/disputes in an uploaded case.

- "OUT_OF_DOMAIN": unrelated to law entirely (e.g., poems, cooking recipes, weather, generic entertainment).



Audiences:

- "professional": legal terminology or professional strategy.

- "student_public": simple plain language / student / citizen.



Respond with ONLY this JSON format:

{{"domain": "legal", "query_mode": "GENERAL_LAW", "requires_case_context": false, "requires_statutory_law": true, "jurisdiction": "India", "audience": "student_public"}}



QUESTION: {query}



JSON:"""



    try:

        raw = call_llm(CLASSIFIER_MODEL, prompt)

        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())

        result = json.loads(cleaned)



        domain = result.get("domain", "legal")

        query_mode = result.get("query_mode", "GENERAL_LAW")

        audience = result.get("audience", "student_public")



        if domain not in ("legal", "out_of_domain"):

            domain = pre["domain"] if pre else "legal"



        if domain == "out_of_domain":

            return {

                "domain": "out_of_domain",

                "query_mode": "OUT_OF_DOMAIN",

                "requires_case_context": False,

                "requires_statutory_law": False,

                "jurisdiction": "India",

                "audience": audience if audience in ("professional", "student_public") else "student_public",

            }



        if query_mode not in ("CASE_SPECIFIC", "GENERAL_LAW", "MIXED"):

            query_mode = pre["query_mode"] if pre else "GENERAL_LAW"



        req_case = True if query_mode in ("CASE_SPECIFIC", "MIXED") else False

        req_law = True if query_mode in ("GENERAL_LAW", "MIXED") else False



        return {

            "domain": "legal",

            "query_mode": query_mode,

            "requires_case_context": req_case,

            "requires_statutory_law": req_law,

            "jurisdiction": "India",

            "audience": audience if audience in ("professional", "student_public") else "student_public",

        }

    except Exception:

        if pre:

            return pre

        return {

            "domain": "legal",

            "query_mode": "GENERAL_LAW",

            "requires_case_context": False,

            "requires_statutory_law": True,

            "jurisdiction": "India",

            "audience": "student_public",

        }

