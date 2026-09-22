"""
Admin Router (synopsis Section 4.1 -- Client layer, Admin console).
Read-only metrics: cost, safety-violations, citation-accuracy trend --
the "Control Tower Dashboard" described in the synopsis.
"""
from fastapi import APIRouter, Depends
from ai_core.rag.vector_store import get_supabase_client
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