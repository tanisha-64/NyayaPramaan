
"""

CRAG Module — live web-search fallback (DuckDuckGo, free) when internal

retrieval has no confident match.

"""

from ddgs import DDGS



CONFIDENCE_THRESHOLD = 0.55





def is_retrieval_sufficient(matches: list[dict]) -> bool:

    if not matches:

        return False

    best_score = matches[0].get("combined_score") or matches[0].get("similarity") or 0

    return best_score >= CONFIDENCE_THRESHOLD





def corrective_web_search(query: str) -> dict | None:

    try:

        with DDGS() as ddgs:

            results = list(ddgs.text(f"{query} India law", max_results=3))

        if not results:

            return None

        combined_text = "\n\n".join(f"{r.get('title', '')}: {r.get('body', '')}" for r in results)

        source_list = [{"title": r.get("title", "Web source"), "url": r.get("href", "")} for r in results]

        primary = source_list[0]

        display = f"{primary['title']} ({primary['url']})" if primary["url"] else primary["title"]

        return {

            "case_name": display, "display_name": display, "full_text": combined_text,

            "source_type": "external_crag", "jurisdiction_type": "unknown", "source_links": source_list,

        }

    except Exception:

        return None

