
"""
CRAG Module — filtered web-search fallback for authoritative Indian legal sources only.
Strictly allowlists primary/secondary legal portals and rejects dictionary/untrusted sites.
"""
from urllib.parse import urlparse
from ddgs import DDGS

CONFIDENCE_THRESHOLD = 0.55

LEGAL_DOMAIN_ALLOWLIST = [
    "indiacode.nic.in",
    "sci.gov.in",
    "main.sci.gov.in",
    "judgments.ecourts.gov.in",
    "ecourts.gov.in",
    "delhihighcourt.nic.in",
    "bombayhighcourt.nic.in",
    "calcuttahighcourt.gov.in",
    "hckcs.gov.in",
    "livelaw.in",
    "barandbench.com",
    "indiankanoon.org",
    "casemine.com",
    "nalsa.gov.in",
    "lawmin.gov.in",
    "mha.gov.in",
]

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


def is_retrieval_sufficient(matches: list[dict]) -> bool:
    if not matches:
        return False
    best_score = matches[0].get("combined_score") or matches[0].get("similarity") or 0
    return best_score >= CONFIDENCE_THRESHOLD


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


def is_allowed_legal_url(url: str) -> bool:
    if not url:
        return False
    try:
        domain = urlparse(url).netloc.lower()
        if any(bad in domain for bad in DISALLOWED_DOMAINS):
            return False
        return any(allowed in domain for allowed in LEGAL_DOMAIN_ALLOWLIST)
    except Exception:
        return False


def is_legally_relevant_content(title: str, body: str) -> bool:
    text = f"{title} {body}".lower()
    if any(topic in text for topic in NON_LEGAL_TOPICS):
        return False
    return any(kw in text for kw in LEGAL_KEYWORDS)


def corrective_web_search(query: str) -> dict | None:
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(f"{query} site:indiacode.nic.in OR site:indiankanoon.org OR site:sci.gov.in OR site:livelaw.in OR site:barandbench.com", max_results=5))

        if not raw_results:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(f"{query} Indian law statute judgment", max_results=5))

        # Filter strictly for authoritative legal domains AND legally relevant content
        results = [
            r for r in raw_results
            if is_allowed_legal_url(r.get("href", "")) and is_legally_relevant_content(r.get("title", ""), r.get("body", ""))
        ]

        if not results:
            return None

        combined_text = "\n\n".join(f"{r.get('title', '')}: {r.get('body', '')}" for r in results[:3])
        source_list = [{"title": r.get("title", "Authoritative Legal Source"), "url": r.get("href", "")} for r in results[:3]]
        primary = source_list[0]
        display = f"{primary['title']} ({primary['url']})" if primary["url"] else primary["title"]

        return {
            "case_name": display,
            "display_name": display,
            "full_text": combined_text,
            "source_type": "external_crag",
            "jurisdiction_type": "unknown",
            "source_links": source_list,
        }
    except Exception:
        return None



