
"""

Vector Store — Supabase pgvector wrapper for judgments, statutes, and

per-document page chunks.

"""

from supabase import create_client

import os

from dotenv import load_dotenv



load_dotenv()





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

    combined = judgments + statutes

    combined.sort(key=lambda x: x["score"], reverse=True)

    return combined[:match_count]





# ---------------- Document chunks (single-document-per-conversation) ----------------

def insert_document_chunks_batch(case_id: str, pages: list[tuple[int, str]], embeddings: list[list[float]]):

    client = get_supabase_client()

    rows = [{"case_id": case_id, "page_number": p, "chunk_text": t, "embedding": e}

            for (p, t), e in zip(pages, embeddings)]

    return client.table("document_chunks").insert(rows).execute()





def search_document_chunks(query_embedding: list[float], case_id: str, match_count: int = 5):

    client = get_supabase_client()

    result = client.rpc("match_document_chunks", {

        "query_embedding": query_embedding, "target_case_id": case_id, "match_count": match_count,

    }).execute()

    return result.data

