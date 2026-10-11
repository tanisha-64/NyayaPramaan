"""
CRAG Module — filtered web-search fallback for authoritative Indian legal sources only.

* Allowlist, not blocklist: a result is used only if its HOST is (a subdomain of) an allowed legal domain. Matching is
  on the parsed hostname, never a substring of the URL, so "indiacode.nic.in.evil.example" or a query-string trick
  cannot pass.
* Sources are classified: OFFICIAL (government legislation portals, courts, legal-aid authority) vs SECONDARY (law
  news / reporters / aggregators). Official sources are searched first and ranked first; secondary ones are used only
  when no official result was found, and are labelled as commentary rather than authority.
* Bounded corrective retrieval: at most 3 searches (official sites -> secondary sites -> generic filtered), stopping
  as soon as an official source was found. Each search has a timeout.
* The query is redacted of personal identifiers before it leaves the machine.
"""
from datetime import date
from urllib.parse import urlparse

from ddgs import DDGS

from ai_core.guardrails.output_guard import redact_pii

CONFIDENCE_THRESHOLD = 0.55
SEARCH_TIMEOUT_SECONDS = 10
MAX_SEARCHES = 3
MAX_RESULTS_PER_SEARCH = 5

OFFICIAL_DOMAINS = {
    "indiacode.nic.in": "India Code (Government of India)",
    "legislative.gov.in": "Legislative Department, Government of India",
    "egazette.gov.in": "The Gazette of India",
    "sci.gov.in": "Supreme Court of India",
    "main.sci.gov.in": "Supreme Court of India",
    "judgments.ecourts.gov.in": "eCourts Judgments Portal",
    "ecourts.gov.in": "eCourts (Government of India)",
    "delhihighcourt.nic.in": "Delhi High Court",
    "bombayhighcourt.nic.in": "Bombay High Court",
    "calcuttahighcourt.gov.in": "Calcutta High Court",
    "allahabadhighcourt.in": "Allahabad High Court",
    "hckcs.gov.in": "High Court of Karnataka",
    "nalsa.gov.in": "National Legal Services Authority",
    "lawmin.gov.in": "Ministry of Law and Justice",
    "doj.gov.in": "Department of Justice, Government of India",
    "mha.gov.in": "Ministry of Home Affairs",
}
SECONDARY_DOMAINS = {
    "livelaw.in": "LiveLaw (legal news)",
    "barandbench.com": "Bar & Bench (legal news)",
    "indiankanoon.org": "Indian Kanoon (case-law aggregator)",
    "casemine.com": "CaseMine (case-law aggregator)",
}
LEGAL_DOMAIN_ALLOWLIST = list(OFFICIAL_DOMAINS) + list(SECONDARY_DOMAINS)

DISALLOWED_DOMAINS = [
    "wiktionary.org",
    "wikipedia.org",
    "quora.com",
    "reddit.com",
    "dictionary.com",
    "merriam-webster.com",
    "vocabulary.com",
    "thefreedictionary.com",
    "collinsdictionary.com",
    "cambridge.org",
]

LEGAL_KEYWORDS = [
    "law", "legal", "court", "act", "section", "judgment", "statute", "order", "justice",
    "tribunal", "petition", "appeal", "rights", "advocate", "jurisdiction", "bns", "ipc",
    "crpc", "bnss", "bsa", "constitution", "offence", "bail", "adverse possession", "property",
    "criminal", "civil", "high court", "supreme court", "article"
]

NON_LEGAL_TOPICS = [
    "bluetooth", "wi-fi", "driver", "printer", "troubleshoot", "windows update", "iphone",
    "android app", "gameplay", "recipe", "baking", "microsoft support", "firmware", "headset",
    "pairing", "audio device"
]


def is_retrieval_sufficient(matches: list[dict]) -> bool:
    if not matches:
        return False
    best_score = matches[0].get("combined_score") or matches[0].get("similarity") or 0
    return best_score >= CONFIDENCE_THRESHOLD


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().rstrip(".")
    except Exception:
        return ""


