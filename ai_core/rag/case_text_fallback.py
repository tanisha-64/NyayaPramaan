"""
case_text_fallback.py  (FULL REPLACEMENT)  ->  ai_core/rag/case_text_fallback.py

Deterministic, zero-LLM, zero-embedding retrieval + exact extraction over a document.
Every sentence returned is a VERBATIM (whitespace-normalised) sentence of the document.
`pages=[(page_number, text)]` (from document_chunks) gives every result a REAL page number.
"""
from __future__ import annotations

import re

_STOP = frozenset(
    "a an the of in on at to for and or is are was were be been being what which who whom "
    "when where why how did does do done give tell me all about this that these those it its "
    "with by from as has have had kya hai hain ka ki ke me mein ne ko se par aur btao batao "
    "bataiye case document file pdf uploaded please iss is yeh ye woh wo kaun kab".split()
)

_MONTHS = (
    "jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    "sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
)
YEAR_RE = re.compile(r"\b(1[5-9]\d\d|20\d\d)\b")
DATE_RE = re.compile(
    rf"\b(?:\d{{1,2}}(?:st|nd|rd|th)?[\s\-/.,]+(?:{_MONTHS})[a-z]*\.?,?[\s\-/.]+\d{{4}}"
    rf"|(?:{_MONTHS})[a-z]*\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}"
    rf"|\d{{1,2}}[\-/.]\d{{1,2}}[\-/.]\d{{2,4}})\b",
    re.I,
)
HEARING_RE = re.compile(
    r"\b(hear(?:d|ing|ings)|listed|adjourn\w*|posted for|fixed for|next date|"
    r"argued|arguments? (?:were|was) heard|sunwai)\b|सुनवाई",
    re.I,
)
_DATE_Q = re.compile(
    r"\b(dates?|hearings?|tarikh|tareekh|next date|adjourn\w*|sunwai)\b|तारीख|सुनवाई", re.I
)
_PAGE_MARK = re.compile(r"(?im)^[\s\[\-=]*page\s*(\d{1,4})(?:\s*of\s*\d+)?[\s\]\-=]*$")
_SENT_SPLIT = re.compile(r"(?<=[.!?।;])\s+|\n{2,}")

# website watermark / metadata lines that pollute extracted text
_WATERMARK = re.compile(r"Indian\s*Kanoon\s*[-–]\s*https?://\S+(?:\s+\d{1,3})?", re.I)
_HEADER_NOISE = re.compile(r"Equivalent citations|^\s*Bench\s*:|\bAuthor\s*:|\bCites\s+\d+|\bCited by\s+\d+", re.I)


def _stem(w: str) -> str:
    w = w.lower()
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _tokens(text: str) -> set[str]:
    return {
        _stem(w)
        for w in re.findall(r"[A-Za-zऀ-ॿ0-9]+", text or "")
        if len(w) > 2 and w.lower() not in _STOP
    }


content_tokens = _tokens  # public alias (used by the router to vet web sources)


def _clean(s: str) -> str:
    s = _WATERMARK.sub(" ", s or "")
    return re.sub(r"\s+", " ", s).strip(" -–—•")


# --------------------------------------------------------------------------
def split_pages(text: str) -> list[tuple[int | None, str]]:
    """[(page_number|None, page_text)] from \\f or '[Page N]' markers; else ~2500-char sections
    with page=None (page numbers are never invented)."""
    text = text or ""
    if "\f" in text:
        parts = text.split("\f")
        return [(i + 1, p.strip()) for i, p in enumerate(parts) if p.strip()]
    marks = list(_PAGE_MARK.finditer(text))
    if len(marks) >= 2:
        out = []
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            body = text[m.end():end].strip()
            if body:
                out.append((int(m.group(1)), body))
        return out
    out, buf = [], ""
    for sent in _SENT_SPLIT.split(text):
        if len(buf) + len(sent) > 2500 and buf:
            out.append((None, buf.strip()))
            buf = ""
        buf += sent + " "
    if buf.strip():
        out.append((None, buf.strip()))
    return out


def _pages(case_text: str, pages):
    return pages if pages else split_pages(case_text)


