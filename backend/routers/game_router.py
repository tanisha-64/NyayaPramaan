"""Rights-Rakshak Game Router — scenario-based legal-rights learning game."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import random
from ai_core.evaluation.rights_game_generator import generate_scenario, CATEGORIES
from ai_core.rag.vector_store import get_supabase_client
from backend.auth.supabase_auth import get_optional_user

router = APIRouter()


@router.get("/scenario")
def get_scenario():
    client = get_supabase_client()
    category = random.choice(CATEGORIES)

    try:
        existing = client.table("rights_scenarios").select("*").eq("category", category).order("created_at", desc=True).limit(5).execute()
        if existing.data and random.random() < 0.5:
            return random.choice(existing.data)
    except Exception as e:
        print(f"[game_router] Supabase query notice: {e}")

    scenario = generate_scenario(category)
    if not scenario:
        # Fallback scenario
        from ai_core.evaluation.rights_game_generator import CURATED_SCENARIOS, _shuffle_scenario
        return _shuffle_scenario(random.choice(CURATED_SCENARIOS))

    try:
        result = client.table("rights_scenarios").insert(scenario).execute()
        if result.data:
            return result.data[0]
    except Exception as e:
        print(f"[game_router] Supabase insert notice: {e}")

    return scenario


class AnswerSubmit(BaseModel):
    points: int


@router.post("/answer")
def submit_answer(body: AnswerSubmit, user=Depends(get_optional_user)):
    if not user:
        return {"total_points": body.points, "scenarios_completed": 1}

    client = get_supabase_client()
    try:
        existing = client.table("user_game_progress").select("*").eq("user_id", user.id).execute()

        if existing.data:
            progress = existing.data[0]
            new_points = progress["total_points"] + body.points
            new_count = progress["scenarios_completed"] + 1
            client.table("user_game_progress").update({
                "total_points": new_points, "scenarios_completed": new_count,
            }).eq("user_id", user.id).execute()
        else:
            new_points, new_count = body.points, 1
            client.table("user_game_progress").insert({
                "user_id": user.id, "total_points": new_points, "scenarios_completed": new_count,
            }).execute()

        return {"total_points": new_points, "scenarios_completed": new_count}
    except Exception as e:
        print(f"[game_router] submit_answer error: {e}")
        return {"total_points": body.points, "scenarios_completed": 1}


@router.get("/progress")
def get_progress(user=Depends(get_optional_user)):
    if not user:
        return {"total_points": 0, "scenarios_completed": 0}

    client = get_supabase_client()
    try:
        result = client.table("user_game_progress").select("*").eq("user_id", user.id).execute()
        return result.data[0] if result.data else {"total_points": 0, "scenarios_completed": 0}
    except Exception as e:
        print(f"[game_router] get_progress error: {e}")
        return {"total_points": 0, "scenarios_completed": 0}