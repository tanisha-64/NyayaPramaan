"""
Timeline extractor — chronological, evidence-linked events from a case file.

Deterministic on purpose (no LLM): every event is a date that literally appears in the document together with the
sentence that contains it and the page it was found on. Nothing is generated, so a date, page or event cannot be
invented, and extracting a timeline costs no LLM call.

What the label means (it is derived from the words of the sentence, never assumed):
  Hearing (recorded)         the sentence says a hearing took place ("was heard", "appeared before", "arguments heard")
  Hearing (listed/next date) the sentence says it is listed / adjourned / posted for that date: it has NOT happened yet
                             as far as the sentence says
  Hearing (date mentioned)   a hearing is mentioned near the date but the sentence does not say whether it took place
  Order/Judgment, Filing, FIR, Deadline, Incident (as stated), Date mentioned  — same principle
A date that merely appears in the text is therefore never presented as a hearing that occurred.

extract_timeline(case_text) -> str keeps the original string contract ("- <date> -- <event>" lines, or
"No explicit dates found."), now with the page reference appended. extract_timeline_events(case_text) -> list[dict]
exposes the structured form (date, iso, event_type, status, page, page_estimated, text).
"""
import re
from datetime import date

from ai_core.rag.document_chunker import pages_from_text

NO_DATES_MESSAGE = "No explicit dates found."
MAX_EVENTS = 150
MAX_SENTENCE_CHARS = 280

_MONTHS = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_MONTH_NUM = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_I = re.IGNORECASE
_D_MON_Y = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?[\s.,/-]*(?:day\s+of\s+)?({_MONTHS})\.?[\s,/-]*(\d{{4}})\b", _I)
_MON_D_Y = re.compile(rf"\b({_MONTHS})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", _I)
_NUMERIC = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")

# sentence boundary: terminal punctuation + space + a capital/bracket, but not after common abbreviations or after a
# 1-3 digit paragraph number such as "12." (a 4-digit year before the full stop still ends a sentence)
_SENT_BOUNDARY = re.compile(r"(?<!\b\d\.)(?<!\b\d\d\.)(?<!\b\d\d\d\.)(?<!\bNo)(?<!\bNos)(?<!\bRs)(?<!\bSec)(?<!\bDr)(?<!\bMr)(?<!\bMrs)(?<!\bSri)(?<!\bSmt)(?<!\bSh)(?<!\bvs)(?<!\bv)(?<=[.;!?])\s+(?=[A-Z(\[]|\d{1,3}\.\s+[A-Z])")

_SCHEDULED = re.compile(r"\b(next date|listed (?:for|on)|list(?:ed)? on|posted (?:for|on|to)|adjourned (?:to|till|for)|fixed for|to be heard|stands? (?:adjourned|listed)|put up on|returnable on|to appear (?:on|before)|shall appear|re-?notified)\b", _I)
_RECORDED = re.compile(r"\b(was heard|were heard|heard (?:the )?(?:learned )?(?:counsel|parties|arguments)|heard on|hearing (?:was )?held|appeared (?:before|on)|argued|arguments were heard|came up for hearing|taken up for hearing|reserved (?:the )?(?:judg(?:e)?ment|order))\b", _I)
_ORDER = re.compile(r"\b(order(?:ed)? dated|judg(?:e)?ment (?:dated|pronounced|delivered)|pronounced|decreed|dismissed|allowed|disposed|decided on|order passed|passed (?:the|an) order)\b", _I)
_FIR = re.compile(r"\bfir\b|\bfirst information report\b", _I)
_FILING = re.compile(r"\b(filed|instituted|presented|lodged|preferred|registered|received|submitted|initiated)\b", _I)
_DEADLINE = re.compile(r"\b(within \d+|on or before|not later than|time (?:is )?(?:granted|extended)|last date|deadline|period of limitation)\b", _I)
_INCIDENT = re.compile(r"\b(incident|occurred|accident|offence (?:was )?committed|alleged(?:ly)?)\b", _I)
_HEARING = re.compile(r"\bhearing\b|\bheard\b", _I)

LABELS = {
    ("hearing", "scheduled"): "Hearing (listed/next date)",
    ("hearing", "recorded"): "Hearing (recorded)",
    ("hearing", "mentioned"): "Hearing (date mentioned)",
    ("order", "recorded"): "Order/Judgment",
    ("filing", "recorded"): "Filing",
    ("fir", "recorded"): "FIR",
    ("deadline", "stated"): "Deadline",
    ("incident", "stated"): "Incident (as stated)",
    ("other", "mentioned"): "Date mentioned",
}


def _to_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d) if 1900 <= y <= 2100 else None
    except ValueError:
        return None


