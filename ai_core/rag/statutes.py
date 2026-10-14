"""statutes.py -> ai_core/rag/statutes.py
Verbatim statute text (loaded by scripts/ingest_statutes.py) in table `statute_sections`.
Explicit questions ("section 303 BNS", "IPC 302") are answered ONLY from this table."""
import re

from ai_core.rag.case_text_fallback import content_tokens

_ACT = r"(bnss|bns|bsa|ipc|crpc)"
_NUM = r"(\d{1,3}[A-Za-z]{0,2})"
_EXPLICIT = re.compile(rf"\b(?:section|sec|s|dhara)\.?\s*{_NUM}\b.{{0,30}}?\b{_ACT}\b|\b{_ACT}\b\s*(?:section|sec|s|dhara)?\.?\s*{_NUM}\b", re.I)
_GENERIC = {"punish", "punishment", "law", "legal", "bns", "bnss", "bsa", "ipc", "crpc", "section", "act", "under",
            "penalty", "offence", "offense", "crime", "sanhita", "code", "kya", "hai", "matlab", "case", "liye", "btao",
            "batao", "mein", "karne", "wala", "wali", "what", "which", "ke", "ka", "ki", "k"}
_AMEND = re.compile(r"\s*STATE AMENDMENTS?\b.*", re.S)   # state-level amendments follow some sections in the PDF


def _clean(text: str) -> str:
    return _AMEND.sub("", re.sub(r"[ \t]+", " ", text or "")).strip()


def explicit_lookup(query: str):
    """('BNS', '303') when the question names an act AND a section number, else None."""
    m = _EXPLICIT.search(query or "")
    if not m:
        return None
    g = m.groups()
    num, act = (g[0], g[1]) if g[0] else (g[3], g[2])
    return act.upper(), num.upper()


def find_sections(client, query: str, limit: int = 3) -> list[dict]:
    """Exact row for an explicit lookup; otherwise the best heading matches (+ best text match in BNS/BNSS/BSA, whose
    PDFs have no usable headings). Never raises."""
    try:
        ex = explicit_lookup(query)
        t = client.table("statute_sections")
        if ex:
            return t.select("*").eq("act", ex[0]).eq("section", ex[1]).limit(1).execute().data or []
        toks = [w for w in content_tokens(query) if w not in _GENERIC]
        if not toks:
            return []
        toks = toks[:4]
        rows = t.select("*").or_(",".join(f"heading.ilike.%{w}%" for w in toks)).limit(30).execute().data or []
        score = lambda r: len(set(toks) & content_tokens(r.get("heading") or ""))
        best = max((score(r) for r in rows), default=0)
        out = sorted([r for r in rows if best and score(r) == best], key=lambda r: r["act"])[:limit]
        have = {r["act"] for r in out}
        trows = t.select("*").or_(",".join(f"text.ilike.%{w}%" for w in toks)).limit(60).execute().data or []

        def tscore(r):  # distinct query words in the opening of the section (+ bonus for a penalty clause)
            head = _clean(r["text"])[:300].lower()
            return sum(w in head for w in toks) * 2 + ("shall be punished" in head)

        for act in ("BNS", "BNSS", "BSA"):
            cand = sorted([r for r in trows if r["act"] == act and act not in have], key=lambda r: -tscore(r))
            out += [r for r in cand[:2] if tscore(r) >= 2]
        return out
    except Exception:  # noqa: BLE001  (table missing / network) -> no statute evidence, never a crash
        return []


def statute_sources(rows: list[dict], status: str = "verified") -> list[dict]:
    return [{"name": f"{r['act_name']} — Section {r['section']}" + (f" ({r['heading']})" if r.get("heading") else ""),
             "type": "statute", "url": r["source_url"] + (f"#page={r['page']}" if r.get("page") else ""),
             "verification_status": status, "jurisdiction": "India", "section": f"Section {r['section']}",
             "excerpt": re.sub(r"\s+", " ", _clean(r["text"]))[:500]} for r in rows]


def statute_text(r: dict, limit: int = 1500) -> str:
    return _clean(r["text"])[:limit]