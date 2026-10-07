"""
Phase 2 — Case-Evidence Grounding & Hallucination Hard-Stop Regression Tests.
Guarantees that CASE_SPECIFIC questions answer ONLY from retrieved evidence,
never invent unstated facts/documents, and refuse when evidence is absent.
"""
import uuid
import pytest
from unittest.mock import patch, MagicMock
from backend.routers.chat_router import _handle_ask, QueryRequest


@pytest.fixture(autouse=True)
def mock_external_services():
    """Autouse fixture to mock network calls across all grounding tests."""
    with patch("backend.routers.chat_router._log"), \
         patch("ai_core.rag.embeddings.embed_text", return_value=[0.1] * 768), \
         patch("backend.routers.chat_router.embed_text", return_value=[0.1] * 768), \
         patch("trust_log.hash_chain.get_last_hash", return_value=""), \
         patch("trust_log.hash_chain.save_log_entry"):
        yield


def test_phase2_test1_plaintiff_title_no_fabricated_deeds():
    """TEST 1: Query plaintiff title. The document mentions oral partition, no registered sale deed.
    The prompt contract strictly prevents hallucinating sale deeds or tax receipts."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence supports the plaintiff's title?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "land_dispute_suit.pdf",
        "status": "ready",
        "summary": "Partition dispute.",
        "case_text": "Oral family settlement in 2015 regarding ancestral land."
    }]

    case_chunks = [{
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "page_number": 3,
        "chunk_text": "Plaintiff claims ownership based on an oral family settlement dated 12.04.2015 without registered conveyance.",
        "similarity": 0.85
    }]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=case_chunks), \
         patch("backend.routers.chat_router._verify_and_label", return_value=("supported", [{"verdict": "supported", "claim": "oral family settlement"}])), \
         patch("backend.routers.chat_router.call_llm") as mock_llm:
        mock_llm.return_value = "According to Page 3, the plaintiff claims title based on an oral family settlement dated 12.04.2015 [land_dispute_suit.pdf — Page 3]."
        res = _handle_ask(req, user_id="u1")

        # Verify prompt received the hard constraints
        all_prompts = " ".join(call[0][1] for call in mock_llm.call_args_list if len(call[0]) > 1)
        assert "STRICT CASE-SPECIFIC EVIDENCE CONTRACT" in all_prompts
        assert "STRICT NEGATIVE CONSTRAINT" in all_prompts
        assert "sale deeds" in all_prompts or "sale deed" in all_prompts

        assert "oral family settlement" in res["answer"]
        # Must not fabricate registered deeds
        assert "registered sale deed" not in res["answer"].lower()
        assert res["sources"][0]["name"] == "land_dispute_suit.pdf — Page 3"


def test_phase2_test2_cyber_harassment_refusal_on_land_document():
    """TEST 2: Query cyber harassment on a land document.
    Must return clear refusal and NOT use web/statutory search."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence proves cyber harassment?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "land_record.pdf",
        "status": "ready",
        "summary": "Land revenue records.",
        "case_text": "Agricultural plot survey numbers."
    }]

    # Chunks are unrelated (low similarity)
    unrelated_chunks = [{
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "page_number": 1,
        "chunk_text": "Survey No 45/2 agricultural land boundary.",
        "similarity": 0.08
    }]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=unrelated_chunks), \
         patch("backend.routers.chat_router.search_knowledge_base") as mock_kb:
        res = _handle_ask(req, user_id="u1")

        # Must not call general knowledge base
        mock_kb.assert_not_called()
        assert res.get("no_documentary_evidence_found") is True
        assert "no supporting evidence was found" in res["answer"].lower()
        assert "cyber harassment" in res["answer"].lower()
        assert res["sources"] == []


