"""
Phase 2 & Phase 2.1 — Case-Evidence Grounding, LLM-as-Judge Reliability & Regression Tests.
Guarantees that CASE_SPECIFIC questions answer ONLY from retrieved evidence,
never invent unstated facts/documents, distinguish between 6 distinct verdict states,
and never conflate retrieval insufficiency with 'no evidence found'.
"""
import uuid
import pytest
from unittest.mock import patch, MagicMock
from backend.routers.chat_router import _handle_ask, QueryRequest
from ai_core.evaluation.llm_judge import (
    STATE_GROUNDED,
    STATE_PARTIALLY_GROUNDED,
    STATE_CONTRADICTED,
    STATE_NO_EVIDENCE_FOUND,
    STATE_RETRIEVAL_INSUFFICIENT,
    STATE_VERIFICATION_PENDING,
    judge_claims_against_evidence,
)


@pytest.fixture(autouse=True)
def mock_external_services():
    """Autouse fixture to mock network calls across all grounding tests."""
    with patch("backend.routers.chat_router._log"), \
         patch("ai_core.rag.embeddings.embed_text", return_value=[0.1] * 768), \
         patch("backend.routers.chat_router.embed_text", return_value=[0.1] * 768), \
         patch("backend.routers.chat_router.self_reflect", return_value={"usefulness": "high", "conclusion": None, "conclusion_needed": False}), \
         patch("backend.routers.chat_router.generate_suggestions", return_value=[]), \
         patch("trust_log.hash_chain.get_last_hash", return_value=""), \
         patch("trust_log.hash_chain.save_log_entry"):
        yield


# ==============================================================================
# EXISTING PHASE 2 TESTS (Regressions)
# ==============================================================================

def test_phase2_test1_plaintiff_title_no_fabricated_deeds():
    """TEST 1: Query plaintiff title. The document mentions oral partition, no registered sale deed.
    The prompt contract strictly prevents hallucinating sale deeds or tax receipts."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence supports the plaintiff's title?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
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

    mock_judgment = {
        "overall_verdict": STATE_GROUNDED,
        "is_accurate": True,
        "issue": "",
        "supported_claims": ["Plaintiff claims ownership based on oral family settlement dated 12.04.2015"],
        "unsupported_claims": [],
        "claim_verdicts": [{"claim": "oral family settlement", "verdict": "SUPPORTED", "page_numbers": [3]}],
    }

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=case_chunks), \
         patch("backend.routers.chat_router.extract_claims", return_value=(["oral family settlement dated 12.04.2015"], True)), \
         patch("backend.routers.chat_router.judge_claims_against_evidence", return_value=mock_judgment), \
         patch("backend.routers.chat_router.call_llm") as mock_llm:
        mock_llm.return_value = "According to Page 3, the plaintiff claims title based on an oral family settlement dated 12.04.2015 [land_dispute_suit.pdf — Page 3]."
        res = _handle_ask(req, user_id="u1")

        all_prompts = " ".join(call[0][1] for call in mock_llm.call_args_list if len(call[0]) > 1)
        assert "STRICT CASE-SPECIFIC EVIDENCE CONTRACT" in all_prompts
        assert "STRICT NEGATIVE CONSTRAINT" in all_prompts
        assert "sale deeds" in all_prompts or "sale deed" in all_prompts

        assert "oral family settlement" in res["answer"]
        assert "registered sale deed" not in res["answer"].lower()
        assert res["sources"][0]["name"] == "land_dispute_suit.pdf — Page 3"
        assert res["sources"][0]["page"] == 3
        assert "oral family settlement" in res["sources"][0]["excerpt"]


@pytest.mark.parametrize("query", ["What happened in 1941?", "Give all the dates of hearing"])
def test_short_followups_with_attached_document_use_case_context(query):
    from ai_core.router.intent_classifier import classify_intent

    result = classify_intent(query, has_document=True)

    assert result["label"] == "CASE_SPECIFIC"
    assert result["requires_case_context"] is True


def test_document_summary_is_not_mislabeled_as_verified():
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="summary btao iski", case_id=case_id)
    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "judgment.pdf",
        "status": "ready",
        "summary": "The court dismissed the appeal.",
        "case_text": "Full judgment text.",
    }]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.ensure_valid_session", return_value="session-1"), \
         patch("backend.routers.chat_router.get_recent_history", return_value=""), \
         patch("backend.routers.chat_router.save_message"):
        result = _handle_ask(req, user_id="u1")

    assert result["verified"] is False
    assert result["sources"][0]["verification_status"] == "unverified"
    assert result["sources"][0]["section"] == "Full-document summary"


def test_phase2_test2_cyber_harassment_refusal_on_land_document():
    """TEST 2: Query cyber harassment on a land document.
    Must return clear refusal and NOT use web/statutory search."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence proves cyber harassment?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "land_record.pdf",
        "status": "ready",
        "summary": "Land revenue records.",
        "case_text": "Agricultural plot survey numbers."
    }]

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

        mock_kb.assert_not_called()
        assert res.get("no_documentary_evidence_found") is True
        assert res.get("verdict_state") == STATE_NO_EVIDENCE_FOUND
        assert "no supporting evidence was found" in res["answer"].lower()
        assert "cyber harassment" in res["answer"].lower()
        assert res["sources"] == []


