"""
Characterisation tests for behaviour that existed BEFORE this change set. They were run against the untouched code
first; they must keep passing so existing API contracts are preserved.
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ai_core.evaluation.fake_supabase import FakeSupabase
from ai_core.evaluation.llm_judge import (
    STATE_GROUNDED, STATE_PARTIALLY_GROUNDED, STATE_CONTRADICTED, STATE_NO_EVIDENCE_FOUND, STATE_VERIFICATION_PENDING,
)
from ai_core.router.intent_classifier import classify_intent
from ai_core.trustagent.pipeline import verify_and_correct
from backend.auth.supabase_auth import get_current_user
from backend.main import app
from backend.security import clean_uuid, safe_filename, validate_upload

USER_A = SimpleNamespace(id="11111111-1111-1111-1111-111111111111", email="a@example.test")
USER_B = SimpleNamespace(id="22222222-2222-2222-2222-222222222222", email="b@example.test")
CASE_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
SESSION_A = "cccccccc-cccc-cccc-cccc-cccccccccccc"


def _client_as(user, db):
    app.dependency_overrides[get_current_user] = lambda: user
    patchers = [patch("backend.routers.chat_router.get_supabase_client", return_value=db),
                patch("backend.routers.case_router.get_supabase_client", return_value=db),
                patch("backend.routers.document_router.get_supabase_client", return_value=db)]
    for p in patchers:
        p.start()
    return TestClient(app), patchers


@pytest.fixture
def db():
    return FakeSupabase(tables={
        "cases": [{"id": CASE_A, "user_id": USER_A.id, "filename": "a.pdf", "case_text": "x", "status": "ready"}],
        "chat_sessions": [{"id": SESSION_A, "user_id": USER_A.id, "title": "t"}],
        "chat_messages": [{"id": "m1", "session_id": SESSION_A, "role": "user", "content": "secret question"}],
        "document_chunks": [{"id": "ch1", "case_id": CASE_A, "page_number": 1, "chunk_text": "text"}],
    })


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    yield
    app.dependency_overrides.clear()
    patch.stopall()


def test_app_exposes_documented_routes():
    paths = set(app.openapi()["paths"])
    for p in ("/chat/ask", "/document/upload", "/document/{case_id}/status", "/document/{case_id}/reindex",
              "/case/list", "/case/{case_id}", "/health"):
        assert p in paths


def test_protected_routes_require_authentication():
    client = TestClient(app)
    assert client.post("/chat/ask", json={"query": "hi"}).status_code == 401
    assert client.get("/case/list").status_code == 401
    assert client.get(f"/chat/sessions/{SESSION_A}/messages").status_code == 401


def test_other_users_session_and_case_are_indistinguishable_from_missing(db):
    client, _ = _client_as(USER_B, db)
    r = client.get(f"/chat/sessions/{SESSION_A}/messages")
    assert r.status_code == 404
    assert client.get(f"/case/{CASE_A}").status_code == 404
    assert client.delete(f"/case/{CASE_A}").status_code == 404
    assert client.delete(f"/document/{CASE_A}").status_code == 404
    assert client.get(f"/document/{CASE_A}/status").status_code == 404
    assert any(c["id"] == CASE_A for c in db.rows("cases")), "foreign delete must not remove the case"
    assert db.rows("document_chunks"), "foreign delete must not remove the chunks"


def test_owner_can_read_own_session(db):
    client, _ = _client_as(USER_A, db)
    r = client.get(f"/chat/sessions/{SESSION_A}/messages")
    assert r.status_code == 200 and r.json()["messages"][0]["content"] == "secret question"


def test_security_helpers():
    assert clean_uuid(CASE_A.upper()) == CASE_A
    with pytest.raises(Exception):
        clean_uuid("not-a-uuid")
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("a b(1).pdf") == "a b(1).pdf"
    with pytest.raises(Exception) as e:
        validate_upload("x.exe", b"abc")
    assert e.value.status_code == 415
    with pytest.raises(Exception) as e:
        validate_upload("x.pdf", b"")
    assert e.value.status_code == 400
    # (changed deliberately: a bare "%PDF-1.4 ..." stub is now rejected as corrupt, so use a real one-page PDF)
    import io
    from pypdf import PdfWriter
    writer, buf = PdfWriter(), io.BytesIO()
    writer.add_blank_page(width=200, height=200)
    writer.write(buf)
    assert validate_upload("x.pdf", buf.getvalue()) == ".pdf"


@pytest.mark.parametrize("query,has_doc,expected", [
    ("What is BNS Section 351?", True, "GENERAL_LAW"),
    ("What evidence did the plaintiff rely on?", True, "CASE_SPECIFIC"),
    ("give me a recipe for cake", False, "OUT_OF_DOMAIN"),
    ("what does section 303 BNS say and what did the court hold in this case", True, "MIXED"),
])
def test_intent_routing_rules(query, has_doc, expected):
    with patch("ai_core.router.intent_classifier.call_llm", side_effect=AssertionError("no LLM expected")):
        assert classify_intent(query, has_doc)["label"] == expected


def _verify(draft, verdicts, ok=True, evidence="ev", pages=frozenset({1})):
    claims = [v["claim"] for v in verdicts]

    def judge(**kw):
        sup = [v["claim"] for v in verdicts if v["verdict"] in ("SUPPORTED", "PARTIALLY_SUPPORTED")]
        uns = [v["claim"] for v in verdicts if v["verdict"] not in ("SUPPORTED", "PARTIALLY_SUPPORTED")]
        vals = [v["verdict"] for v in verdicts]
        overall = (STATE_GROUNDED if all(x == "SUPPORTED" for x in vals) else STATE_CONTRADICTED if all(x == "CONTRADICTED" for x in vals)
                   else STATE_PARTIALLY_GROUNDED if sup else STATE_NO_EVIDENCE_FOUND)
        return {"claim_verdicts": verdicts, "overall_verdict": overall, "supported_claims": sup, "unsupported_claims": uns,
                "is_accurate": True, "issue": ""}
    return verify_and_correct(query="q", draft=draft, evidence=evidence, retrieved_pages=set(pages),
                              extract=lambda t: (claims, ok), judge=judge, correct=lambda *a: "rewritten")


def test_pipeline_grounded():
    r = _verify("A [Page 1]", [{"claim": "A", "verdict": "SUPPORTED", "page_numbers": [1]}])
    assert r.verdict_state == STATE_GROUNDED and r.verified


def test_pipeline_extraction_failure_is_pending_never_verified():
    r = _verify("A", [], ok=False)
    assert r.verdict_state == STATE_VERIFICATION_PENDING and not r.verified


def test_pipeline_contradicted_withholds_answer():
    r = _verify("A", [{"claim": "A", "verdict": "CONTRADICTED", "page_numbers": []}])
    assert r.verdict_state == STATE_CONTRADICTED and r.answer != "A"


def test_pipeline_removes_unsupported_claims_and_reverifies():
    r = _verify("A. B.", [{"claim": "A", "verdict": "SUPPORTED", "page_numbers": [1]},
                          {"claim": "B", "verdict": "NOT_VERIFIABLE", "page_numbers": []}])
    assert r.corrected and r.removed_claims == ["B"] and r.reverified is True
