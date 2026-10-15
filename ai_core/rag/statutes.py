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
            "batao", "mein", "karne", "wala", "wali", "what", "which", "ke", "ka", "ki", "k", "saza", "chahiye", "kitni",
            "kitna", "kaise", "kya", "mana", "diya", "kiya", "mera", "meri", "mere", "mujhe", "krna", "kare"}
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
    """Exact row for an explicit lookup; otherwise the best heading matches (+ best text matches in BNS/BNSS/BSA, whose
    PDFs have no usable headings). A match needs >= 2 of the question's words (1 when it has <= 2), so loosely related
    sections never become 'evidence'. Never raises."""
    try:
        ex = explicit_lookup(query)
        t = client.table("statute_sections")
        if ex:
            return t.select("*").eq("act", ex[0]).eq("section", ex[1]).limit(1).execute().data or []
        ql = query.lower()
        toks = sorted((w for w in content_tokens(query) if w not in _GENERIC), key=lambda w: ql.find(w) % 10_000)[:4]
        if not toks:
            return []
        need = 1 if len(toks) <= 2 else 2
        rows = t.select("*").or_(",".join(f"heading.ilike.%{w}%" for w in toks)).limit(40).execute().data or []
        score = lambda r: len(set(toks) & content_tokens(r.get("heading") or ""))
        best = max((score(r) for r in rows), default=0)
        out = sorted([r for r in rows if best >= need and score(r) == best], key=lambda r: r["act"])[:limit]
        have = {r["act"] for r in out}
        trows = t.select("*").or_(",".join(f"text.ilike.%{w}%" for w in toks)).limit(80).execute().data or []

        def hits(r):  # distinct query words in the opening of the section
            return sum(w in _clean(r["text"])[:300].lower() for w in toks)

        def tscore(r):  # more distinct words, a penalty clause, and many mentions of the topic rank higher
            body = _clean(r["text"]).lower()
            return hits(r) * 2 + ("shall be punished" in body) + min(sum(body.count(w) for w in toks), 20) * 0.1

        for act in ("BNS", "BNSS", "BSA"):
            cand = sorted([r for r in trows if r["act"] == act and act not in have and hits(r) >= need], key=lambda r: -tscore(r))
            out += cand[:2]
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


def statute_evidence(r: dict, limit: int = 1800) -> str:
    """Text given to the LLM: the opening plus every 'shall be punished' sentence further down (long sections such as
    BNS 303 put the penalty after pages of explanations)."""
    t = _clean(r["text"])
    if len(t) <= limit:
        return t
    pun = re.findall(r"[^.]*shall be punished[^.]*\.", t[700:])[:3]
    return (t[:700] + " ... " + " ".join(p.strip() for p in pun))[:limit]