def test_phase2_test3_absent_topic_hard_stop_refusal():
    """TEST 3: What evidence proves bribery? When low similarity chunks return, reports no documentary evidence found."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence proves bribery and corruption by the defendant?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "rent_agreement.pdf",
        "status": "ready",
        "summary": "Tenancy contract.",
        "case_text": "Monthly rent of 25000."
    }]

    unrelated_chunks = [{
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "page_number": 1,
        "chunk_text": "Monthly tenancy agreement clauses.",
        "similarity": 0.05
    }]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=unrelated_chunks):
        res = _handle_ask(req, user_id="u1")
        assert res.get("no_documentary_evidence_found") is True
        assert res.get("verdict_state") == STATE_NO_EVIDENCE_FOUND
        assert "no supporting evidence was found" in res["answer"].lower()


def test_phase2_test4_present_topic_strictly_grounded():
    """TEST 4: What does the document say about monthly rent?
    Grounded strictly in retrieved chunks with citations."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What does the document say about monthly rent?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
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

    mock_judgment = {
        "overall_verdict": STATE_GROUNDED,
        "is_accurate": True,
        "issue": "",
        "supported_claims": ["monthly rent of Rs 40,000"],
        "unsupported_claims": [],
        "claim_verdicts": [{"claim": "monthly rent of Rs 40,000", "verdict": "SUPPORTED", "page_numbers": [2]}],
    }

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=chunks), \
         patch("backend.routers.chat_router.extract_claims", return_value=(["monthly rent is Rs 40,000"], True)), \
         patch("backend.routers.chat_router.judge_claims_against_evidence", return_value=mock_judgment), \
         patch("backend.routers.chat_router.call_llm") as mock_llm:
        mock_llm.return_value = "As per Page 2 of the lease deed, the monthly rent is Rs 40,000 payable on or before the 5th of every month."
        res = _handle_ask(req, user_id="u1")
        assert "40,000" in res["answer"]
        assert res["sources"][0]["name"] == "lease_deed.pdf — Page 2"
        assert res.get("verdict_state") == STATE_GROUNDED


def test_phase2_test5_general_law_with_document_attached():
    """TEST 5: Ask 'What is section 351 BNS?' while a document is attached.
    Must route to GENERAL_LAW and NOT use the case chunks as evidence."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What is section 351 BNS?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "arbitration_award.pdf",
        "status": "ready",
        "summary": "Arbitration award.",
        "case_text": "Commercial dispute text."
    }]

    bns_rows = [{
        "act": "BNS",
        "act_name": "Bharatiya Nyaya Sanhita, 2023",
        "section": "351",
        "heading": "Assault",
        "text": "Section 351 defines assault under BNS 2023.",
        "page": 120,
        "source_url": "https://www.indiacode.nic.in/bns.pdf",
    }]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks") as mock_doc_search, \
         patch("backend.routers.chat_router.find_sections", return_value=bns_rows), \
         patch("backend.routers.chat_router.mapping_note", return_value=""), \
         patch("backend.routers.chat_router.call_llm", return_value="Section 351 of the Bharatiya Nyaya Sanhita (BNS), 2023 defines the offence of assault."):
        res = _handle_ask(req, user_id="u1")

        mock_doc_search.assert_not_called()
        assert "Bharatiya Nyaya Sanhita" in res["answer"]
        assert res["routing_label"] == "GENERAL_LAW"


def test_phase2_test6_post_generation_hallucination_hard_stop():
    """TEST 6: Generator hallucinates unverified claims for a CASE_SPECIFIC query.
    LLM Judge flags all claims as unverified. Post-generation hard stop intercepts and returns refusal."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence proves the boundary wall was constructed in 1990?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
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

    mock_judgment = {
        "overall_verdict": STATE_NO_EVIDENCE_FOUND,
        "is_accurate": False,
        "issue": "Municipal permit not found in evidence.",
        "supported_claims": [],
        "unsupported_claims": ["The plaintiff produced a 1990 municipal construction permit"],
        "claim_verdicts": [{"claim": "1990 municipal permit", "verdict": "NOT_VERIFIABLE", "page_numbers": []}],
    }

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=chunks), \
         patch("backend.routers.chat_router.call_llm", return_value=hallucinated_draft), \
         patch("backend.routers.chat_router.extract_claims", return_value=(["1990 municipal permit"], True)), \
         patch("backend.routers.chat_router.judge_claims_against_evidence", return_value=mock_judgment):
        res = _handle_ask(req, user_id="u1")

        assert "municipal construction permit" not in res["answer"]
        assert res.get("no_documentary_evidence_found") is True
        assert res.get("verdict_state") == STATE_NO_EVIDENCE_FOUND
        assert "no supporting evidence was found" in res["answer"].lower()


