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

# Fast keyword pre-filter -- obvious general-law signals even when a doc is attached.
# Matched on WORD boundaries (see _has): substring matching made "fir" fire on "first"/"confirm" and "act" on "fact".
# WEAK signals are common words that also appear in questions about the document itself ("what punishment did the
# court impose?"); on their own they must not override a clear document reference.
WEAK_GENERAL_SIGNALS = ["fir", "bail", "punishment", "what is the punishment", "penalty", "offence"]
STRONG_GENERAL_SIGNALS = [
    "section", "bns", "ipc", "crpc", "bnss", "bsa", "cpc",
    "which law", "which section", "legal definition of", "what does the law say",
    "statute", "bare act", "constitution article", "fundamental right", "dhara",
    "adverse possession",
]
GENERAL_LAW_SIGNALS = WEAK_GENERAL_SIGNALS + STRONG_GENERAL_SIGNALS
GENERAL_CONCEPT_PHRASES = ["adverse possession"]
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
    # added: questions that point at the document without saying "this case"
    "the accused", "the appellant", "the complainant", "the judge", "the court held", "did the court",
    "was convicted", "was acquitted", "was sentenced", "the order", "the judgment", "according to the document",
    "in the document", "document me", "file me", "iss case", "is pdf", "the witnesses",
]
# "page 3", "on p. 4": an explicit page reference is a document reference.
_PAGE_REFERENCE = re.compile(r"\b(?:page|pg|p)\.?\s*\d+\b", re.IGNORECASE)
# Phrases that ask for the LAW itself; they keep a weak general signal from being demoted.
_LAW_ASK = re.compile(r"\b(provision|law|legal|under|kanoon|kaanoon|dhara|section|act)\b", re.IGNORECASE)
OUT_OF_DOMAIN_SIGNALS = [
    "recipe", "cake", "bake", "poem", "poetry", "joke", "song", "lyrics",
    "weather", "cricket", "ipl", "football", "movie", "actor", "actress",
    "horoscope", "astrology", "bluetooth", "wifi", "gameplay", "gaming",
    "reverse string", "javascript tutorial", "python script",
]
LEGAL_TERMS = [
    "court", "case", "law", "dhara", "section", "fir", "bail", "bns", "ipc", "crpc", "bnss", "bsa", "act", "rights",
    "petition", "judge", "advocate", "title", "evidence", "plaintiff", "possession", "suit", "harassment",
]


def _has(text: str, signals: list[str]) -> bool:
    """True if any signal occurs as whole word(s) (a trailing plural 's' is allowed)."""
    return any(re.search(rf"(?<!\w){re.escape(sig.strip())}s?(?!\w)", text) for sig in signals)


def classify_intent(query: str, has_document: bool = False) -> dict:
    lowered = query.lower()

    # Check out-of-domain signals first
    has_legal_terms = _has(lowered, LEGAL_TERMS)
    if _has(lowered, OUT_OF_DOMAIN_SIGNALS) and not has_legal_terms:
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
    has_strong_general = _has(lowered, STRONG_GENERAL_SIGNALS)
    has_weak_general = _has(lowered, WEAK_GENERAL_SIGNALS)
    has_general_signal = has_strong_general or has_weak_general
    # Legal CONCEPT phrases contain words that are also document-reference signals ("adverse possession" -> "possession").
    # They must not make a pure law question look like a question about the open document.
    doc_view = lowered
    for phrase in GENERAL_CONCEPT_PHRASES:
        doc_view = doc_view.replace(phrase, " ")
    has_doc_signal = _has(doc_view, DOCUMENT_REFERENCE_SIGNALS) or bool(_PAGE_REFERENCE.search(doc_view))

    if has_doc_signal and has_weak_general and not has_strong_general and not _LAW_ASK.search(lowered):
        has_general_signal = False      # "what punishment did the court impose?" is about the document

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
