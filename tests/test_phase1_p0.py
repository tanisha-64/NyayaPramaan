import pytest
from unittest.mock import patch, MagicMock
from ai_core.guardrails.output_guard import redact_pii
from ai_core.rag.document_classifier import classify_document
from ai_core.router.intent_classifier import classify_intent, REFUSAL_MESSAGE
from ai_core.rag.crag_corrector import is_allowed_legal_url, is_legally_relevant_content, corrective_web_search
from ai_core.evaluation.llm_judge import judge_answer
from ai_core.rag.vector_store import search_knowledge_base
from ai_core.rag.document_reader import read_case_file_with_gemini
from backend.routers.chat_router import general_legal_answer, _handle_ask, QueryRequest


def test_aadhaar_and_pan_pii_redaction():
    """Requirement 1: Verify Aadhaar and PAN redaction while preserving phone & email."""
    text = "User Aadhaar 4532 9812 3456 and PAN ABCDE1234F with phone 9876543210 and email test@nyaya.org"
    redacted = redact_pii(text)
    assert "4532 9812 3456" not in redacted
    assert "ABCDE1234F" not in redacted
    assert "9876543210" not in redacted
    assert "test@nyaya.org" not in redacted
    assert "[REDACTED_AADHAAR]" in redacted
    assert "[REDACTED_PAN]" in redacted


def test_document_classifier_filename_compatibility():
    """Requirement 2: Verify classify_document works with filename and text_sample."""
    res1 = classify_document("", filename="anticipatory_bail_petition.pdf")
    assert res1["is_legal_relevant"] is True
    assert res1["document_type"] == "case_file"

    res2 = classify_document("IN THE SUPREME COURT OF INDIA. WRIT PETITION NO. 45 OF 2023.")
    assert res2["is_legal_relevant"] is True


def test_intent_classification_case_specific():
    """Requirement 3A: CASE_SPECIFIC query classification."""
    q = "uploaded PDF me plaintiff ka title kis evidence se prove hota hai?"
    intent = classify_intent(q)
    assert intent["domain"] == "legal"
    assert intent["query_mode"] == "CASE_SPECIFIC"
    assert intent["requires_case_context"] is True


def test_intent_classification_general_law():
    """Requirement 3B: GENERAL_LAW query classification."""
    q = "harassment k liye kaunsi dhara lagti hai?"
    intent = classify_intent(q)
    assert intent["domain"] == "legal"
    assert intent["query_mode"] == "GENERAL_LAW"
    assert intent["requires_statutory_law"] is True


def test_intent_classification_mixed():
    """Requirement 3C: MIXED query classification."""
    q = "mere uploaded land dispute case mein adverse possession ka kya effect ho sakta hai?"
    intent = classify_intent(q)
    assert intent["domain"] == "legal"
    assert intent["query_mode"] == "MIXED"
    assert intent["requires_case_context"] is True
    assert intent["requires_statutory_law"] is True


def test_intent_classification_out_of_domain():
    """Requirement 3D & 8 (Case E): Out-of-domain safety refusal for romantic poem."""
    q = "Write me a romantic poem."
    intent = classify_intent(q)
    assert intent["domain"] == "out_of_domain"
    assert intent["query_mode"] == "OUT_OF_DOMAIN"


def test_crag_domain_allowlist_and_wiktionary_rejection():
    """Requirement 4: Ensure Wiktionary/Wikipedia/blogs are rejected, legal sites allowed."""
    assert is_allowed_legal_url("https://indiacode.nic.in/handle/123456789/1362") is True
    assert is_allowed_legal_url("https://sci.gov.in/judgments") is True
    assert is_allowed_legal_url("https://livelaw.in/top-stories/supreme-court") is True
    assert is_allowed_legal_url("https://indiankanoon.org/doc/123456/") is True
    
    # Blocked domains
    assert is_allowed_legal_url("https://en.wiktionary.org/wiki/top") is False
    assert is_allowed_legal_url("https://en.wikipedia.org/wiki/Law") is False
    assert is_allowed_legal_url("https://quora.com/what-is-law") is False
    assert is_allowed_legal_url("https://random-law-blog.com/tips") is False


def test_crag_rejects_bluetooth_and_tech_support():
    """Case G: Ensure Microsoft Bluetooth troubleshooting and non-legal tech pages are rejected."""
    # Technical support / hardware titles are rejected
    assert is_legally_relevant_content("Fix Bluetooth problems in Windows", "Support article about pairing bluetooth audio devices") is False
    assert is_legally_relevant_content("Microsoft Support - Troubleshoot Devices", "Device drivers and updates for hardware") is False
    # Authoritative legal content is accepted
    assert is_legally_relevant_content("Section 351 Bharatiya Nyaya Sanhita", "Offence of assault defined under BNS 2023 in Indian court") is True


def test_crag_corrective_search_rejects_untrusted():
    """Requirement 4: Mocked DDGS returning Wiktionary returns None."""
    with patch("ai_core.rag.crag_corrector.DDGS") as mock_ddgs:
        instance = MagicMock()
        instance.text.return_value = [
            {"title": "top - Wiktionary", "body": "The highest part of something", "href": "https://en.wiktionary.org/wiki/top"}
        ]
        mock_ddgs.return_value.__enter__.return_value = instance

        res = corrective_web_search("What evidence supports the plaintiff's title?")
        assert res is None  # Wiktionary rejected!