# ==============================================================================
# PHASE 2.1 GOLDEN TEST SUITE (Tests A through G)
# ==============================================================================

def test_phase2_1_golden_test_a_gorakhram_plaintiff_evidence():
    """GOLDEN TEST A:
    Gorakhram PDF: 'Is case me plaintiff ne apne claim ko support karne ke liye kaunse evidence diye hain?'
    Expected: letters (29/30 Aug 1929) + oral evidence/depositions (Laxmibai, Inderlal, Kanhaiyalal) + diamond ring + possession.
    Verdict: GROUNDED / PARTIALLY_GROUNDED.
    Must NOT refuse as 'no evidence found'."""
    case_id = str(uuid.uuid4())
    query = "Is case me plaintiff ne apne claim ko support karne ke liye kaunse evidence diye hain?"
    req = QueryRequest(query=query, case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "Gorakhram_Sadhuram_vs_Laxmibai_1950.pdf",
        "status": "ready",
        "summary": "Mortgage and title dispute between Gorakhram Sadhuram and Laxmibai.",
        "case_text": "Case concerning property mortgaged with letters of 29/30 Aug 1929 and depositions."
    }]

    gorakhram_chunks = [
        {
            "id": str(uuid.uuid4()),
            "case_id": case_id,
            "page_number": 2,
            "chunk_text": "Plaintiff relied upon letters dated 29th and 30th August 1929 evidencing deposit of title deeds and equitable mortgage.",
            "similarity": 0.88,
        },
        {
            "id": str(uuid.uuid4()),
            "case_id": case_id,
            "page_number": 3,
            "chunk_text": "Oral evidence was adduced by the plaintiff Laxmibai and her husband Inderlal, confirming the transaction and delivery of the diamond ring.",
            "similarity": 0.85,
        },
        {
            "id": str(uuid.uuid4()),
            "case_id": case_id,
            "page_number": 4,
            "chunk_text": "Witness Kanhaiyalal (son of plaintiff) deposed regarding plaintiff's continuous possession, payment of municipal taxes, and structural repairs.",
            "similarity": 0.82,
        },
    ]

    draft_answer = (
        "In this case, the plaintiff presented several key pieces of evidence to support her claim:\n"
        "1. Documentary evidence: Letters dated 29th and 30th August 1929 confirming the equitable mortgage.\n"
        "2. Oral depositions: Depositions of the plaintiff Laxmibai and her husband Inderlal regarding the transaction and handover of the diamond ring.\n"
        "3. Witness evidence: Testimony of son Kanhaiyalal proving continuous possession, tax payments, and property repairs."
    )

    mock_judgment = {
        "overall_verdict": STATE_GROUNDED,
        "is_accurate": True,
        "issue": "",
        "supported_claims": [
            "Letters dated 29th and 30th August 1929",
            "Depositions of Laxmibai and husband Inderlal regarding diamond ring",
            "Evidence of son Kanhaiyalal proving possession, tax payments, and repairs",
        ],
        "unsupported_claims": [],
        "claim_verdicts": [
            {"claim": "Letters dated 29th and 30th August 1929", "verdict": "SUPPORTED", "page_numbers": [2]},
            {"claim": "Depositions of Laxmibai and Inderlal", "verdict": "SUPPORTED", "page_numbers": [3]},
            {"claim": "Son Kanhaiyalal evidence of possession and repairs", "verdict": "SUPPORTED", "page_numbers": [4]},
        ],
    }

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=gorakhram_chunks), \
         patch("backend.routers.chat_router.call_llm", return_value=draft_answer), \
         patch("backend.routers.chat_router.extract_claims", return_value=(mock_judgment["supported_claims"], True)), \
         patch("backend.routers.chat_router.judge_claims_against_evidence", return_value=mock_judgment):

        res = _handle_ask(req, user_id="u1")

        # Must NOT refuse
        assert res.get("no_documentary_evidence_found") is not True
        assert res.get("verdict_state") in (STATE_GROUNDED, STATE_PARTIALLY_GROUNDED)
        assert res["verified"] is True

        # Check factual coverage
        ans = res["answer"]
        assert "29th" in ans or "August 1929" in ans or "1929" in ans
        assert "Laxmibai" in ans or "Inderlal" in ans
        assert "diamond ring" in ans or "Kanhaiyalal" in ans or "possession" in ans
        # Forbidden fabricated claims must be absent
        assert "registered sale deed" not in ans.lower()
        assert "probate certificate" not in ans.lower()


