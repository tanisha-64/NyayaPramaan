"""
intent_rules.py  (NEW FILE)  ->  ai_core/router/intent_rules.py

Deterministic pre-filter for 4-way routing. An attached document must NOT force
CASE_SPECIFIC: "what is crime?" with a PDF attached is GENERAL_LAW.

Uses WORD-BOUNDARY regexes (the old substring list matched "fir" inside "first",
"act" inside "fact", etc.).

prefilter_label(query, has_document) -> "CASE_SPECIFIC" | "GENERAL_LAW" | "MIXED" | None
None = undecided, let the LLM classifier decide.
"""
import re

_YEAR = re.compile(r"\b(1[5-9]\d\d|20\d\d)\b")

# Words that clearly point at the attached document / its parties / its facts.
_DOC = re.compile(
    r"\b(this|is|iss|uss|the)\s+(case|document|file|pdf|judgment|judgement|order|petition|suit|appeal)\b"
    r"|\b(uploaded|attached)\b"
    r"|\b(plaintiffs?|defendants?|petitioners?|respondents?|appellants?|accused|complainant)\b"
    r"|\b(hearings?|dates?|witness(?:es)?|exhibits?|deposition|award|decree|verdict|held)\b"
    r"|\b(summar\w*|summary|saransh)\b"
    r"|\b(iski|iska|iske|isme|isko|isse|uski|uska|uske|usme)\b"
    r"|\b(mere|meri|mera)\s+(case|file|document)\b"
    r"|\b(is|iss)\s+(case|file|document|pdf)\b"
    r"|इस\s*(केस|फाइल|दस्तावेज़)|सुनवाई|तारीख",
    re.I,
)
# A document IS attached and the question asks about evidence/the claim/the dispute inside it --
# this ALWAYS means "look in the document first". Only applied when has_document, below.
_EVIDENCE = re.compile(r"\b(evidence|proves?|proof|claims?|disputes?)\b", re.I)
# Statute / general-law markers
_STATUTE = re.compile(
    r"\b(section|sec|dhara|article|schedule)\b\s*\.?\s*\d+"
    r"|\b\d+\s*(?:of\s+)?(bns|bnss|bsa|ipc|crpc|cpc)\b"
    r"|\b(bns|bnss|bsa|ipc|crpc|cpc|constitution|bare act|fundamental rights?)\b"
    r"|\b(fir|bail|anticipatory bail|punishment|penalty|adverse possession|limitation act|statute)\b"
    r"|धारा",
    re.I,
)
# "what is X", "define X", "X kya hota hai" -> definitional / general-law
_DEFINITION = re.compile(
    r"^\s*(what\s+(is|are|does|do)|define|meaning\s+of|explain|difference\s+between|"
    r"how\s+(to|do|does|can)|can\s+i|punishment\s+for|procedure\s+(for|to)|which\s+(law|section|act))\b"
    r"|\bkya\s+hota\s+hai\b|\bkya\s+hai\b.*\b(law|dhara|section|kanoon)\b|\bmeaning\b|\bkaise\b|क्या\s+होता",
    re.I,
)


def prefilter_label(query: str, has_document: bool) -> str | None:
    q = query or ""
    doc = bool(_DOC.search(q) or _YEAR.search(q))
    statute = bool(_STATUTE.search(q))
    definition = bool(_DEFINITION.match(q) or _DEFINITION.search(q))

    if not has_document:
        if doc and statute:
            return "MIXED"
        if doc:
            return "CASE_SPECIFIC"
        return "GENERAL_LAW"

    # a document IS attached -- "what evidence/claim/dispute..." always means "check the document"
    doc = doc or bool(_EVIDENCE.search(q))
    if doc and statute:
        return "MIXED"
    if doc:
        return "CASE_SPECIFIC"
    if statute or definition:
        return "GENERAL_LAW"
    return None  # ambiguous -> LLM decides (failure => GENERAL_LAW, never fake case facts)