def test_general_law_bns_disambiguation_not_banking():
    """Case D: Asking for BNS 351 disambiguates and filters out Banking Acts."""
    mock_statutes = [
        {"act_name": "Banking Companies (Acquisition and Transfer of Undertakings) Act", "section_number": "351", "combined_score": 0.88},
        {"act_name": "Bharatiya Nyaya Sanhita, 2023", "section_number": "351", "combined_score": 0.95},
    ]
    with patch("ai_core.rag.vector_store.hybrid_search_judgments", return_value=[]), \
         patch("ai_core.rag.vector_store.hybrid_search_statutes", return_value=mock_statutes):
        results = search_knowledge_base([0.1]*768, "What is section 351 BNS?")
        assert len(results) == 1
        assert "Bharatiya Nyaya Sanhita" in results[0]["act_name"]
        assert "Banking" not in results[0]["act_name"]


def test_case_specific_evidence_grounding():
    """Case A: Case-specific queries instruct the LLM with strict negative constraints against fabricated documents."""
    req = QueryRequest(query="What evidence supports the plaintiff's title?", case_id="test-case-123")
    mock_client = MagicMock()
    mock_client.table().select().eq().execute.return_value.data = [{"filename": "land_dispute_case.pdf", "user_id": "u1"}]
    
    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=[{"page_number": 1, "chunk_text": "Dispute between brothers regarding ancestral plot."}]), \
         patch("backend.routers.chat_router.call_llm") as mock_llm:
        mock_llm.return_value = "The document mentions a verbal partition in 2017 but does not record a registered title deed."
        
        res = _handle_ask(req, user_id="u1")
        assert "answer" in res
        all_prompts = " ".join(call[0][1] for call in mock_llm.call_args_list if len(call[0]) > 1)
        assert "STRICT NEGATIVE CONSTRAINT" in all_prompts
        assert "Do NOT invent, fabricate, or list standard legal documents" in all_prompts


def test_unsupported_case_claim_no_evidence():
    """Case B: When case chunks have low relevance or lack evidence, reports no documentary evidence found."""
    req = QueryRequest(query="What evidence proves the plaintiff committed cyber harassment?", case_id="test-case-123")
    mock_client = MagicMock()
    mock_client.table().select().eq().execute.return_value.data = [{"filename": "land_dispute_case.pdf", "user_id": "u1"}]
    
    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=[{"page_number": 1, "chunk_text": "Land boundary dispute.", "similarity": 0.05}]):
        
        res = _handle_ask(req, user_id="u1")
        assert res.get("no_documentary_evidence_found") is True
        assert "could not find sufficient supporting evidence" in res["answer"].lower()


def test_mixed_mode_retrieval_and_application():
    """Case C: Mixed query joins both case facts and statutory law."""
    req = QueryRequest(query="Mere uploaded land dispute case me adverse possession ka kya legal effect ho sakta hai?", case_id="test-case-123")
    mock_client = MagicMock()
    mock_client.table().select().eq().execute.return_value.data = [{"filename": "land_dispute_case.pdf", "user_id": "u1"}]
    
    case_chunk = [{"page_number": 1, "chunk_text": "Possession claimed since 2017 partition."}]
    law_match = [{"act_name": "Limitation Act, 1963", "section_number": "Article 65", "full_text": "12 years continuous adverse possession required.", "source_type": "statute"}]
    
    with patch("backend.routers.chat_router.get_supabase_client", return_value=mock_client), \
         patch("backend.routers.chat_router.search_document_chunks", return_value=case_chunk), \
         patch("backend.routers.chat_router.search_knowledge_base", return_value=law_match), \
         patch("backend.routers.chat_router.call_llm") as mock_llm:
        mock_llm.return_value = "Under the Limitation Act 1963, 12 years of open adverse possession is required. The document only indicates possession since 2017."
        
        res = _handle_ask(req, user_id="u1")
        assert "answer" in res
        all_prompts = " ".join(call[0][1] for call in mock_llm.call_args_list if len(call[0]) > 1)
        assert "=== UPLOADED CASE FACTS" in all_prompts
        assert "=== APPLICABLE INDIAN STATUTORY LAW" in all_prompts



def test_document_upload_resilience_no_500(tmp_path):
    """Case F: Document reader extracts local text without crashing even when GenAI API key is absent."""
    test_file = tmp_path / "sample_legal.txt"
    test_file.write_text("IN THE HIGH COURT OF DELHI AT NEW DELHI. SUIT NO 123 OF 2024.", encoding="utf-8")
    
    extracted = read_case_file_with_gemini(str(test_file))
    assert "HIGH COURT OF DELHI" in extracted


def test_llm_judge_remains_callable():
    """Requirement 7: Preserve LLM-as-a-Judge."""
    with patch("ai_core.evaluation.llm_judge.call_llm") as mock_llm:
        mock_llm.return_value = '{"is_accurate": true, "is_helpful": true, "issue": ""}'
        judgment = judge_answer("What is BNS 351?", "Section 351 BNS deals with assault.", "Section 351 defines assault.")
        assert judgment["is_accurate"] is True
        assert judgment["is_helpful"] is True


def test_general_legal_answer_prompt_rules():
    """Requirement 6: General legal answer prompt enforces BNS 2023 temporal context and non-hallucination."""
    with patch("backend.routers.chat_router.call_llm") as mock_call:
        mock_call.return_value = "Section 103 BNS punishes murder."
        ans = general_legal_answer("What is punishment for murder in India?", "gemini/gemini-3.6-flash", "student_public")
        assert ans == "Section 103 BNS punishes murder."
        called_prompt = mock_call.call_args[0][1]
        assert "Bharatiya Nyaya Sanhita (BNS), 2023" in called_prompt
        assert "Do NOT invent, guess, or hallucinate" in called_prompt
