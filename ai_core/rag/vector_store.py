"""
Vector Store — bulk operations for speed, multi-document search, and case-status
helpers for background-processing + cancellation flow.
"""
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()


def get_supabase_client():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


# ---------------- Judgments (knowledge-base) ----------------
def insert_judgment(case_name, court, year, jurisdiction_type, full_text, embedding):
    client = get_supabase_client()
    return client.table("judgments").insert({
        "case_name": case_name,
        "court": court,
        "year": year,
        "jurisdiction_type": jurisdiction_type,
        "full_text": full_text,
        "embedding": embedding,
    }).execute()


def similarity_search(query_embedding: list[float], match_count: int = 5):
    client = get_supabase_client()
    return client.rpc("match_judgments", {"query_embedding": query_embedding, "match_count": match_count}).execute().data


def hybrid_search_judgments(query_embedding, query_text, match_count=5):
    client = get_supabase_client()
    return client.rpc("hybrid_search_judgments", {
        "query_embedding": query_embedding,
        "query_text": query_text,
        "match_count": match_count,
    }).execute().data


# ---------------- Statutes (knowledge-base) ----------------
def insert_statute(act_name, section_number, section_title, full_text, embedding):
    client = get_supabase_client()
    return client.table("statutes").insert({
        "act_name": act_name,
        "section_number": section_number,
        "section_title": section_title,
        "full_text": full_text,
        "embedding": embedding,
    }).execute()


def hybrid_search_statutes(query_embedding, query_text, match_count=5):
    client = get_supabase_client()
    return client.rpc("hybrid_search_statutes", {
        "query_embedding": query_embedding,
        "query_text": query_text,
        "match_count": match_count,
    }).execute().data


def search_knowledge_base(query_embedding, query_text, match_count=5):
    judgments = hybrid_search_judgments(query_embedding, query_text, match_count)
    statutes = hybrid_search_statutes(query_embedding, query_text, match_count)
    for j in judgments:
        j["source_type"] = "judgment"
        j["display_name"] = j["case_name"]
        j["score"] = j.get("combined_score", 0)
    for s in statutes:
        s["source_type"] = "statute"
        s["display_name"] = f"{s['act_name']} — Section {s['section_number']}"
        s["score"] = s.get("combined_score", 0)
    combined = (judgments or []) + (statutes or [])
    combined.sort(key=lambda x: x.get("score", 0), reverse=True)
    return combined[:match_count]


# ---------------- Document chunks (bulk + multi-doc) ----------------
def insert_document_chunk(case_id: str, page_number: int, chunk_text: str, embedding: list[float]):
    """Single-chunk insert (backward compatible)."""
    client = get_supabase_client()
    return client.table("document_chunks").insert({
        "case_id": case_id,
        "page_number": page_number,
        "chunk_text": chunk_text,
        "embedding": embedding,
    }).execute()


def insert_document_chunks_batch(case_id: str, pages: list[tuple[int, str]], embeddings: list[list[float]]):
    """Bulk-inserts multiple document chunks in a single Supabase request."""
    if not pages or not embeddings:
        return None
    client = get_supabase_client()
    rows = [
        {"case_id": case_id, "page_number": p, "chunk_text": t, "embedding": e}
        for (p, t), e in zip(pages, embeddings)
    ]
    return client.table("document_chunks").insert(rows).execute()


def search_document_chunks(query_embedding: list[float], case_id: str, match_count: int = 5):
    """Single document search."""
    return search_document_chunks_multi(query_embedding, [case_id], match_count)


def search_document_chunks_multi(query_embedding: list[float], case_ids: list[str], match_count: int = 5):
    """Searches across MULTIPLE attached documents at once; each result carries its own case_id and filename."""
    if not case_ids:
        return []
    client = get_supabase_client()
    results = client.rpc("match_document_chunks_multi", {
        "query_embedding": query_embedding,
        "target_case_ids": case_ids,
        "match_count": match_count,
    }).execute().data

    if results:
        case_rows = client.table("cases").select("id, filename").in_("id", case_ids).execute().data
        filename_map = {r["id"]: r.get("filename", "document") for r in (case_rows or [])}
        for r in results:
            r["filename"] = filename_map.get(r.get("case_id"), "document")
    return results or []


# ---------------- Case status (background-processing support) ----------------
def get_case_status(case_id: str) -> str:
    client = get_supabase_client()
    result = client.table("cases").select("status").eq("id", case_id).execute()
    return result.data[0]["status"] if result.data else "failed"


def set_case_status(case_id: str, status: str):
    client = get_supabase_client()
    client.table("cases").update({"status": status}).eq("id", case_id).execute()