def test_phase2_1_golden_test_b_gorakhram_cyber_harassment_refusal():
    """GOLDEN TEST B:
    Gorakhram PDF: 'What evidence proves cyber harassment?'
    Expected: NO_EVIDENCE_FOUND only when retrieval coverage is sufficient.
    Must return clear no-evidence finding, not retrieval insufficient."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence proves cyber harassment in this case?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "Gorakhram_vs_Laxmibai.pdf",
        "status": "ready",
        "summary": "1950 mortgage suit.",
        "case_text": "1950 property mortgage suit."
    }]

    unrelated_chunks = [{
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "page_number": 1,
        "chunk_text": "Suit for declaration of mortgage rights.",
        "similarity": 0.04
    }]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=unrelated_chunks):

        res = _handle_ask(req, user_id="u1")
        assert res.get("no_documentary_evidence_found") is True
        assert res.get("verdict_state") == STATE_NO_EVIDENCE_FOUND
        assert "no supporting evidence was found" in res["answer"].lower()
        assert "cyber harassment" in res["answer"].lower()


def test_phase2_1_golden_test_c_gorakhram_plaintiff_possession():
    """GOLDEN TEST C:
    Gorakhram PDF: 'What does the judgment say about the plaintiff's possession?'
    Expected: Grounded in actual document pages (e.g. continuous possession, repair of premises)."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What does the judgment say about the plaintiff's possession?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "Gorakhram_vs_Laxmibai.pdf",
        "status": "ready",
        "summary": "Mortgage suit.",
        "case_text": "Plaintiff established actual continuous possession and paid all municipal assessments."
    }]

    chunks = [{
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "page_number": 4,
        "chunk_text": "The trial court found that the plaintiff remained in undisturbed physical possession of the mortgaged property and carried out periodic repairs.",
        "similarity": 0.91
    }]

    mock_judgment = {
        "overall_verdict": STATE_GROUNDED,
        "is_accurate": True,
        "issue": "",
        "supported_claims": ["Plaintiff remained in undisturbed physical possession and did repairs"],
        "unsupported_claims": [],
        "claim_verdicts": [{"claim": "undisturbed possession", "verdict": "SUPPORTED", "page_numbers": [4]}],
    }

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=chunks), \
         patch("backend.routers.chat_router.call_llm", return_value="As per Page 4, the plaintiff remained in undisturbed physical possession of the property and carried out repairs."), \
         patch("backend.routers.chat_router.extract_claims", return_value=(["undisturbed possession"], True)), \
         patch("backend.routers.chat_router.judge_claims_against_evidence", return_value=mock_judgment):

        res = _handle_ask(req, user_id="u1")
        assert "undisturbed physical possession" in res["answer"]
        assert res["verified"] is True
        assert res.get("verdict_state") == STATE_GROUNDED
        assert res["sources"][0]["name"] == "Gorakhram_vs_Laxmibai.pdf — Page 4"


