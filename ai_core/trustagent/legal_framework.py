"""
Which body of law applies, and as of when — for general legal questions.

India replaced three colonial-era laws with new ones on 1 July 2024:
    IPC (1860)  -> BNS (2023)      CrPC (1973) -> BNSS (2023)      Indian Evidence Act (1872) -> BSA (2023)
As a general rule offences committed BEFORE that date continue to be governed by the old laws, and offences on or after
it by the new ones; the details (pending cases, procedure, savings clauses) are matters for the statutes and a lawyer.

This module is deterministic (no LLM) and conservative:
  * it only reads what the question STATES (acts named, dates/years given); nothing is assumed about the facts;
  * it never maps one section number to another: section-level mappings are exactly where invented answers hide, and
    must come from a retrieved source;
  * it returns a short, hedged note that is shown to the user and added to the answer prompt, plus the date the law is
    stated "as of".
"""
import re
from datetime import date

from ai_core.timeline.extractor import find_dates

BNS_IN_FORCE_FROM = date(2024, 7, 1)
_I = re.IGNORECASE

OLD_ACTS = {
    "IPC": re.compile(r"\bipc\b|\bindian penal code\b", _I),
    "CrPC": re.compile(r"\bcr\.?\s?p\.?\s?c\b|\bcode of criminal procedure\b", _I),
    "Indian Evidence Act": re.compile(r"\bindian evidence act\b|\biea\b", _I),
}
NEW_ACTS = {
    "BNS": re.compile(r"\bbns\b|\bbharatiya nyaya sanhita\b", _I),
    "BNSS": re.compile(r"\bbnss\b|\bbharatiya nagarik suraksha sanhita\b", _I),
    "BSA": re.compile(r"\bbsa\b|\bbharatiya sakshya adhiniyam\b", _I),
}
# "BNS 2023", "Indian Penal Code, 1860": the year names the Act, it is not a date in the user's facts
_ACT_YEAR = re.compile(r"(?:sanhita|adhiniyam|act|code|ipc|crpc|bns|bnss|bsa)[\s,]*(?:of\s+)?(?:18|19|20)\d{2}", _I)
_YEAR = re.compile(r"\b(18\d{2}|19\d{2}|20\d{2})\b")

_OLD_TO_NEW = "IPC/CrPC/Indian Evidence Act"
_NEW_NAMES = "BNS/BNSS/BSA"


def _periods(text: str) -> tuple[str, list[str]]:
    """('pre'|'post'|'straddle'|'unknown', iso dates / years found) from dates the user wrote."""
    stripped = _ACT_YEAR.sub(" ", text)
    pre = post = False
    seen: list[str] = []
    for _, _, _, iso in find_dates(stripped):
        if iso:
            seen.append(iso)
            d = date.fromisoformat(iso)
            pre |= d < BNS_IN_FORCE_FROM
            post |= d >= BNS_IN_FORCE_FROM
    if not seen:
        for m in _YEAR.finditer(stripped):
            y = int(m.group(1))
            if y <= 2023:
                pre = True
            elif y >= 2025:
                post = True
            # 2024 alone is ambiguous (before or after 1 July): no inference
            if y != 2024:
                seen.append(str(y))
    period = "straddle" if pre and post else "pre" if pre else "post" if post else "unknown"
    return period, seen


def analyze_legal_framework(query: str, today: date | None = None) -> dict:
    today = today or date.today()
    text = query or ""
    old = [n for n, p in OLD_ACTS.items() if p.search(text)]
    new = [n for n, p in NEW_ACTS.items() if p.search(text)]
    period, ref_dates = _periods(text)

    note = None
    if old or new or period != "unknown":
        base = (f"The {_NEW_NAMES} replaced the {_OLD_TO_NEW} with effect from 1 July 2024. As a general rule, offences "
                f"committed before that date are still governed by the older laws and later offences by the new ones.")
        if period == "unknown":
            tail = "Your question does not say when the offence happened, so confirm which law applies before relying on a section number."
        elif period == "pre":
            tail = f"The date(s) you mention point to before 1 July 2024, where the {_OLD_TO_NEW} would generally apply."
            if new:
                tail += f" You referred to the {', '.join(new)}; check whether that is the right Act for your dates."
        elif period == "post":
            tail = f"The date(s) you mention are on or after 1 July 2024, where the {_NEW_NAMES} would generally apply."
            if old:
                tail += f" You referred to the {', '.join(old)}; check whether that is the right Act for your dates."
        else:
            tail = "You mention dates on both sides of 1 July 2024, so both regimes may be relevant."
        note = f"{base} {tail} Section numbers differ between the old and new laws; verify them in the official text."

    return {
        "jurisdiction": "India",
        "law_as_of": today.isoformat(),
        "new_laws_in_force_from": BNS_IN_FORCE_FROM.isoformat(),
        "mentions_old_acts": old,
        "mentions_new_acts": new,
        "period": period,
        "reference_dates": ref_dates[:5],
        "relevant": note is not None,
        "note": note,
    }


def prompt_rule(analysis: dict) -> str:
    base = ("Indian law is stated as of " + analysis["law_as_of"] + ". The Bharatiya Nyaya Sanhita (BNS), Bharatiya Nagarik "
            "Suraksha Sanhita (BNSS) and Bharatiya Sakshya Adhiniyam (BSA) replaced the IPC, CrPC and Indian Evidence Act on "
            "1 July 2024. Never convert an old section number to a new one (or the reverse) unless the EVIDENCE gives the mapping.")
    return base + (f" {analysis['note']}" if analysis.get("note") else "")
