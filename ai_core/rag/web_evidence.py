"""web_evidence.py (NEW) -> ai_core/rag/web_evidence.py
Free (ddgs = DuckDuckGo, no API key) search limited to the allow-listed legal sites, then the REAL page text is
fetched and the passages that answer the question are quoted verbatim. Nothing here comes from model memory."""
import io
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import requests

from ai_core.guardrails.output_guard import redact_pii
from ai_core.rag.case_text_fallback import content_tokens
from ai_core.rag.crag_corrector import (_OFFICIAL_SITES, _SECONDARY_SITES, _search, is_legally_relevant_content,
                                        source_class, source_organization)

MAX_PAGES, TIMEOUT, MAX_BYTES = 4, 8, 2_000_000
_UA = {"User-Agent": "Mozilla/5.0 (compatible; NyayaPramaanBot/1.0)"}
_GENERIC = {"india", "indian", "law", "legal", "act", "section", "provision", "rule", "rules", "code"}
_LABEL = {"official": "Official source", "secondary": "Secondary commentary (not an authority)"}


def _search_query(question: str, ask) -> str:
    """LLM only rewrites the QUESTION into an English search query; it never supplies the answer."""
    try:
        q = (ask("Rewrite this legal question as ONE short English web-search query (max 12 words) using Indian legal "
                 "terms (Act names; a section number only if you are sure). Output only the query.\n"
                 f"QUESTION: {redact_pii(question)}") or "").strip().strip('"')
        return q.splitlines()[0][:150] if q and "high demand" not in q else question
    except Exception:  # noqa: BLE001
        return question


def _fetch(url: str) -> str:
    """Page text (HTML or PDF) from an allow-listed host only (also after redirects). '' on any problem."""
    try:
        r = requests.get(url, headers=_UA, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        if not source_class(r.url):
            return ""
        raw = r.raw.read(MAX_BYTES, decode_content=True)
        if "pdf" in r.headers.get("content-type", "").lower() or url.lower().endswith(".pdf"):
            from pypdf import PdfReader
            return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(raw)).pages[:40])
        import lxml.html
        doc = lxml.html.fromstring(raw)
        for bad in doc.xpath("//script|//style|//nav|//footer|//header"):
            bad.drop_tree()
        return doc.text_content()
    except Exception:  # noqa: BLE001
        return ""


def _passages(text: str, q_tok: set, k: int = 2, width: int = 700) -> list[str]:
    """Best non-overlapping windows of the page that cover >= half of the question's content words."""
    text = re.sub(r"\s+", " ", text or "")
    scored = []
    for i in range(0, max(1, len(text)), width // 2):
        hit = q_tok & content_tokens(text[i:i + width])
        if len(hit) >= min(2, len(q_tok)) and len(hit) / len(q_tok) >= 0.5:
            scored.append((len(hit) / len(q_tok), i))
    out, used = [], []
    for _, i in sorted(scored, key=lambda x: -x[0]):
        if all(abs(i - j) >= width for j in used):
            used.append(i)
            w = text[i:i + width]
            if i > 0 and " " in w[:30]:
                w = w.split(" ", 1)[1]                      # start on a word boundary
            if i + width < len(text) and " " in w:
                w = w.rsplit(" ", 1)[0]                     # end on a word boundary
            out.append(w.strip())
        if len(out) >= k:
            break
    return out


def web_evidence(question: str, ask) -> dict | None:
    """Same shape as crag_corrector.corrective_web_search, but with quoted passages from the real pages."""
    q = _search_query(question, ask)
    q_tok = content_tokens(q) - _GENERIC
    if len(q_tok) < 2:
        return None
    found: dict[str, dict] = {}
    for variant in (f"{q} {_OFFICIAL_SITES}", f"{q} {_SECONDARY_SITES}"):
        for r in _search(variant):
            u, c = r.get("href", ""), source_class(r.get("href", ""))
            if c and u not in found and is_legally_relevant_content(r.get("title", ""), r.get("body", "")):
                found[u] = {**r, "_c": c}
        if any(v["_c"] == "official" for v in found.values()):
            break                                           # official evidence found: do not widen
    pages = sorted(found.values(), key=lambda r: r["_c"] != "official")[:MAX_PAGES]
    if not pages:
        return None
    with ThreadPoolExecutor(len(pages)) as ex:
        texts = list(ex.map(lambda r: _fetch(r["href"]), pages))
    links, parts = [], []
    for r, t in zip(pages, texts):
        # page unreachable -> fall back to the search-engine snippet of that page (still the page's own text)
        ps = _passages(t, q_tok) or (_passages(r.get("body", ""), q_tok, 1) if not t else [])
        if ps:
            org = source_organization(r["href"])
            links.append({"title": r.get("title") or "Legal source", "url": r["href"], "source_class": r["_c"],
                          "organization": org, "quote": ps[0]})
            parts += [f"[{_LABEL[r['_c']]}: {org}] {r.get('title', '')}\n{p}" for p in ps]
    if not links:
        return None
    return {"case_name": links[0]["title"], "display_name": links[0]["title"], "full_text": "\n\n".join(parts),
            "source_type": "external_crag", "jurisdiction_type": "unknown", "source_links": links,
            "has_official_source": any(l["source_class"] == "official" for l in links),
            "retrieved_on": date.today().isoformat()}