def test_phase2_1_golden_test_d_intentionally_unsupported_topic():
    """GOLDEN TEST D:
    An intentionally unsupported topic (e.g. offshore tax evasion).
    Expected: NO_EVIDENCE_FOUND."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence proves the defendant engaged in offshore tax evasion in Panama?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "civil_suit_1950.pdf",
        "status": "ready",
        "summary": "Civil suit.",
        "case_text": "Dispute over domestic loan and mortgage."
    }]

    unrelated_chunks = [{
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "page_number": 1,
        "chunk_text": "Civil suit between local parties regarding mortgage of a shop.",
        "similarity": 0.06
    }]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=unrelated_chunks):

        res = _handle_ask(req, user_id="u1")
        assert res.get("verdict_state") == STATE_NO_EVIDENCE_FOUND
        assert res.get("no_documentary_evidence_found") is True
        assert "no supporting evidence was found" in res["answer"].lower()


def test_phase2_1_golden_test_e_simulated_retrieval_failure():
    """GOLDEN TEST E:
    Simulated retrieval failure (0 chunks returned due to retrieval error / empty match).
    Expected: RETRIEVAL_INSUFFICIENT, NOT NO_EVIDENCE_FOUND."""
    case_id = str(uuid.uuid4())
    # Hindi/Hinglish query
    req_hi = QueryRequest(query="Is case me plaintiff ne kya claim kiya hai?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "case_file.pdf",
        "status": "ready",
        "summary": "Case summary.",
        "case_text": "Case text."
    }]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=[]):

        res_hi = _handle_ask(req_hi, user_id="u1")

        # CRITICAL: Must be RETRIEVAL_INSUFFICIENT, NEVER NO_EVIDENCE_FOUND
        assert res_hi.get("verdict_state") == STATE_RETRIEVAL_INSUFFICIENT
        assert res_hi.get("retrieval_insufficient") is True
        assert res_hi.get("no_documentary_evidence_found") is not True
        assert "पर्याप्त संबंधित अंश retrieve नहीं कर पाया" in res_hi["answer"]

    # English query
    req_en = QueryRequest(query="What evidence supports the plaintiff's title?", case_id=case_id)
    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=[]):

        res_en = _handle_ask(req_en, user_id="u1")
        assert res_en.get("verdict_state") == STATE_RETRIEVAL_INSUFFICIENT
        assert res_en.get("retrieval_insufficient") is True
        assert "could not retrieve sufficient relevant passages" in res_en["answer"]


def test_phase2_1_golden_test_f_simulated_judge_infra_failure():
    """GOLDEN TEST F:
    Simulated judge/API/JSON failure.
    Expected: VERIFICATION_PENDING, NOT NO_EVIDENCE_FOUND."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence supports the plaintiff's claim?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "valid_case.pdf",
        "status": "ready",
        "summary": "Valid case.",
        "case_text": "Plaintiff relied on letters of Aug 1929."
    }]

    chunks = [{
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "page_number": 1,
        "chunk_text": "Plaintiff produced letters of August 1929.",
        "similarity": 0.85
    }]

    draft = "The plaintiff produced August 1929 letters to support her claim."

    # Simulate Judge / Verifier failure
    mock_infra_error = {
        "claim_verdicts": [],
        "overall_verdict": STATE_VERIFICATION_PENDING,
        "is_accurate": True,
        "issue": "API connection timeout",
        "supported_claims": [],
        "unsupported_claims": [],
    }

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=chunks), \
         patch("backend.routers.chat_router.call_llm", return_value=draft), \
         patch("backend.routers.chat_router.extract_claims", return_value=(["August 1929 letters"], True)), \
         patch("backend.routers.chat_router.judge_claims_against_evidence", return_value=mock_infra_error):

        res = _handle_ask(req, user_id="u1")

        # Must NEVER be NO_EVIDENCE_FOUND
        assert res.get("verdict_state") == STATE_VERIFICATION_PENDING
        assert res.get("no_documentary_evidence_found") is not True
        assert res.get("verified") is False
        assert "August 1929 letters" in res["answer"]


