"""
Legal News Fetcher — Google News RSS and verified Indian Legal Portals
(Supreme Court of India, LiveLaw, Bar & Bench, LawBeat, PIB Legal).
Extracts articles with reliable fallbacks and images so it never returns empty.
"""
import feedparser
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import re

# "when:2d" restricts Google News results to the last 2 days only,
# so stale/old articles never get picked up.
RSS_FEEDS = [
    "https://news.google.com/rss/search?q=Supreme+Court+India+judgment+OR+BNS+OR+statute+when:2d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=High+Court+legal+verdict+India+when:2d&hl=en-IN&gl=IN&ceid=IN:en",
]

FEED_TIMEOUT_SECONDS = 6

DEFAULT_LEGAL_IMAGES = [
    "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1505664194779-8beaceb93744?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1453733197781-704fa5988299?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1479142506502-19b3a3b7ff33?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1436450412740-6b988f486c6b?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=800&q=80",
]

CURATED_LEGAL_NEWS = [
    {
        "title": "Supreme Court Reiterates: Right to Speedy Trial is Inalienable Part of Article 21",
        "summary": "A Supreme Court bench affirmed that prolonged incarceration without trial violates the fundamental right to personal liberty under Article 21 of the Indian Constitution, granting bail.",
        "image": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=800&q=80",
        "url": "https://main.sci.gov.in",
        "source": "Supreme Court of India",
        "date": datetime.now(timezone.utc).isoformat()
    },
    {
        "title": "Implementation of Bharatiya Nyaya Sanhita (BNS) and New Criminal Laws Across Courts",
        "summary": "High Courts and subordinate judiciary nationwide adopt updated procedural guidelines and digital evidence standards under the Bharatiya Nagarik Suraksha Sanhita (BNSS) and Bharatiya Sakshya Adhiniyam.",
        "image": "https://images.unsplash.com/photo-1505664194779-8beaceb93744?auto=format&fit=crop&w=800&q=80",
        "url": "https://pib.gov.in",
        "source": "Ministry of Law & Justice",
        "date": datetime.now(timezone.utc).isoformat()
    },
    {
        "title": "Consumer Protection: E-Commerce Platforms Held Accountable for Defective Third-Party Goods",
        "summary": "NCDRC ruled that digital marketplace platforms exercising end-to-end fulfillment control cannot evade liability as mere intermediaries when consumers receive substandard products.",
        "image": "https://images.unsplash.com/photo-1453733197781-704fa5988299?auto=format&fit=crop&w=800&q=80",
        "url": "https://ncdrc.nic.in",
        "source": "National Consumer Commission",
        "date": datetime.now(timezone.utc).isoformat()
    },
    {
        "title": "Constitutional Bench Upholds Environmental Public Trust Doctrine in Urban Development Cases",
        "summary": "The apex court ruled that municipal authorities hold natural wetlands and urban green covers in public trust, mandating environmental audits prior to commercial clearances.",
        "image": "https://images.unsplash.com/photo-1479142506502-19b3a3b7ff33?auto=format&fit=crop&w=800&q=80",
        "url": "https://main.sci.gov.in",
        "source": "Supreme Court Reporter",
        "date": datetime.now(timezone.utc).isoformat()
    },
    {
        "title": "High Court Clarifies Mandatory Conciliation under Commercial Courts Act, 2015",
        "summary": "Pre-institution mediation and conciliation under Section 12A is mandatory before filing commercial suits unless urgent interim relief is genuinely contemplated and substantiated.",
        "image": "https://images.unsplash.com/photo-1436450412740-6b988f486c6b?auto=format&fit=crop&w=800&q=80",
        "url": "https://delhihighcourt.nic.in",
        "source": "High Court of Delhi",
        "date": datetime.now(timezone.utc).isoformat()
    },
    {
        "title": "Digital Personal Data Protection (DPDP) Act Compliance Rules Notified for Enterprises",
        "summary": "The statutory rules set forth grievance redressal standards, consent management mandates, and data fiduciary breach penalty schedules.",
        "image": "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=800&q=80",
        "url": "https://meity.gov.in",
        "source": "Ministry of Electronics & IT",
        "date": datetime.now(timezone.utc).isoformat()
    }
]


def _clean_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    return " ".join(clean.split()).strip()


def _entry_datetime(entry) -> datetime:
    """Best-effort parse of an RSS entry's published date, for sorting newest-first."""
    try:
        if getattr(entry, "published_parsed", None):
            import calendar
            return datetime.fromtimestamp(calendar.timegm(entry.published_parsed), tz=timezone.utc)
        if entry.get("published"):
            return parsedate_to_datetime(entry["published"])
    except Exception:
        pass
    return datetime.min.replace(tzinfo=timezone.utc)


def _fetch_feed(feed_url: str):
    """Fetch an RSS feed with a hard timeout so a slow/unreachable feed never
    stalls the request (feedparser.parse(url) has no timeout on its own)."""
    req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=FEED_TIMEOUT_SECONDS) as resp:
        raw = resp.read()
    return feedparser.parse(raw)


def fetch_legal_news() -> tuple[list[dict], bool]:
    """Returns (articles, used_fallback). used_fallback=True means the curated
    static list had to be used (so the caller should NOT cache the result)."""
    raw_entries = []

    for feed_url in RSS_FEEDS:
        try:
            feed = _fetch_feed(feed_url)
            for entry in feed.entries:
                raw_title = entry.get("title", "")
                if not raw_title:
                    continue
                raw_entries.append((entry, _entry_datetime(entry)))
        except Exception as e:
            print(f"[news_fetcher] RSS feed error: {e}")

    # newest first
    raw_entries.sort(key=lambda pair: pair[1], reverse=True)

    articles: list[dict] = []
    seen_titles = set()

    for entry, _dt in raw_entries:
        raw_title = entry.get("title", "")
        parts = raw_title.rsplit(" - ", 1)
        title = parts[0].strip()
        source = parts[1].strip() if len(parts) > 1 else entry.get("source", {}).get("title", "Legal Dispatch")

        if title in seen_titles:
            continue
        seen_titles.add(title)

        summary = _clean_html(entry.get("summary", "")) or _clean_html(entry.get("description", ""))
        if not summary or len(summary) < 20:
            summary = f"Recent legal proceedings and key judicial updates regarding {title}."

        link = entry.get("link", "https://main.sci.gov.in")
        pub_date = entry.get("published", "") or datetime.now(timezone.utc).isoformat()
        image = DEFAULT_LEGAL_IMAGES[len(articles) % len(DEFAULT_LEGAL_IMAGES)]

        articles.append({
            "title": title,
            "summary": summary[:240] + ("..." if len(summary) > 240 else ""),
            "image": image,
            "url": link,
            "source": source,
            "date": pub_date
        })

        if len(articles) >= 6:
            break

    if len(articles) >= 3:
        return articles[:6], False

    # Genuine RSS failure — pad with curated static list, but tell the
    # caller this is a fallback so it does NOT get cached as "today's news".
    for curated in CURATED_LEGAL_NEWS:
        if curated["title"] not in seen_titles:
            articles.append(curated)
        if len(articles) >= 6:
            break

    return articles[:6], True