def find_dates(text: str) -> list[tuple[int, int, str, str | None]]:
    """[(start, end, date_text_as_written, iso_or_None)] without overlaps, in text order."""
    found: list[tuple[int, int, str, str | None]] = []

    def add(m, d):
        found.append((m.start(), m.end(), m.group(0).strip(), d.isoformat() if d else None))

    for m in _D_MON_Y.finditer(text):
        add(m, _to_date(int(m.group(3)), _MONTH_NUM[m.group(2).lower()[:3]], int(m.group(1))))
    for m in _MON_D_Y.finditer(text):
        add(m, _to_date(int(m.group(3)), _MONTH_NUM[m.group(1).lower()[:3]], int(m.group(2))))
    for m in _NUMERIC.finditer(text):
        # Indian convention dd/mm/yyyy; an impossible reading (month > 12) yields no iso rather than a guess.
        add(m, _to_date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
    found.sort()
    out, last_end = [], -1
    for item in found:
        if item[0] >= last_end:
            out.append(item)
            last_end = item[1]
    return out


# A sentence can hold several events ("heard on 5 May 2020 and adjourned to 7 June 2020"). Each date is classified on its
# own clause so the first is not labelled with the second's wording.
_CLAUSE_SPLIT = re.compile(r"[;,]\s+|\s+(?:and|but|whereas|while|thereafter|then|after which)\s+", _I)
MIN_CLAUSE_WORDS = 6


def _clause_around(sentence: str, start: int, end: int) -> str:
    cuts = [(0, 0)] + [(m.start(), m.end()) for m in _CLAUSE_SPLIT.finditer(sentence)] + [(len(sentence), len(sentence))]
    spans = [(cuts[i][1], cuts[i + 1][0]) for i in range(len(cuts) - 1)]
    idx = next((i for i, (a, b) in enumerate(spans) if a <= start < b or (a < end <= b)), None)
    if idx is None:
        return sentence
    a, b = spans[idx]
    if len(sentence[a:b].split()) < MIN_CLAUSE_WORDS:       # "On 12.03.2019," on its own says nothing: take the next clause too
        if idx + 1 < len(spans):
            b = spans[idx + 1][1]
        elif idx > 0:
            a = spans[idx - 1][0]
    return sentence[a:b]


def _sentence_around(text: str, start: int, end: int) -> tuple[str, str]:
    """(sentence for display, the clause around the date used to classify it)."""
    bounds = [0] + [m.end() for m in _SENT_BOUNDARY.finditer(text)] + [len(text)]
    lo = max(b for b in bounds if b <= start)
    hi = min(b for b in bounds if b >= end)
    full = text[lo:hi]
    lead = len(full) - len(full.lstrip())
    sentence = full.strip()
    clause = _clause_around(sentence, start - lo - lead, end - lo - lead)
    if len(sentence) > MAX_SENTENCE_CHARS:      # keep the date inside the window
        a = max(0, start - lo - lead - MAX_SENTENCE_CHARS // 2)
        sentence = ("…" if a else "") + sentence[a:a + MAX_SENTENCE_CHARS].strip() + "…"
    return sentence, clause


def classify_event(sentence: str) -> tuple[str, str]:
    """(event_type, status) from the wording of the sentence only."""
    if _SCHEDULED.search(sentence):
        return "hearing", "scheduled"
    if _RECORDED.search(sentence):
        return "hearing", "recorded"
    if _FIR.search(sentence) and re.search(r"\b(registered|lodged|dated|filed)\b", sentence, _I):
        return "fir", "recorded"
    if _ORDER.search(sentence):
        return "order", "recorded"
    if _FILING.search(sentence):
        return "filing", "recorded"
    if _DEADLINE.search(sentence):
        return "deadline", "stated"
    if _INCIDENT.search(sentence):
        return "incident", "stated"
    if _HEARING.search(sentence):
        return "hearing", "mentioned"
    return "other", "mentioned"


def extract_timeline_events(case_text: str) -> list[dict]:
    if not case_text or not case_text.strip():
        return []
    pages, estimated = pages_from_text(case_text)
    events, seen = [], set()
    for page_number, page_text in pages:
        flat = re.sub(r"\s+", " ", page_text)
        for start, end, date_text, iso in find_dates(flat):
            sentence, clause = _sentence_around(flat, start, end)
            key = (iso or date_text.lower(), sentence.lower())
            if key in seen:
                continue
            seen.add(key)
            event_type, status = classify_event(clause)
            events.append({"date": date_text, "iso": iso, "event_type": event_type, "status": status,
                           "label": LABELS[(event_type, status)], "page": page_number, "page_estimated": estimated,
                           "text": sentence})
    # chronological; dates that could not be normalised keep document order after the dated ones
    indexed = list(enumerate(events))
    indexed.sort(key=lambda p: (p[1]["iso"] is None, p[1]["iso"] or "", p[0]))
    return [e for _, e in indexed][:MAX_EVENTS]


def render_timeline(events: list[dict]) -> str:
    if not events:
        return NO_DATES_MESSAGE
    lines = []
    for e in events:
        page = f"Page ~{e['page']}" if e.get("page_estimated") else f"Page {e['page']}"
        lines.append(f"- {e['date']} -- {e['label']}: {e['text']} ({page})")
    return "\n".join(lines)


def extract_timeline(case_text: str) -> str:
    return render_timeline(extract_timeline_events(case_text))


# ---- timeline questions in chat -------------------------------------------------------------------------------

_TIMELINE_QUERY = re.compile(
    r"\b(timeline|chronolog\w*|sequence of events|dates?|hearings?|next date|adjourn\w*|when (?:was|did|is|were)|"
    r"filed on|date of|orders? passed|kab|tareekh|tarikh|sunwai)\b|तारीख|कब|सुनवाई", _I)


def is_timeline_query(query: str) -> bool:
    return bool(_TIMELINE_QUERY.search(query or ""))


def timeline_evidence_chunks(case_text: str, case_id: str, limit: int = 12) -> list[dict]:
    """Date-bearing sentences of the case, shaped like retrieved chunks (page-tagged, verbatim text), so a chronology
    question can be answered from the whole document and verified/cited by the same pipeline as any other evidence."""
    chunks = []
    for i, e in enumerate(extract_timeline_events(case_text)[:limit]):
        chunks.append({"id": f"timeline-{i}", "case_id": case_id, "page_number": e["page"], "chunk_text": e["text"],
                       "retrieved_by": ["timeline"]})
    return chunks