def _sentences(body: str) -> list[str]:
    out = []
    for s in _SENT_SPLIT.split(body or ""):
        s = _clean(s)
        if len(s) >= 15 and not re.search(r"\.{6,}", s):   # skip table-of-contents lines
            out.append(s)
    return out


# --------------------------------------------------------------------------
def search_case_text(case_text: str, query: str, k: int = 6, pages=None) -> list[dict]:
    q_tok = _tokens(query)
    q_years = set(YEAR_RE.findall(query or ""))
    if not q_tok and not q_years:
        return []
    cands = []
    for page, body in _pages(case_text, pages):
        sents = _sentences(body)
        for i in range(len(sents)):
            win = " ".join(sents[max(0, i - 1): i + 2])
            w_tok = _tokens(win)
            cov = len(q_tok & w_tok) / len(q_tok) if q_tok else 0.0
            year_hit = bool(q_years) and any(y in win for y in q_years)
            if q_years and not year_hit:
                continue
            if not q_years and cov < 0.34:
                continue
            score = min(1.0, 0.8 * cov + (0.5 if year_hit else 0.0))
            if score > 0:
                cands.append((score, page, i, win))
    cands.sort(key=lambda c: -c[0])
    out, used = [], []
    for score, page, i, win in cands:
        if any(p == page and abs(i - j) < 2 for p, j in used):
            continue
        used.append((page, i))
        out.append({
            "page_number": page,
            "chunk_text": win[:900],
            "similarity": round(score, 3),
            "score": round(score, 3),
            "retrieval": "lexical_case_text",
        })
        if len(out) >= k:
            break
    return out


# --------------------------------------------------------------------------
def is_date_query(query: str) -> bool:
    q = query or ""
    return bool(_DATE_Q.search(q) or YEAR_RE.search(q))


_MON = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}


def _norm_date(d: str) -> str:
    """Canonical y-m-d when parseable (so '14 March, 1950' == '14/03/1950'), else letters/digits only."""
    t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", (d or "").lower())
    m = re.match(r"(\d{1,2})[\s\-/.,]+([a-z]{3})[a-z]*\.?,?[\s\-/.]+(\d{4})", t) or None
    if m and m.group(2) in _MON:
        return f"{m.group(3)}-{_MON[m.group(2)]}-{int(m.group(1))}"
    m = re.match(r"([a-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})", t)
    if m and m.group(1) in _MON:
        return f"{m.group(3)}-{_MON[m.group(1)]}-{int(m.group(2))}"
    m = re.match(r"(\d{1,2})[\-/.](\d{1,2})[\-/.](\d{2,4})", t)
    if m:
        y = int(m.group(3)); y = y + (1900 if y > 30 else 2000) if y < 100 else y
        return f"{y}-{int(m.group(2))}-{int(m.group(1))}"
    return re.sub(r"\W+", "", t)


def _clip(sentence: str, date_text: str, width: int = 200) -> str:
    sentence = re.sub(r"^[A-Z]\.,?\s+and,?\s+", "", sentence)  # fragment left by "Section 3C." style splits
    if len(sentence) <= width:
        return sentence
    idx = sentence.lower().find((date_text or "").lower())
    start = max(0, idx - 70) if idx >= 0 else 0
    if start > 0:                                   # begin at a word boundary
        sp = sentence.find(" ", start)
        start = sp + 1 if 0 <= sp < start + 25 else start
    end = start + width
    if end < len(sentence):                         # end at a word boundary
        sp = sentence.rfind(" ", start, end)
        end = sp if sp > start + 40 else end
    return ("…" if start > 0 else "") + sentence[start:end].strip() + ("…" if end < len(sentence) else "")