def test_phase2_1_golden_test_g_hallucinated_draft_unsupported_claims_removed():
    """GOLDEN TEST G:
    Draft contains both a genuine supported claim (letters of Aug 1929)
    AND hallucinated claims (registered sale deed, probate order, tax receipts).
    Expected: PARTIALLY_GROUNDED, unsupported claims removed, supported claims retained."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence supports the plaintiff's claim?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "mortgage_suit.pdf",
        "status": "ready",
        "summary": "Mortgage suit.",
        "case_text": "Deposit of title deeds via letters dated 29 August 1929."
    }]

    chunks = [{
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "page_number": 2,
        "chunk_text": "Plaintiff established deposit of title deeds through letters dated 29 August 1929.",
        "similarity": 0.89
    }]

    mixed_draft = (
        "The plaintiff proved her claim by producing:\n"
        "1. Letters dated 29 August 1929.\n"
        "2. A registered sale deed executed in 1930.\n"
        "3. A probate certificate issued by the High Court."
    )

    mock_judgment = {
        "overall_verdict": STATE_PARTIALLY_GROUNDED,
        "is_accurate": True,
        "issue": "Registered sale deed and probate certificate are not mentioned in the evidence.",
        "supported_claims": ["Letters dated 29 August 1929"],
        "unsupported_claims": [
            "A registered sale deed executed in 1930",
            "A probate certificate issued by the High Court",
        ],
        "claim_verdicts": [
            {"claim": "Letters dated 29 August 1929", "verdict": "SUPPORTED", "page_numbers": [2]},
            {"claim": "A registered sale deed executed in 1930", "verdict": "NOT_VERIFIABLE", "page_numbers": []},
            {"claim": "A probate certificate issued by the High Court", "verdict": "NOT_VERIFIABLE", "page_numbers": []},
        ],
    }

    filtered_draft = "Based on the evidence, the plaintiff proved her claim through letters dated 29 August 1929 [mortgage_suit.pdf — Page 2]."

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=chunks), \
         patch("backend.routers.chat_router.call_llm", return_value=mixed_draft), \
         patch("backend.routers.chat_router.extract_claims", return_value=(["Letters dated 29 August 1929", "registered sale deed", "probate certificate"], True)), \
         patch("backend.routers.chat_router.judge_claims_against_evidence", return_value=mock_judgment), \
         patch("backend.routers.chat_router.filter_supported_claims_answer", return_value=filtered_draft):

        res = _handle_ask(req, user_id="u1")

        assert res.get("verdict_state") == STATE_PARTIALLY_GROUNDED
        assert "29 August 1929" in res["answer"]
        # Hallucinated items MUST be removed
        assert "registered sale deed" not in res["answer"].lower()
        assert "probate certificate" not in res["answer"].lower()


# ==============================================================================
# PHASE 2.2 RETRIEVAL RESILIENCE & MULTI-STRATEGY TESTS
# ==============================================================================

def test_phase2_2_vector_store_multi_rpc_fallback():
    """Verify search_document_chunks falls back to match_document_chunks_multi when match_document_chunks raises error."""
    from ai_core.rag.vector_store import search_document_chunks
    case_id = str(uuid.uuid4())
    mock_client = MagicMock()

    def mock_rpc(rpc_name, params):
        mock_res = MagicMock()
        if rpc_name == "match_document_chunks":
            raise RuntimeError("function match_document_chunks does not exist")
        elif rpc_name == "match_document_chunks_multi":
            mock_res.execute.return_value.data = [
                {"id": str(uuid.uuid4()), "case_id": case_id, "page_number": 2, "chunk_text": "Letters of 29 August 1929", "similarity": 0.88}
            ]
            return mock_res
        mock_res.execute.return_value.data = []
        return mock_res

    mock_client.rpc.side_effect = mock_rpc
    with patch("ai_core.rag.vector_store.get_supabase_client", return_value=mock_client):
        chunks = search_document_chunks([0.1]*768, case_id=case_id)
        assert len(chunks) == 1
        assert chunks[0]["case_id"] == case_id
        assert "29 August 1929" in chunks[0]["chunk_text"]


def test_phase2_2_vector_store_direct_table_cosine_sim_fallback():
    """Verify search_document_chunks falls back to direct table fetch + cosine similarity when all RPCs fail."""
    from ai_core.rag.vector_store import search_document_chunks
    case_id = str(uuid.uuid4())
    mock_client = MagicMock()
    mock_client.rpc.side_effect = RuntimeError("RPC connection error")

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value.data = [
        {"id": str(uuid.uuid4()), "case_id": case_id, "page_number": 3, "chunk_text": "Laxmibai deposition regarding diamond ring", "embedding": [0.1]*768},
        {"id": str(uuid.uuid4()), "case_id": case_id, "page_number": 4, "chunk_text": "Undisturbed physical possession", "embedding": [0.05]*768},
    ]
    mock_client.table.return_value = mock_table

    with patch("ai_core.rag.vector_store.get_supabase_client", return_value=mock_client):
        chunks = search_document_chunks([0.1]*768, case_id=case_id)
        assert len(chunks) == 2
        assert chunks[0]["case_id"] == case_id
        assert "Laxmibai" in chunks[0]["chunk_text"]


def test_phase2_2_chat_router_dynamic_case_text_chunking_fallback():
    """Verify _handle_ask dynamically indexes case_text on-the-fly when document chunks were missing."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What does the judgment say about the plaintiff's possession?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "Gorakhram_vs_Laxmibai.pdf",
        "status": "ready",
        "summary": "1950 mortgage suit.",
        "case_text": "The plaintiff proved continuous undisturbed possession and structural repairs of the premises."
    }]

    search_calls = []

    def mock_search_doc_chunks(query_vec, target_case_id, match_count=8, *args, **kwargs):
        search_calls.append(len(search_calls))
        if len(search_calls) == 1:
            return []  # Initial search has 0 chunks
        # After on-the-fly indexing, returns newly indexed chunks
        return [{
            "id": str(uuid.uuid4()),
            "case_id": target_case_id,
            "page_number": 1,
            "chunk_text": "The plaintiff proved continuous undisturbed possession and structural repairs of the premises.",
            "similarity": 0.90,
        }]

    mock_judgment = {
        "overall_verdict": STATE_GROUNDED,
        "is_accurate": True,
        "issue": "",
        "supported_claims": ["The plaintiff proved continuous undisturbed possession"],
        "unsupported_claims": [],
        "claim_verdicts": [{"claim": "undisturbed possession", "verdict": "SUPPORTED", "page_numbers": [1]}],
    }

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", side_effect=mock_search_doc_chunks), \
         patch("ai_core.rag.document_chunker.chunk_text_into_pages", return_value=1), \
         patch("backend.routers.chat_router.call_llm", return_value="The plaintiff proved continuous undisturbed possession."), \
         patch("backend.routers.chat_router.extract_claims", return_value=(["The plaintiff proved continuous undisturbed possession"], True)), \
         patch("backend.routers.chat_router.judge_claims_against_evidence", return_value=mock_judgment):

        res = _handle_ask(req, user_id="u1")

        assert res.get("verdict_state") == STATE_GROUNDED
        assert "undisturbed possession" in res["answer"]
        assert res.get("no_documentary_evidence_found") is not True
        assert res.get("retrieval_insufficient") is not True


