"""
Vector Store — Supabase pgvector wrapper for judgments, statutes, and
per-document page chunks.
Multi-strategy retrieval with robust RPC fallbacks and direct-table similarity
to guarantee live document retrieval never fails.
"""
from supabase import create_client
import os
import uuid
import json
import re
from dotenv import load_dotenv

load_dotenv()


class PartialInsertError(RuntimeError):
    def __init__(self, message: str, inserted_ids: list[str]):
        super().__init__(message)
        self.inserted_ids = inserted_ids


def get_supabase_client():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


# ---------------- Judgments ----------------

def insert_judgment(case_name, court, year, jurisdiction_type, full_text, embedding):
    client = get_supabase_client()
    return client.table("judgments").insert({
        "case_name": case_name, "court": court, "year": year,
        "jurisdiction_type": jurisdiction_type, "full_text": full_text, "embedding": embedding,
    }).execute()


def hybrid_search_judgments(query_embedding, query_text, match_count=5):
    client = get_supabase_client()
    return client.rpc("hybrid_search_judgments", {
        "query_embedding": query_embedding, "query_text": query_text, "match_count": match_count,
    }).execute().data


def hybrid_search_statutes(query_embedding, query_text, match_count=5):
    client = get_supabase_client()
    return client.rpc("hybrid_search_statutes", {
        "query_embedding": query_embedding, "query_text": query_text, "match_count": match_count,
    }).execute().data


KNOWN_ACT_ALIASES = {
    "bns": ["bharatiya nyaya sanhita", "bns"],
    "bnss": ["bharatiya nagarik suraksha sanhita", "bnss"],
    "bsa": ["bharatiya sakshya adhiniyam", "bsa"],
    "ipc": ["indian penal code", "ipc"],
    "crpc": ["code of criminal procedure", "crpc"],
    "cpc": ["code of civil procedure", "cpc"],
    "it act": ["information technology act", "it act"],
    "limitation act": ["limitation act"],
    "constitution": ["constitution of india", "constitution"],
}


def search_knowledge_base(query_embedding, query_text, match_count=5):
    judgments = hybrid_search_judgments(query_embedding, query_text, match_count) or []
    statutes = hybrid_search_statutes(query_embedding, query_text, match_count) or []

    lowered_q = query_text.lower()
    
    target_act_patterns = None
    for alias_key, patterns in KNOWN_ACT_ALIASES.items():
        if alias_key in lowered_q or any(p in lowered_q for p in patterns):
            target_act_patterns = patterns
            break

    valid_statutes = []
    for s in statutes:
        act_name_low = s.get("act_name", "").lower()
        if target_act_patterns:
            if any(p in act_name_low for p in target_act_patterns):
                s["source_type"] = "statute"
                s["display_name"] = f"{s['act_name']} — Section {s['section_number']}"
                s["score"] = s.get("combined_score", 0)
                valid_statutes.append(s)
        else:
            s["source_type"] = "statute"
            s["display_name"] = f"{s['act_name']} — Section {s['section_number']}"
            s["score"] = s.get("combined_score", 0)
            valid_statutes.append(s)

    for j in judgments:
        j["source_type"] = "judgment"
        j["display_name"] = j.get("case_name", "Landmark Judgment")
        j["score"] = j.get("combined_score", 0)

    combined = judgments + valid_statutes
    combined.sort(key=lambda x: x["score"], reverse=True)
    return combined[:match_count]


# ---------------- Document chunks (single-document-per-conversation) ----------------

def insert_document_chunks_batch(case_id: str, pages: list[tuple[int, str]], embeddings: list[list[float]]):
    if len(pages) != len(embeddings):
        raise ValueError("Each document chunk must have exactly one embedding")

    client = get_supabase_client()
    rows = [{"case_id": case_id, "page_number": p, "chunk_text": t, "embedding": e}
            for (p, t), e in zip(pages, embeddings)]
    response = client.table("document_chunks").insert(rows).execute()
    inserted_rows = response.data or []
    inserted_ids = [row["id"] for row in inserted_rows if row.get("id")]
    if len(inserted_ids) != len(rows):
        raise PartialInsertError(
            f"Expected IDs for {len(rows)} inserted document chunks, received {len(inserted_ids)}",
            inserted_ids,
        )
    return inserted_ids


def count_document_chunks(case_id: str) -> int:
    response = (
        get_supabase_client()
        .table("document_chunks")
        .select("id", count="exact")
        .eq("case_id", case_id)
        .limit(1)
        .execute()
    )
    if isinstance(response.count, int):
        return response.count
    return len(response.data or [])