def test_phase2_test3_absent_topic_hard_stop_refusal():
    """TEST 3: What evidence proves bribery? Absent from document.
    Must return explicit no-evidence refusal."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence proves bribery and corruption by the defendant?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "rent_agreement.pdf",
        "status": "ready",
        "summary": "Tenancy contract.",
        "case_text": "Monthly rent of 25000."
    }]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=[]):
        res = _handle_ask(req, user_id="u1")
        assert res.get("no_documentary_evidence_found") is True
        assert "no supporting evidence was found" in res["answer"].lower()


def test_phase2_test4_present_topic_strictly_grounded():
    """TEST 4: What does the document say about monthly rent?
    Grounded strictly in retrieved chunks with citations."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What does the document say about monthly rent?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "lease_deed.pdf",
        "status": "ready",
        "summary": "Lease deed summary.",
        "case_text": "Tenant shall pay monthly rent of Rs 40,000 on the 5th of each calendar month."
    }]

    chunks = [{
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "page_number": 2,
        "chunk_text": "Tenant shall pay monthly rent of Rs 40,000 on or before the 5th of each calendar month.",
        "similarity": 0.92
    }]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=chunks), \
         patch("backend.routers.chat_router._verify_and_label", return_value=("supported", [{"verdict": "supported", "claim": "Rs 40,000 rent"}])), \
         patch("backend.routers.chat_router.call_llm") as mock_llm:
        mock_llm.return_value = "As per Page 2 of the lease deed, the monthly rent is Rs 40,000 payable on or before the 5th of every month."
        res = _handle_ask(req, user_id="u1")
        assert "40,000" in res["answer"]
        assert res["sources"][0]["name"] == "lease_deed.pdf — Page 2"


def test_phase2_test5_general_law_with_document_attached():
    """TEST 5: Ask 'What is section 351 BNS?' while a document is attached.
    Must route to GENERAL_LAW and NOT use the case chunks as evidence."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What is section 351 BNS?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "arbitration_award.pdf",
        "status": "ready",
        "summary": "Arbitration award.",
        "case_text": "Commercial dispute text."
    }]

    bns_match = [{
        "act_name": "Bharatiya Nyaya Sanhita, 2023",
        "section_number": "351",
        "full_text": "Section 351 defines assault under BNS 2023.",
        "source_type": "statute"
    }]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks") as mock_doc_search, \
         patch("backend.routers.chat_router.search_knowledge_base", return_value=bns_match) as mock_kb, \
         patch("backend.routers.chat_router.call_llm") as mock_llm:
        mock_llm.return_value = "Section 351 of the Bharatiya Nyaya Sanhita (BNS), 2023 defines the offence of assault."
        res = _handle_ask(req, user_id="u1")

        # Crucial check: search_document_chunks was NOT called for pure GENERAL_LAW query
        mock_doc_search.assert_not_called()
        mock_kb.assert_called_once()
        assert "Bharatiya Nyaya Sanhita" in res["answer"]
        assert res["routing_label"] == "GENERAL_LAW"


def test_phase2_test6_post_generation_hallucination_hard_stop():
    """TEST 6: Generator hallucinates unverified claims for a CASE_SPECIFIC query.
    Verifier flags the claims as unverified. Post-generation hard stop intercepts and returns refusal."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence proves the boundary wall was constructed in 1990?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "suit_record.pdf",
        "status": "ready",
        "summary": "Suit record.",
        "case_text": "Plot boundary discussion."
    }]

    chunks = [{
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "page_number": 1,
        "chunk_text": "Plot boundary disputed between parties.",
        "similarity": 0.70
    }]

    hallucinated_draft = "The plaintiff produced a 1990 municipal construction permit and tax receipts proving the wall was built in 1990."

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=chunks), \
         patch("backend.routers.chat_router.call_llm", return_value=hallucinated_draft), \
         patch("backend.routers.chat_router._verify_and_label", return_value=("unverified", [{"verdict": "unverified", "claim": "1990 municipal permit"}])):
        res = _handle_ask(req, user_id="u1")

        # Intercepted! Did NOT return the hallucinated municipal permit
        assert "municipal construction permit" not in res["answer"]
        assert res.get("no_documentary_evidence_found") is True
        assert "no supporting evidence was found" in res["answer"].lower()
