"""News Router — Google-News-RSS-based, cached per day, multiple articles."""
from fastapi import APIRouter
from datetime import date
from ai_core.evaluation.news_fetcher import fetch_legal_news
from ai_core.rag.vector_store import get_supabase_client

router = APIRouter()


@router.get("/legal")
def get_legal_news():
    client = get_supabase_client()
    today = str(date.today())

    try:
        cached = client.table("daily_news").select("articles").eq("news_date", today).eq("location", "india").execute()
        if cached.data and cached.data[0].get("articles"):
            articles = cached.data[0]["articles"]
            if articles and not all(a.get("title") == "Google News" for a in articles):
                return {"articles": articles}
    except Exception as e:
        print(f"[news_router] Cache lookup notice: {e}")

    articles, used_fallback = fetch_legal_news()

    # Only cache genuine RSS results — never lock in the static fallback
    # list as "today's news" for the rest of the day.
    if articles and not used_fallback:
        try:
            client.table("daily_news").upsert({"news_date": today, "location": "india", "articles": articles}).execute()
        except Exception as e:
            print(f"[news_router] Cache save notice: {e}")

    return {"articles": articles}