# ==============================================================================
# PHASE 2.3 END-TO-END PRODUCTION DOCUMENT QA REGRESSION TESTS
# ==============================================================================

def test_phase2_3_gorakhram_hinglish_plaintiff_evidence_retrieval_and_pages():
    """Verify Hinglish question 'Is case me plaintiff ne apne claim ko support karne ke liye kaunse evidence diye hain?'
    successfully retrieves letters, depositions, ring, and possession with exact page citations."""
    case_id = str(uuid.uuid4())
    query = "Is case me plaintiff ne apne claim ko support karne ke liye kaunse evidence diye hain?"
    req = QueryRequest(query=query, case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "Gorakhram_Sadhuram_vs_Laxmibai_1950.pdf",
        "status": "ready",
        "summary": "1950 mortgage judgment.",
        "case_text": "Case concerning property mortgaged with letters of 29/30 Aug 1929 and depositions."
    }]

    chunks = [
        {"id": str(uuid.uuid4()), "case_id": case_id, "page_number": 2, "chunk_text": "Plaintiff produced letters of 29th and 30th August 1929 evidencing equitable mortgage.", "similarity": 0.89},
        {"id": str(uuid.uuid4()), "case_id": case_id, "page_number": 3, "chunk_text": "Oral deposition of Laxmibai and Inderlal proving delivery of the diamond ring.", "similarity": 0.86},
        {"id": str(uuid.uuid4()), "case_id": case_id, "page_number": 4, "chunk_text": "Evidence of son Kanhaiyalal establishing undisturbed possession and property repairs.", "similarity": 0.84},
    ]

    draft_answer = (
        "In this judgment, the plaintiff produced the following evidence to support her claim:\n"
        "1. Letters dated 29th and 30th August 1929 confirming the equitable mortgage [Page 2].\n"
        "2. Oral depositions of Laxmibai and Inderlal regarding the diamond ring [Page 3].\n"
        "3. Evidence of son Kanhaiyalal proving continuous possession and repairs [Page 4]."
    )

    mock_judgment = {
        "overall_verdict": STATE_GROUNDED,
        "is_accurate": True,
        "issue": "",
        "supported_claims": [
            "Letters dated 29th and 30th August 1929",
            "Oral depositions of Laxmibai and Inderlal regarding diamond ring",
            "Evidence of son Kanhaiyalal proving continuous possession and repairs",
        ],
        "unsupported_claims": [],
        "claim_verdicts": [
            {"claim": "Letters dated 29th and 30th August 1929", "verdict": "SUPPORTED", "page_numbers": [2]},
            {"claim": "Oral depositions of Laxmibai and Inderlal", "verdict": "SUPPORTED", "page_numbers": [3]},
            {"claim": "Evidence of son Kanhaiyalal", "verdict": "SUPPORTED", "page_numbers": [4]},
        ],
    }

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=chunks), \
         patch("backend.routers.chat_router.call_llm", return_value=draft_answer), \
         patch("backend.routers.chat_router.extract_claims", return_value=(mock_judgment["supported_claims"], True)), \
         patch("backend.routers.chat_router.judge_claims_against_evidence", return_value=mock_judgment):

        res = _handle_ask(req, user_id="u1")

        assert res.get("verdict_state") == STATE_GROUNDED
        assert res["verified"] is True
        assert "1929" in res["answer"]
        assert "Laxmibai" in res["answer"]
        assert "diamond ring" in res["answer"]
        assert "possession" in res["answer"]
        assert res["sources"][0]["name"] == "Gorakhram_Sadhuram_vs_Laxmibai_1950.pdf — Page 2"


