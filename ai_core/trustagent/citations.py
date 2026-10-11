"""
Citation checking. A page reference in an answer is only trustworthy if that page was actually among the
retrieved passages the answer was generated from. Everything here is deterministic (no LLM).
"""
import re

# "[Page 3]", "[Page 3, 5]", "[file.pdf — Page 3]", "Page 3", "pages 3-5", "pg. 4", "p. 7", Hindi "पृष्ठ 3"
_PAGE_REF = re.compile(
    r"(?:\bpages?|\bpgs?\.?|\bpp?\.|पृष्ठ|पेज)\s*(\d+(?:\s*(?:,|&|and|और|-|–|to)\s*\d+)*)",
    re.IGNORECASE,
)
_BRACKET_WITH_PAGE = re.compile(r"\s*\[[^\[\]]*?(?:\bpages?|\bpgs?\.?|पृष्ठ|पेज)\s*\d[^\[\]]*\]", re.IGNORECASE)
_SPECIFIC_TOKENS = [
    re.compile(r"\b(?:1[89]|20)\d{2}\b"),                                          # years
    re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-](?:\d{4}|\d{2})\b"),                    # dd.mm.yyyy
    re.compile(r"(?:₹|\bRs\.?|\bINR)\s*[\d,]+(?:\.\d+)?", re.IGNORECASE),           # money
    re.compile(r"\bsections?\s+\d+[A-Za-z]?(?:\(\d+\))?", re.IGNORECASE),           # section numbers
]


def extract_cited_pages(text: str) -> set[int]:
    pages: set[int] = set()
    for m in _PAGE_REF.finditer(text or ""):
        chunk = m.group(1)
        if re.search(r"\d\s*(?:-|–|to)\s*\d", chunk):
            a, b = [int(x) for x in re.findall(r"\d+", chunk)[:2]]
            if 0 < b - a <= 50:
                pages.update(range(a, b + 1))
                continue
        pages.update(int(x) for x in re.findall(r"\d+", chunk))
    return {p for p in pages if p > 0}


def check_citations(answer: str, retrieved_pages: set[int]) -> dict:
    """Splits cited pages into those backed by retrieved passages and those that are not."""
    cited = extract_cited_pages(answer)
    valid = sorted(p for p in cited if p in retrieved_pages)
    invalid = sorted(p for p in cited if p not in retrieved_pages)
    return {"cited": sorted(cited), "valid": valid, "invalid": invalid}


def strip_invalid_bracket_citations(answer: str, invalid_pages: list[int]) -> str:
    """Removes bracketed citations like "[Page 9]" whose pages were not retrieved. Inline mentions are left alone
    (rewriting prose is riskier than flagging it)."""
    if not invalid_pages:
        return answer
    bad = set(invalid_pages)

    def repl(m: re.Match) -> str:
        pages = extract_cited_pages(m.group(0))
        return "" if pages and pages <= bad else m.group(0)

    return _BRACKET_WITH_PAGE.sub(repl, answer)


def _norm(s: str) -> str:
    return re.sub(r"[\s,]+", "", s.lower())


def ungrounded_specifics(answer: str, evidence: str) -> list[str]:
    """Years, dates, amounts and section numbers that appear in the answer but nowhere in the evidence.
    Advisory signal (the prompt itself may legitimately mention e.g. 'BNS 2023'), reported as a count."""
    ev = _norm(evidence or "")
    found: list[str] = []
    for pat in _SPECIFIC_TOKENS:
        for m in pat.finditer(answer or ""):
            tok = m.group(0)
            if _norm(tok) not in ev and tok not in found:
                found.append(tok)
    return found