def _host_matches(host: str, domains) -> str | None:
    """The matching allowlist domain if host IS it or a subdomain of it ("www.indiacode.nic.in" yes, "evilindiacode.nic.in" no)."""
    for d in domains:
        if host == d or host.endswith("." + d):
            return d
    return None


def source_class(url: str) -> str | None:
    """'official' | 'secondary' | None (not allowed)."""
    host = _host(url)
    if not host or _host_matches(host, DISALLOWED_DOMAINS):
        return None
    if _host_matches(host, OFFICIAL_DOMAINS):
        return "official"
    if _host_matches(host, SECONDARY_DOMAINS):
        return "secondary"
    return None


def source_organization(url: str) -> str:
    host = _host(url)
    for table in (OFFICIAL_DOMAINS, SECONDARY_DOMAINS):
        d = _host_matches(host, table)
        if d:
            return table[d]
    return host or "unknown"


def is_allowed_legal_url(url: str) -> bool:
    return source_class(url) is not None


def is_legally_relevant_content(title: str, body: str) -> bool:
    text = f"{title} {body}".lower()
    if any(topic in text for topic in NON_LEGAL_TOPICS):
        return False
    return any(kw in text for kw in LEGAL_KEYWORDS)


_OFFICIAL_SITES = " OR ".join(f"site:{d}" for d in ("indiacode.nic.in", "sci.gov.in", "ecourts.gov.in", "nalsa.gov.in", "legislative.gov.in"))
_SECONDARY_SITES = " OR ".join(f"site:{d}" for d in SECONDARY_DOMAINS)


def _search(query: str) -> list[dict]:
    try:
        try:
            ddgs = DDGS(timeout=SEARCH_TIMEOUT_SECONDS)
        except TypeError:
            ddgs = DDGS()
        with ddgs as client:
            return list(client.text(query, max_results=MAX_RESULTS_PER_SEARCH))
    except Exception:
        return []


def corrective_web_search(query: str) -> dict | None:
    """Evidence from allowed legal sources, official first, or None when nothing allowed and relevant was found."""
    safe_query = redact_pii(query or "").strip()
    if not safe_query:
        return None
    try:
        variants = [f"{safe_query} {_OFFICIAL_SITES}", f"{safe_query} {_SECONDARY_SITES}", f"{safe_query} Indian law statute judgment"]
        kept: dict[str, dict] = {}
        for variant in variants[:MAX_SEARCHES]:
            for r in _search(variant):
                url = r.get("href", "")
                cls = source_class(url)
                if cls and url not in kept and is_legally_relevant_content(r.get("title", ""), r.get("body", "")):
                    kept[url] = {**r, "_class": cls}
            if any(v["_class"] == "official" for v in kept.values()):
                break                                    # authoritative evidence found: no need to widen
        if not kept:
            return None

        ranked = sorted(kept.values(), key=lambda r: r["_class"] != "official")[:3]
        has_official = ranked[0]["_class"] == "official"
        label = {"official": "Official source", "secondary": "Secondary commentary (not an authority)"}
        combined_text = "\n\n".join(
            f"[{label[r['_class']]}: {source_organization(r.get('href', ''))}] {r.get('title', '')}: {r.get('body', '')}" for r in ranked)
        source_list = [{"title": r.get("title", "Legal source"), "url": r.get("href", ""), "source_class": r["_class"],
                        "organization": source_organization(r.get("href", ""))} for r in ranked]
        primary = source_list[0]
        display = f"{primary['title']} ({primary['url']})" if primary["url"] else primary["title"]

        return {
            "case_name": display,
            "display_name": display,
            "full_text": combined_text,
            "source_type": "external_crag",
            "jurisdiction_type": "unknown",
            "source_links": source_list,
            "has_official_source": has_official,
            "retrieved_on": date.today().isoformat(),
        }
    except Exception:
        return None
