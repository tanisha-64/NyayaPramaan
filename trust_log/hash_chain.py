"""
Tamper-evident hash-chain audit log (synopsis Section 4.6).
Each verification event's hash includes the previous entry's hash.
"""
import hashlib
import json
import time

def compute_entry_hash(event: dict, previous_hash: str) -> str:
    payload = json.dumps(event, sort_keys=True) + previous_hash
    return hashlib.sha256(payload.encode()).hexdigest()

def build_log_entry(event: dict, previous_hash: str = "") -> dict:
    entry_hash = compute_entry_hash(event, previous_hash)
    return {
        "timestamp": time.time(),
        "event": event,
        "previous_hash": previous_hash,
        "entry_hash": entry_hash,
    }

from ai_core.rag.vector_store import get_supabase_client

def get_last_hash() -> str:
    """Fetches the most recent entry_hash from query_log, so the chain
    continues correctly even across server restarts."""
    client = get_supabase_client()
    result = client.table("query_log").select("entry_hash").order("created_at", desc=True).limit(1).execute()
    if result.data:
        return result.data[0]["entry_hash"]
    return ""

def save_log_entry(log_entry: dict, query: str, response: str, verified: bool, model_used: str = None):
    """Persists the hash-chain entry into Supabase's query_log table."""
    client = get_supabase_client()
    client.table("query_log").insert({
        "query": query,
        "response": response,
        "verified": verified,
        "model_used": model_used,
        "previous_hash": log_entry["previous_hash"],
        "entry_hash": log_entry["entry_hash"],
    }).execute()