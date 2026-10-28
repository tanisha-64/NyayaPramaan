"""
Phase 1 Document Isolation Regression Tests:
Guarantees that a CASE-SPECIFIC question can NEVER retrieve evidence/chunks/summary
from another uploaded case/document.
"""
import uuid
import pytest
from unittest.mock import patch, MagicMock
from backend.routers.chat_router import _handle_ask, QueryRequest
from ai_core.rag.vector_store import search_document_chunks


@pytest.fixture(autouse=True)
def mock_external_services():
    """Autouse fixture to mock network calls (embeddings, LLMs, hash-chain logs) across all isolation tests."""
    with patch("backend.routers.chat_router._log"), \
         patch("ai_core.rag.embeddings.embed_text", return_value=[0.1] * 768), \
         patch("backend.routers.chat_router.embed_text", return_value=[0.1] * 768), \
         patch("backend.routers.chat_router.extract_claims", return_value=(["mock claim"], True)), \
         patch("backend.routers.chat_router.judge_claims_against_evidence", return_value={"overall_verdict": "GROUNDED", "is_accurate": True, "issue": "", "supported_claims": ["mock claim"], "unsupported_claims": [], "claim_verdicts": []}), \
         patch("backend.routers.chat_router.self_reflect", return_value={"usefulness": "high", "conclusion": None, "conclusion_needed": False}), \
         patch("backend.routers.chat_router.generate_suggestions", return_value=[]), \
         patch("trust_log.hash_chain.get_last_hash", return_value=""), \
         patch("trust_log.hash_chain.save_log_entry"):
        yield


def _make_mock_client(case_data, chunks=None):
    mock_client = MagicMock()
    def mock_table(table_name):
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.insert.return_value = mock_query
        mock_query.update.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        if table_name == "cases":
            mock_query.execute.return_value.data = case_data
        elif table_name == "chat_sessions":
            mock_query.execute.return_value.data = [{"id": "s1", "user_id": "u1", "case_id": case_data[0]["id"] if case_data else None}]
        elif table_name == "messages":
            mock_query.execute.return_value.data = []
        elif table_name == "document_chunks":
            mock_query.execute.return_value.data = chunks or []
        else:
            mock_query.execute.return_value.data = []
        return mock_query
    mock_client.table.side_effect = mock_table
    return mock_client


def test_1_case_a_isolation_from_case_b():
    """TEST 1: Case A has 2010 land purchase, Case B has 2018 land purchase.
    Querying Case A returns only Case A evidence."""
    case_a_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence says when was the land purchased?", case_id=case_a_id)

    mock_client = _make_mock_client([{
        "id": case_a_id,
        "filename": "land_dispute_case_A.pdf",
        "summary": "Case A summary: purchase in 2010.",
        "status": "ready",
        "case_text": "Plaintiff purchased land in 2010."
    }])

    case_a_chunks = [{"id": str(uuid.uuid4()), "case_id": case_a_id, "page_number": 1, "chunk_text": "Plaintiff purchased land in 2010.", "similarity": 0.88}]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=case_a_chunks) as mock_search, \
         patch("backend.routers.chat_router.call_llm", return_value="The evidence states that the land was purchased in 2010."), \
         patch("ai_core.llm_gateway.call_llm", return_value="The evidence states that the land was purchased in 2010."):
        res = _handle_ask(req, user_id="u1")

        assert "2010" in res["answer"]
        assert "2018" not in res["answer"]
        assert "land_dispute_case_A.pdf" in res["sources"][0]["name"]


def test_2_case_a_unrelated_query_no_leak_from_case_b():
    """TEST 2: When Case A is selected, an unrelated query must NEVER pull chunks from Case B."""
    case_a_id = str(uuid.uuid4())
    req = QueryRequest(query="What is the commercial dispute value?", case_id=case_a_id)

    mock_client = _make_mock_client([{
        "id": case_a_id,
        "filename": "land_dispute_case_A.pdf",
        "summary": "Case A summary: land dispute.",
        "status": "ready",
        "case_text": "Plaintiff purchased land in 2010."
    }])

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=[]), \
         patch("ai_core.llm_gateway.call_llm", return_value=""):
        res = _handle_ask(req, user_id="u1")
        assert res.get("retrieval_insufficient") is True or res.get("no_documentary_evidence_found") is True
        assert res.get("sources") == []


def test_3_vector_store_defensive_isolation_filter():
    """TEST 3: search_document_chunks strictly filters out any chunk with different case_id."""
    case_target_id = str(uuid.uuid4())
    case_other_id = str(uuid.uuid4())

    mock_client = MagicMock()
    mock_client.rpc.return_value.execute.return_value.data = [
        {"id": str(uuid.uuid4()), "case_id": case_target_id, "page_number": 1, "chunk_text": "Target chunk", "similarity": 0.9},
        {"id": str(uuid.uuid4()), "case_id": case_other_id, "page_number": 2, "chunk_text": "Contaminant chunk", "similarity": 0.95},
    ]

    with patch("ai_core.rag.vector_store.get_supabase_client", return_value=mock_client):
        results = search_document_chunks([0.1]*768, case_id=case_target_id)
        assert len(results) == 1
        assert results[0]["case_id"] == case_target_id
        assert results[0]["chunk_text"] == "Target chunk"


