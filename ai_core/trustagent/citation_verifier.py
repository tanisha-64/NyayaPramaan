"""ai_core/trustagent/citation_verifier.py (NEW)
Deterministic citation-existence check: finds every "Section X Act" mention in a
generated answer and verifies it against the real statute_sections table BEFORE
the answer is shown. This never trusts the LLM's own citation -- only the database
row it points at. This is the "Pramaan" (proof) layer."""
import re

_CITE = re.compile(
    r"\b(?:section|sec|s|dhara)\.?\s*(\d{1,3}[A-Za-z]{0,2})\b.{0,25}?\b"
    r"(bnss|bns|bsa|ipc|crpc|iea|ni act|nia|negotiable instruments act)\b"
    r"|\b(bnss|bns|bsa|ipc|crpc|iea|ni act|nia|negotiable instruments act)\b"
    r"\s*(?:section|sec|s|dhara)?\.?\s*(\d{1,3}[A-Za-z]{0,2})\b",
    re.I,
)
_ALIAS = {"NI ACT": "NI", "NIA": "NI", "NEGOTIABLE INSTRUMENTS ACT": "NI"}


def extract_citations(text: str) -> list[tuple[str, str]]:
    """[(act, section)] mentioned in text, de-duplicated, first-seen order."""
    seen, out = set(), []
    for m in _CITE.finditer(text or ""):
        g = m.groups()
        num, act = (g[0], g[1]) if g[0] else (g[3], g[2])
        act = _ALIAS.get(act.upper(), act.upper())
        key = (act, num.upper())
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def verify_citations(client, text: str) -> list[dict]:
    """One Pramaan card per citation mentioned in `text`, checked against the real
    statute_sections table. verified=False means the LLM named a section that does
    NOT exist in our verified database -- a likely hallucination. Never raises."""
    cards = []
    for act, section in extract_citations(text):
        try:
            rows = (client.table("statute_sections")
                    .select("act_name, section, heading, text, source_url, page")
                    .eq("act", act).eq("section", section).limit(1).execute().data or [])
        except Exception:  # noqa: BLE001
            rows = []
        if rows:
            r = rows[0]
            quote = re.sub(r"\s+", " ", r.get("text") or "")[:280]
            cards.append({"act": act, "section": section, "act_name": r.get("act_name"),
                          "heading": r.get("heading"), "quote": quote, "source_url": r.get("source_url"),
                          "page": r.get("page"), "verified": True})
        else:
            cards.append({"act": act, "section": section, "act_name": None, "heading": None,
                          "quote": None, "source_url": None, "page": None, "verified": False})
    return cards