def extract_events(case_text: str, pages=None) -> list[dict]:
    plist = _pages(case_text, pages)
    header_date = None
    if plist:
        m = DATE_RE.search(plist[0][1][:700])
        header_date = _norm_date(m.group(0)) if m else None
    events, seen_dates, seen_sent = [], set(), set()
    for page, body in plist:
        for s in _sentences(body):
            if _HEADER_NOISE.search(s):
                if header_date and not any(e.get("is_header") for e in events):
                    m = DATE_RE.search(s)
                    if m and _norm_date(m.group(0)) == header_date:
                        seen_dates.add(header_date)
                        events.append({"page": page, "date_text": m.group(0), "year": YEAR_RE.search(m.group(0)).group(0) if YEAR_RE.search(m.group(0)) else None,
                                       "sentence": "Date shown in the document header", "is_hearing": False, "is_header": True, "is_full_date": True})
                continue
            jd = re.search(r"DATE OF JUDGMENT\s*:\s*(" + DATE_RE.pattern + ")", s, re.I)
            if jd:  # header line "RESPONDENT: ... DATE OF JUDGMENT: 14/03/1950 BENCH: ..." -> one clean label
                nd = _norm_date(jd.group(1))
                if nd not in seen_dates:
                    seen_dates.add(nd)
                    events.append({"page": page, "date_text": jd.group(1), "year": YEAR_RE.search(jd.group(1)).group(0),
                                   "sentence": "Date of judgment", "is_hearing": False, "is_full_date": True})
                continue
            d = DATE_RE.search(s)
            y = YEAR_RE.search(s)
            if not (d or y):
                continue
            if header_date and re.match(r"^on\s+", s, re.I):  # running header repeated on every page
                m = DATE_RE.search(s[:40])
                if m and _norm_date(m.group(0)) == header_date:
                    continue
            key = s[:120].lower()
            if key in seen_sent:
                continue
            seen_sent.add(key)
            date_text = d.group(0) if d else y.group(0)
            nd = _norm_date(date_text)
            if d and nd in seen_dates:
                continue
            if d:
                seen_dates.add(nd)
            events.append({
                "page": page,
                "date_text": date_text,
                "year": (y.group(0) if y else None),
                "sentence": _clip(s, date_text),
                "is_hearing": bool(HEARING_RE.search(s)),
                "is_full_date": bool(d),
            })
    return events


def _line(e: dict) -> str:
    where = f" [Page {e['page']}]" if e.get("page") else ""
    return f"📅 {e['date_text']} — {e['sentence']}{where}"


def answer_date_question(query: str, case_text: str, hinglish: bool = False, pages=None) -> dict | None:
    """Deterministic answer for date / hearing / year questions. None => not a date question."""
    plist = _pages(case_text, pages)
    if not is_date_query(query) or not plist:
        return None
    events = extract_events(case_text, pages=plist)
    years = set(YEAR_RE.findall(query))
    wants_hearing = bool(HEARING_RE.search(query))

    if years:
        used = [e for e in events if (e.get("year") in years) or any(y in e["sentence"] for y in years)]
        if not used:
            msg = (f"Is document me {', '.join(sorted(years))} ka koi ullekh nahi mila." if hinglish else
                   f"No supporting evidence was found in the uploaded document regarding {', '.join(sorted(years))}.")
            return {"answer": msg, "events": []}
        head = (f"{', '.join(sorted(years))} se jude points:" if hinglish
                else f"What the document says about {', '.join(sorted(years))}:")
    elif wants_hearing:
        hearing = [e for e in events if e["is_hearing"] and e.get("is_full_date")]  # an Act's year is not a hearing date
        if hearing:
            used = hearing
            head = "Hearing se jude dates:" if hinglish else "Hearing-related dates in the document:"
        else:
            used = [e for e in events if e.get("is_full_date")] or events
            if not used:
                return {"answer": ("Is document me hearing ki koi tarikh nahi likhi hai." if hinglish
                                   else "No hearing dates are stated in the uploaded document."), "events": []}
            head = ("Hearing ki koi alag tarikh nahi likhi hai. Ye dates document me milti hain:" if hinglish else
                    "The document does not state specific hearing dates. These other dates are mentioned:")
    else:
        used = [e for e in events if e.get("is_full_date")] or events
        if not used:
            return {"answer": ("Is document me koi date nahi mili." if hinglish
                               else "No dates were found in the uploaded document."), "events": []}
        head = "Document me ye dates milti hain:" if hinglish else "Dates mentioned in the document:"

    used = used[:8]
    return {"answer": f"{head}\n" + "\n".join(_line(e) for e in used), "events": used}