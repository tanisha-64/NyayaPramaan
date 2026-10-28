"""
Admin Router (synopsis Section 4.1 -- Client layer, Admin console).
Read-only metrics: cost, safety-violations, citation-accuracy trend --
the "Control Tower Dashboard" described in the synopsis.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from ai_core.rag.vector_store import get_supabase_client
from ai_core.llm_gateway import call_llm, is_llm_failure
from ai_core.router.adaptive_router import choose_model
from backend.auth.supabase_auth import get_current_user, require_role

router = APIRouter()


@router.get("/metrics")
def get_metrics(user=Depends(get_current_user)):
    require_role(user, allowed_roles=["admin"])

    client = get_supabase_client()
    logs = client.table("query_log").select("verified, model_used").execute().data

    total = len(logs)
    verified_count = sum(1 for l in logs if l["verified"])
    model_usage = {}
    for l in logs:
        m = l.get("model_used", "unknown")
        model_usage[m] = model_usage.get(m, 0) + 1

    return {
        "total_queries": total,
        "verified_count": verified_count,
        "citation_accuracy_rate": round(verified_count / total, 3) if total else None,
        "model_usage_breakdown": model_usage,
    }


@router.get("/judgments-count")
def judgments_count(user=Depends(get_current_user)):
    require_role(user, allowed_roles=["admin"])
    client = get_supabase_client()
    result = client.table("judgments").select("id", count="exact").execute()
    return {"total_judgments": result.count}


@router.get("/activity")
def get_activity(user=Depends(get_current_user)):
    """Real user-activity counts -- no heuristics, no made-up numbers."""
    require_role(user, allowed_roles=["admin"])
    client = get_supabase_client()

    total_registered_users = None
    try:
        total_registered_users = len(client.auth.admin.list_users())
    except Exception:  # noqa: BLE001
        total_registered_users = None

    active_users_today = None
    try:
        today_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")
        rows = client.table("chat_sessions").select("user_id").gte("updated_at", today_start).execute().data
        active_users_today = len({r["user_id"] for r in rows if r.get("user_id")})
    except Exception:  # noqa: BLE001
        active_users_today = None

    return {"total_registered_users": total_registered_users, "active_users_today": active_users_today}


@router.get("/health")
def get_health(user=Depends(get_current_user)):
    """Actually pings the DB and the LLM gateway, and derives TrustAgent accuracy
    from real recent query_log rows -- no hardcoded 'Active/Operational'."""
    require_role(user, allowed_roles=["admin"])
    client = get_supabase_client()
    checks = []

    def add(name, ok, status):
        checks.append({"name": name, "ok": ok, "status": status})

    try:
        client.table("chat_sessions").select("id").limit(1).execute()
        add("Database (Supabase)", True, "Operational")
    except Exception as e:  # noqa: BLE001
        add("Database (Supabase)", False, f"Down: {type(e).__name__}")

    try:
        client.table("judgments").select("id").limit(1).execute()
        add("Indexed Judgments Store", True, "Operational")
    except Exception as e:  # noqa: BLE001
        add("Indexed Judgments Store", False, f"Down: {type(e).__name__}")

    try:
        model = choose_model("ping")
        out = call_llm(model, "Reply with OK.")
        if is_llm_failure(out):
            add("LLM Gateway (Multi-Model Routing)", False, "Model call failed")
        else:
            add("LLM Gateway (Multi-Model Routing)", True, f"Operational ({model})")
    except Exception as e:  # noqa: BLE001
        add("LLM Gateway (Multi-Model Routing)", False, f"Down: {type(e).__name__}")

    try:
        recent = client.table("query_log").select("verified").limit(50).execute().data
        if recent:
            rate = sum(1 for r in recent if r.get("verified")) / len(recent)
            add("TrustAgent Citation Verification", rate >= 0.7, f"{round(rate * 100)}% verified (last {len(recent)})")
        else:
            add("TrustAgent Citation Verification", True, "No queries logged yet")
    except Exception as e:  # noqa: BLE001
        add("TrustAgent Citation Verification", False, f"Down: {type(e).__name__}")

    return {"checks": checks}