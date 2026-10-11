"""Daily Quiz Router — retries generation if it comes back empty."""
from fastapi import APIRouter, Depends
from backend.rate_limit import limit_ip
from datetime import date
from ai_core.evaluation.quiz_generator import generate_daily_quiz
from ai_core.rag.vector_store import get_supabase_client

router = APIRouter()


@router.get("/today", dependencies=[Depends(limit_ip("public"))])
def get_todays_quiz():
    client = get_supabase_client()
    today = str(date.today())

    try:
        existing = client.table("daily_quiz").select("*").eq("quiz_date", today).execute()
        if existing.data and existing.data[0].get("questions"):
            return existing.data[0]["questions"]
    except Exception as e:
        print(f"[quiz_router] Cache lookup notice: {e}")

    questions = generate_daily_quiz()
    if questions:
        try:
            client.table("daily_quiz").upsert({"quiz_date": today, "questions": questions}).execute()
        except Exception as e:
            print(f"[quiz_router] Cache save notice: {e}")

    return questions