def test_phase2_3_gorakhram_plaintiff_possession_query_variants():
    """Verify both English and Hinglish queries for 'Plaintiff ka possession' route to CASE_SPECIFIC and return Page 4 evidence."""
    case_id = str(uuid.uuid4())
    req_hinglish = QueryRequest(query="Plaintiff ka possession", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "Gorakhram_vs_Laxmibai.pdf",
        "status": "ready",
        "summary": "Mortgage suit.",
        "case_text": "Continuous possession and payment of taxes by plaintiff."
    }]

    chunks = [{
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "page_number": 4,
        "chunk_text": "The plaintiff established continuous undisturbed possession and payment of municipal taxes.",
        "similarity": 0.91
    }]

    mock_judgment = {
        "overall_verdict": STATE_GROUNDED,
        "is_accurate": True,
        "issue": "",
        "supported_claims": ["continuous undisturbed possession and payment of municipal taxes"],
        "unsupported_claims": [],
        "claim_verdicts": [{"claim": "continuous possession", "verdict": "SUPPORTED", "page_numbers": [4]}],
    }

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=chunks), \
         patch("backend.routers.chat_router.call_llm", return_value="The plaintiff established continuous undisturbed possession and payment of taxes [Page 4]."), \
         patch("backend.routers.chat_router.extract_claims", return_value=(["continuous possession"], True)), \
         patch("backend.routers.chat_router.judge_claims_against_evidence", return_value=mock_judgment):

        res = _handle_ask(req_hinglish, user_id="u1")

        assert res.get("verdict_state") == STATE_GROUNDED
        assert "possession" in res["answer"]
        assert res["sources"][0]["name"] == "Gorakhram_vs_Laxmibai.pdf — Page 4"


def test_phase2_3_cyber_harassment_with_doc_attached_returns_no_evidence():
    """Verify 'What evidence proves cyber harassment?' when asked on an attached property judgment
    routes to CASE_SPECIFIC and returns NO_EVIDENCE_FOUND refusal, never generic IT Act law."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What evidence proves cyber harassment?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "Gorakhram_Sadhuram_vs_Laxmibai_1950.pdf",
        "status": "ready",
        "summary": "1950 mortgage suit.",
        "case_text": "Mortgage and property dispute text."
    }]

    unrelated_chunks = [{
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "page_number": 1,
        "chunk_text": "Suit for declaration of mortgage rights.",
        "similarity": 0.05
    }]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=unrelated_chunks), \
         patch("backend.routers.chat_router.search_knowledge_base") as mock_kb:

        res = _handle_ask(req, user_id="u1")

        mock_kb.assert_not_called()
        assert res.get("verdict_state") == STATE_NO_EVIDENCE_FOUND
        assert res.get("no_documentary_evidence_found") is True
        assert "no supporting evidence was found" in res["answer"].lower()
        assert "cyber harassment" in res["answer"].lower()


def test_phase2_3_general_cyber_law_question_distinct_from_document():
    """Verify a genuinely general legal question 'What is the punishment under Section 66E Information Technology Act?'
    asked with a document attached routes to GENERAL_LAW and is clearly labeled as general legal info."""
    case_id = str(uuid.uuid4())
    req = QueryRequest(query="What is the punishment under section 66E of the Information Technology Act?", case_id=case_id)

    mock_client = MagicMock()
    mock_client.table().select().eq().eq().execute.return_value.data = [{
        "id": case_id,
        "filename": "Gorakhram_1950.pdf",
        "status": "ready",
        "summary": "1950 mortgage suit.",
        "case_text": "Mortgage text."
    }]

    statute_rows = [{
        "act": "IT Act",
        "act_name": "Information Technology Act, 2000",
        "section": "66E",
        "heading": "Punishment for violation of privacy",
        "text": "Punishment for violation of privacy under Section 66E.",
        "page": 40,
        "source_url": "https://www.indiacode.nic.in/it-act.pdf",
    }]

    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks") as mock_doc_search, \
         patch("backend.routers.chat_router.find_sections", return_value=statute_rows), \
         patch("backend.routers.chat_router.statute_evidence", return_value="Punishment for violation of privacy under Section 66E."), \
         patch("backend.routers.chat_router.hint_for", return_value=None), \
         patch("backend.routers.chat_router.mapping_note", return_value=""), \
         patch("backend.routers.chat_router.ground_answer", side_effect=lambda ans, *a, **kw: ans), \
         patch("backend.routers.chat_router.call_llm", return_value="Section 66E of the Information Technology Act, 2000 penalizes capturing or transmitting private images."):

        res = _handle_ask(req, user_id="u1")

        mock_doc_search.assert_not_called()
        assert res["routing_label"] == "GENERAL_LAW"
        assert "Section 66E" in res["answer"]


def test_phase2_3_scanned_pdf_ocr_chunking_and_deduplication_safety():
    """Verify chunk_text_into_pages does NOT insert duplicate chunks if already indexed."""
    from ai_core.rag.document_chunker import chunk_text_into_pages
    case_id = str(uuid.uuid4())
    mock_client = MagicMock()
    
    # Simulate chunks already existing
    mock_client.table().select().eq().limit().execute.return_value.data = [{"id": str(uuid.uuid4())}]

    with patch("ai_core.rag.vector_store.get_supabase_client", return_value=mock_client), \
         patch("ai_core.rag.document_chunker.insert_document_chunks_batch") as mock_insert:

        count = chunk_text_into_pages("Sample case text content.", case_id)
        assert count == 1
        mock_insert.assert_not_called()  # Safely avoided duplicate insert!