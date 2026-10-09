"""
Intent Classifier — 4-way routing, THE CORE FIX for general-law questions
being wrongly routed into document-context. Even when a document is
attached, this decides whether the query is actually ABOUT the document,
a GENERAL legal question, a MIX of both, or entirely out of scope.
"""
import json
import re
from ai_core.llm_gateway import call_llm

CLASSIFIER_MODEL = "groq/openai/gpt-oss-20b"

REFUSAL_MESSAGE = (
    "I can assist only with legal research, legal documents, and "
    "legal-domain questions."
)

AUDIENCE_INSTRUCTIONS = {
    "professional": "Write for a legal professional: precise terminology, exact section numbers, procedural nuance.",
    "student_public": "Write for a student/citizen: simple plain language, briefly define legal terms.",
}

# Fast keyword pre-filter -- obvious general-law signals even when a doc is attached
GENERAL_LAW_SIGNALS = [
    "section", "bns ", "ipc ", "crpc", "bnss", "what is the punishment",
    "which law", "which section", "legal definition of", "what does the law say",
    "statute", "bare act", "constitution article", "fundamental right", "dhara",
    "adverse possession", "bail", "fir", "punishment", "penalty", "offence",
]
DOCUMENT_REFERENCE_SIGNALS = [
    "this case", "this document", "the uploaded", "in this file", "plaintiff",
    "defendant", "petitioner", "respondent", "the commissioner", "this pdf",
    "this judgment", "summarize this", "summary of this", "is this a case",
    "uploaded pdf", "uploaded document", "uploaded case", "attached document",
    "is document", "is case", "plaintiff's title", "plaintiff ka title",
    "mere case", "mere uploaded", "is file me", "in this case", "petitioner's argument",
    "evidence", "prove", "proves", "allegation", "alleges", "alleged", "facts",
    "record", "witness", "exhibit", "court order", "order date", "purchased",
    "possession", "deposition",
]
OUT_OF_DOMAIN_SIGNALS = [
    "recipe", "cake", "bake", "poem", "poetry", "joke", "song", "lyrics",
    "weather", "cricket", "ipl", "football", "movie", "actor", "actress",
    "horoscope", "astrology", "bluetooth", "wifi", "gameplay", "gaming",
    "reverse string", "javascript tutorial", "python script",
]


def classify_intent(query: str, has_document: bool = False) -> dict:
    lowered = query.lower()

    # Check out-of-domain signals first
    has_legal_terms = any(w in lowered for w in [
        "court", "case", "law", "dhara", "section", "fir", "bail", "bns",
        "ipc", "crpc", "bnss", "bsa", "act", "rights", "petition", "judge", "advocate", "title",
        "evidence", "plaintiff", "possession", "suit", "harassment"
    ])
    if any(w in lowered for w in OUT_OF_DOMAIN_SIGNALS) and not has_legal_terms:
        return {
            "label": "OUT_OF_DOMAIN",
            "query_mode": "OUT_OF_DOMAIN",
            "domain": "out_of_domain",
            "requires_case_context": False,
            "requires_statutory_law": False,
            "jurisdiction": "India",
            "audience": "student_public",
        }

    # Fast deterministic pre-filter (no LLM call -- instant, no quota used)
    has_general_signal = any(kw in lowered for kw in GENERAL_LAW_SIGNALS)
    has_doc_signal = any(kw in lowered for kw in DOCUMENT_REFERENCE_SIGNALS)

    if not has_document:
        if has_doc_signal and has_general_signal:
            label = "MIXED"
        elif has_doc_signal:
            label = "CASE_SPECIFIC"
        else:
            label = "GENERAL_LAW"
    elif has_general_signal and not has_doc_signal:
        label = "GENERAL_LAW"  # e.g. "What is BNS Section 351?" even with a doc attached
    elif has_doc_signal and not has_general_signal:
        label = "CASE_SPECIFIC"
    elif has_doc_signal and has_general_signal:
        label = "MIXED"
    else:
        # If a document is attached and no explicit statutory section was requested,
        # default to evaluating the attached document (CASE_SPECIFIC) rather than generic law.
        label = "CASE_SPECIFIC" if has_document else None

    is_pro = any(p in lowered for p in ["jurisdiction", "sub-section", "appellant", "respondent", "ratio decidendi", "obiter"])
    audience = "professional" if is_pro else "student_public"

    if label is None:
        prompt = f"""Classify this legal question. The user {"HAS" if has_document else "has NOT"} attached a document to this chat.

Respond with ONLY this JSON:
{{"label": "CASE_SPECIFIC", "audience": "student_public"}}

label options:
- "CASE_SPECIFIC": the question is about facts/content of the attached document specifically (even short follow-ups like "and the dissent?" if document context exists).
- "GENERAL_LAW": a general legal question (a statute, section, definition, procedure) NOT tied to the specific attached document's facts -- even if a document happens to be attached.
- "MIXED": the question asks about the document's facts AND also invokes a general legal provision/concept that should be checked independently.
- "OUT_OF_DOMAIN": not about law at all.

audience: "professional" if legal-technical phrasing/strategy; else "student_public".

QUESTION: {query}

JSON:"""
        try:
            raw = call_llm(CLASSIFIER_MODEL, prompt)
            cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
            result = json.loads(cleaned)
            label = result.get("label", "GENERAL_LAW")
            audience = result.get("audience", audience)
            if label not in ("CASE_SPECIFIC", "GENERAL_LAW", "MIXED", "OUT_OF_DOMAIN"):
                label = "GENERAL_LAW"
            if audience not in ("professional", "student_public"):
                audience = "student_public"
        except Exception:
            label = "CASE_SPECIFIC" if has_document else "GENERAL_LAW"

    return {
        "label": label,
        "query_mode": label,
        "domain": "out_of_domain" if label == "OUT_OF_DOMAIN" else "legal",
        "requires_case_context": label in ("CASE_SPECIFIC", "MIXED"),
        "requires_statutory_law": label in ("GENERAL_LAW", "MIXED"),
        "jurisdiction": "India",
        "audience": audience,
    }
