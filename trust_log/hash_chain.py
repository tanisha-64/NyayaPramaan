
"""Tamper-evident hash-chain audit log."""

import hashlib

import json

import time

from ai_core.rag.vector_store import get_supabase_client





def compute_entry_hash(event: dict, previous_hash: str) -> str:

    payload = json.dumps(event, sort_keys=True) + previous_hash

    return hashlib.sha256(payload.encode()).hexdigest()





def build_log_entry(event: dict, previous_hash: str = "") -> dict:

    entry_hash = compute_entry_hash(event, previous_hash)

    return {"timestamp": time.time(), "event": event, "previous_hash": previous_hash, "entry_hash": entry_hash}





def get_last_hash() -> str:

    client = get_supabase_client()

    result = client.table("query_log").select("entry_hash").order("created_at", desc=True).limit(1).execute()

    return result.data[0]["entry_hash"] if result.data else ""





def save_log_entry(log_entry: dict, query: str, response: str, verified: bool, model_used: str = None, user_id: str = None):

    client = get_supabase_client()

    row = {
        "query": query, "response": response, "verified": verified, "model_used": model_used,
        "previous_hash": log_entry["previous_hash"], "entry_hash": log_entry["entry_hash"],
    }

    if user_id:
        # user_id is stored beside (not inside) the hashed event, so existing chain verification is unchanged.
        # The column comes from sql/proposed/003_query_log_user.sql; without it, fall back to the old row shape.
        try:
            client.table("query_log").insert({**row, "user_id": user_id}).execute()
            return
        except Exception:
            pass

    client.table("query_log").insert(row).execute()