def list_document_chunk_ids(case_id: str) -> list[str]:
    client = get_supabase_client()
    chunk_ids = []
    page_size = 1000
    offset = 0
    while True:
        response = (
            client.table("document_chunks")
            .select("id")
            .eq("case_id", case_id)
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = response.data or []
        chunk_ids.extend(row["id"] for row in rows if row.get("id"))
        if len(rows) < page_size:
            return chunk_ids
        offset += page_size


def delete_document_chunks(chunk_ids: list[str]):
    if not chunk_ids:
        return None
    return get_supabase_client().table("document_chunks").delete().in_("id", chunk_ids).execute()


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search_document_chunks(query_embedding: list[float], case_id: str, match_count: int = 8, query_text: str = "") -> list[dict]:
    if not case_id:
        return []
    try:
        clean_case_id = str(uuid.UUID(str(case_id).strip()))
    except (ValueError, AttributeError, TypeError):
        return []

    client = get_supabase_client()
    raw_data = None
    rpc_used = None

    # Strategy 1: Single-document RPC match_document_chunks
    try:
        res1 = client.rpc("match_document_chunks", {
            "query_embedding": query_embedding,
            "target_case_id": clean_case_id,
            "match_count": match_count,
        }).execute()
        if res1.data:
            raw_data = res1.data
            rpc_used = "match_document_chunks"
    except Exception as e1:
        print(f"[vector_store] match_document_chunks RPC failed: {e1}")

    # Strategy 2: Multi-document RPC match_document_chunks_multi
    if raw_data is None:
        try:
            res2 = client.rpc("match_document_chunks_multi", {
                "query_embedding": query_embedding,
                "target_case_ids": [clean_case_id],
                "match_count": match_count,
            }).execute()
            if res2.data:
                raw_data = res2.data
                rpc_used = "match_document_chunks_multi"
        except Exception as e2:
            print(f"[vector_store] match_document_chunks_multi RPC failed: {e2}")

    # Strategy 3: Direct table fetch + local cosine similarity & hybrid ranking fallback
    if raw_data is None or len(raw_data) == 0:
        try:
            table_res = client.table("document_chunks").select("id, case_id, page_number, chunk_text, embedding").eq("case_id", clean_case_id).execute()
            rows = table_res.data or []
            if rows:
                scored_rows = []
                query_tokens = [w.lower() for w in re.findall(r'\w+', query_text)] if query_text else []
                # Remove common stopwords
                stop_words = {"what", "which", "where", "when", "does", "did", "the", "and", "for", "with", "this", "case", "file", "document", "hai", "hain", "kya", "me", "mein", "ne", "ko", "ke", "liye", "ka", "ki"}
                meaningful_tokens = [t for t in query_tokens if t not in stop_words and len(t) > 2]

                for r in rows:
                    emb = r.get("embedding")
                    if isinstance(emb, str):
                        try:
                            emb = json.loads(emb)
                        except Exception:
                            emb = []
                    cos_sim = _cosine_similarity(query_embedding, emb) if isinstance(emb, list) and emb else 0.0
                    
                    # Lexical keyword score
                    kw_score = 0.0
                    chunk_lower = (r.get("chunk_text") or "").lower()
                    if meaningful_tokens:
                        hits = sum(1 for tok in meaningful_tokens if tok in chunk_lower)
                        kw_score = hits / len(meaningful_tokens)

                    combined_score = 0.75 * cos_sim + 0.25 * kw_score if meaningful_tokens else cos_sim

                    scored_rows.append({
                        "id": r.get("id"),
                        "case_id": r.get("case_id"),
                        "page_number": r.get("page_number", 1),
                        "chunk_text": r.get("chunk_text", ""),
                        "similarity": cos_sim,
                        "score": combined_score,
                    })
                scored_rows.sort(key=lambda x: x.get("score", x["similarity"]), reverse=True)
                raw_data = scored_rows[:match_count]
                rpc_used = "direct_table_cosine_sim"
        except Exception as e3:
            print(f"[vector_store] Direct table fallback failed: {e3}")

    raw_data = raw_data or []

    # Strict defensive isolation check: guarantee chunks belong ONLY to the requested case_id
    isolated_chunks = [
        c for c in raw_data
        if str(c.get("case_id", "")).lower() == clean_case_id.lower()
    ]

    print(f"[VECTOR_SEARCH] case_id={clean_case_id} method={rpc_used} chunks_found={len(isolated_chunks)}")
    return isolated_chunks
