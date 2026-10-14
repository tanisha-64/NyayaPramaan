"""
intent_classifier.py  (FULL REPLACEMENT)  ->  ai_core/router/intent_classifier.py

4-way routing. An attached document must NOT force CASE_SPECIFIC.
Order: out-of-domain check -> deterministic word-boundary pre-filter (no LLM, instant)
-> LLM only when truly ambiguous. If the LLM fails we choose GENERAL_LAW
(never pretend to answer from the document without evidence).
"""
import json
import re

from ai_core.llm_gateway import call_llm, is_llm_failure
from ai_core.router.intent_rules import prefilter_label
from ai_core.router.domain_gate import check_domain

CLASSIFIER_MODEL = "groq/openai/gpt-oss-20b"

REFUSAL_MESSAGE = (
    "I can assist only with legal research, legal documents, and "
    "legal-domain questions."
)

AUDIENCE_INSTRUCTIONS = {
    "professional": "Write for a legal professional: precise terminology, exact section numbers, procedural nuance.",
    "student_public": "Write for a student/citizen: simple plain language, briefly define legal terms.",
}

_PRO_TERMS = ("jurisdiction", "sub-section", "appellant", "respondent", "ratio decidendi", "obiter")


def _result(label: str, audience: str) -> dict:
    return {
        "label": label,
        "query_mode": label,
        "domain": "out_of_domain" if label == "OUT_OF_DOMAIN" else ("greeting" if label == "GREETING" else "legal"),
        "requires_case_context": label in ("CASE_SPECIFIC", "MIXED"),
        "requires_statutory_law": label in ("GENERAL_LAW", "MIXED"),
        "jurisdiction": "India",
        "audience": audience,
    }


def classify_intent(query: str, has_document: bool = False) -> dict:
    lowered = (query or "").lower()

    def _ask(prompt: str) -> str:
        raw = call_llm(CLASSIFIER_MODEL, prompt)
        if is_llm_failure(raw):
            raise RuntimeError("llm unavailable")
        return raw

    gate = check_domain(query, has_document, _ask)
    if gate == "greeting":
        return _result("GREETING", "student_public")
    if gate in ("off_topic", "injection"):
        return _result("OUT_OF_DOMAIN", "student_public")

    audience = "professional" if any(p in lowered for p in _PRO_TERMS) else "student_public"

    label = prefilter_label(query, has_document)
    if label is None:
        prompt = f"""Classify this legal question. The user HAS attached a document to this chat.

Respond with ONLY this JSON:
{{"label": "CASE_SPECIFIC", "audience": "student_public"}}

label options:
- "CASE_SPECIFIC": about the facts/content of the attached document (even short follow-ups).
- "GENERAL_LAW": a general legal question (statute, definition, procedure) NOT tied to the document's facts.
- "MIXED": asks about the document's facts AND a general legal provision.
- "OUT_OF_DOMAIN": not about law at all.

audience: "professional" if legal-technical phrasing/strategy; else "student_public".

QUESTION: {query}

JSON:"""
        try:
            raw = call_llm(CLASSIFIER_MODEL, prompt)
            if is_llm_failure(raw):
                raise RuntimeError("llm unavailable")
            cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
            data = json.loads(cleaned[cleaned.find("{"): cleaned.rfind("}") + 1])
            label = data.get("label", "GENERAL_LAW")
            audience = data.get("audience", audience)
            if label not in ("CASE_SPECIFIC", "GENERAL_LAW", "MIXED", "OUT_OF_DOMAIN"):
                label = "GENERAL_LAW"
            if audience not in ("professional", "student_public"):
                audience = "student_public"
        except Exception:
            label = "GENERAL_LAW"

    return _result(label, audience)