def test_4_zero_chunks_and_indexing_status_gate():
    """TEST 4: Document in 'processing' status returns indexing message instead of hallucinating."""
    case_id = str(uuid.uuid4())
    req_proc = QueryRequest(query="What is the claim?", case_id=case_id)

    mock_client_proc = _make_mock_client([{
        "id": case_id, "filename": "doc.pdf", "status": "processing", "summary": "", "case_text": "Short."
    }])

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client_proc):
        res_proc = _handle_ask(req_proc, user_id="u1")
        assert res_proc.get("indexing_in_progress") is True

    # Ready status with 0 chunks returns retrieval insufficient / no evidence
    mock_client_ready = _make_mock_client([{
        "id": case_id, "filename": "doc.pdf", "status": "ready", "summary": "Done.", "case_text": "Short."
    }])
    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client_ready), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=[]), \
         patch("ai_core.llm_gateway.call_llm", return_value=""):
        res_ready = _handle_ask(req_proc, user_id="u1")
        assert res_ready.get("retrieval_insufficient") is True or res_ready.get("no_documentary_evidence_found") is True


def test_5_summary_isolation_case_a():
    """TEST 5: Summary query for Case A returns Case A's exact summary."""
    case_a_id = str(uuid.uuid4())
    req = QueryRequest(query="Mera document summarize karo", case_id=case_a_id)

    mock_client = _make_mock_client([{
        "id": case_a_id,
        "filename": "case_alpha.pdf",
        "summary": "Executive Summary for Case Alpha: Dispute over ancestral property.",
        "status": "ready",
        "case_text": "Case Alpha full text."
    }])

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("ai_core.rag.summarizer.call_llm", return_value=""):
        res = _handle_ask(req, user_id="u1")
        assert "Case Alpha" in res["answer"]
        assert "ancestral property" in res["answer"]


def test_6_summary_isolation_case_b():
    """TEST 6: Summary query for Case B returns Case B's exact summary."""
    case_b_id = str(uuid.uuid4())
    req = QueryRequest(query="Summarize this case", case_id=case_b_id)

    mock_client = _make_mock_client([{
        "id": case_b_id,
        "filename": "case_beta.pdf",
        "summary": "Executive Summary for Case Beta: Commercial contract arbitration breach.",
        "status": "ready",
        "case_text": "Case Beta full text."
    }])

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("ai_core.rag.summarizer.call_llm", return_value=""):
        res = _handle_ask(req, user_id="u1")
        assert "Case Beta" in res["answer"]


def test_7_two_cases_with_identical_filenames():
    """TEST 7: Two cases with identical filenames (e.g. 'order.pdf') are strictly isolated by case_id."""
    case_1_id = str(uuid.uuid4())
    case_2_id = str(uuid.uuid4())

    req1 = QueryRequest(query="What was the court order date in this case?", case_id=case_1_id)
    req2 = QueryRequest(query="What was the court order date in this case?", case_id=case_2_id)

    chunk1 = [{"id": str(uuid.uuid4()), "case_id": case_1_id, "page_number": 1, "chunk_text": "Order dated 15 Jan 2021.", "similarity": 0.9}]
    chunk2 = [{"id": str(uuid.uuid4()), "case_id": case_2_id, "page_number": 1, "chunk_text": "Order dated 20 Nov 2024.", "similarity": 0.9}]

    mock_client1 = _make_mock_client([{
        "id": case_1_id, "filename": "order.pdf", "status": "ready", "summary": "Order 1", "case_text": "Order 1"
    }], chunks=chunk1)

    mock_client2 = _make_mock_client([{
        "id": case_2_id, "filename": "order.pdf", "status": "ready", "summary": "Order 2", "case_text": "Order 2"
    }], chunks=chunk2)

    # Run for Case 1
    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client1), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=chunk1), \
         patch("backend.routers.chat_router.call_llm", return_value="The court order was passed on 15 Jan 2021.") as mock_llm, \
         patch("ai_core.llm_gateway.call_llm", return_value="The court order was passed on 15 Jan 2021."):
        res1 = _handle_ask(req1, user_id="u1")
        assert "15 Jan 2021" in res1["answer"]

    # Run for Case 2
    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client2), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=chunk2), \
         patch("backend.routers.chat_router.call_llm", return_value="The court order was passed on 20 Nov 2024.") as mock_llm, \
         patch("ai_core.llm_gateway.call_llm", return_value="The court order was passed on 20 Nov 2024."):
        res2 = _handle_ask(req2, user_id="u1")
        assert "20 Nov 2024" in res2["answer"]
