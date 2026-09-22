from typing import Optional, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ai_core.rag.embeddings import embed_text
from ai_core.rag.vector_store import search_knowledge_base
from backend.auth.supabase_auth import get_current_user

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    match_count: int = 10
    court: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    jurisdiction_type: Optional[str] = None  # "binding", "persuasive", or None for all


@router.post("/precedents")
def search_precedents(request: SearchRequest, user=Depends(get_current_user)):
    query_vec = embed_text(request.query, task_type="RETRIEVAL_QUERY")
    # Retrieve candidates
    results = search_knowledge_base(query_vec, request.query, match_count=max(request.match_count * 2, 15))
    
    filtered = []
    for r in results:
        # Court filter
        if request.court and request.court.strip() and request.court != "all":
            r_court = (r.get("court") or "").lower()
            if request.court.lower() not in r_court:
                continue
                
        # Jurisdiction filter
        if request.jurisdiction_type and request.jurisdiction_type != "all":
            if r.get("jurisdiction_type") != request.jurisdiction_type:
                continue
                
        # Year filter
        year = r.get("year")
        if year is not None:
            if request.year_from and year < request.year_from:
                continue
            if request.year_to and year > request.year_to:
                continue
                
        filtered.append(r)
        if len(filtered) >= request.match_count:
            break
            
    return {"results": filtered}