"""Authentication, ownership (case / document / session isolation), roles, quotas and request limits."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ai_core.evaluation.fake_supabase import FakeSupabase
from backend.auth.supabase_auth import get_user_effective_role, require_role
from backend.main import app
from tests import sample_docs as S
from tests.helpers import USER_A, USER_B, ScriptedLLM, signed_in

CASE_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
CASE_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
SESSION_A = "cccccccc-cccc-cccc-cccc-cccccccccccc"
SESSION_B = "dddddddd-dddd-dddd-dddd-dddddddddddd"


@pytest.fixture
def db():
    return FakeSupabase(tables={
        "cases": [
            {"id": CASE_A, "user_id": USER_A.id, "filename": "a.pdf", "case_text": S.JUDGMENT_TEXT, "status": "ready",
             "summary": "s", "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": CASE_B, "user_id": USER_B.id, "filename": "b.pdf", "case_text": "b text", "status": "ready", "summary": "sb"},
        ],
        "document_chunks": [{"id": "ca", "case_id": CASE_A, "page_number": 1, "chunk_text": "a"},
                            {"id": "cb", "case_id": CASE_B, "page_number": 1, "chunk_text": "b"}],
        "chat_sessions": [{"id": SESSION_A, "user_id": USER_A.id, "title": "A's chat"},
                          {"id": SESSION_B, "user_id": USER_B.id, "title": "B's chat"}],
        "chat_messages": [{"session_id": SESSION_A, "role": "user", "content": "a msg"},
                          {"session_id": SESSION_B, "role": "user", "content": "b msg"}],
        "session_documents": [{"session_id": SESSION_B, "case_id": CASE_B}],
    })


# ------------------------------------------------------------------ every protected route needs a token

def test_every_protected_route_rejects_anonymous_requests():
    client = TestClient(app)
    public = ("/health", "/docs", "/openapi.json", "/redoc", "/quiz", "/news", "/game")
    checked = 0
    for path, methods in app.openapi()["paths"].items():
        if path.startswith(public):
            continue
        for method in methods:
            url = path.replace("{case_id}", CASE_A).replace("{session_id}", SESSION_A)
            r = client.request(method.upper(), url, json={} if method in ("post", "put", "patch") else None)
            assert r.status_code == 401, f"{method.upper()} {path} answered {r.status_code} without a token"
            checked += 1
    assert checked >= 15


def test_invalid_token_is_rejected():
    with patch("backend.auth.supabase_auth.get_client") as gc:
        gc.return_value.auth.get_user.side_effect = RuntimeError("bad jwt")
        r = TestClient(app).get("/case/list", headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 401


# ------------------------------------------------------------------ ownership: cases and documents

def test_users_only_see_their_own_cases(db):
    with signed_in(USER_A, db) as c:
        listed = c.get("/case/list").json()
    assert [x["id"] for x in listed] == [CASE_A]


def test_foreign_case_operations_look_exactly_like_missing_ones(db):
    with signed_in(USER_A, db) as c:
        missing = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
        for call in (lambda i: c.get(f"/case/{i}"), lambda i: c.get(f"/case/{i}/brief"), lambda i: c.delete(f"/case/{i}"),
                     lambda i: c.put(f"/case/{i}/notes", json={"notes": "x"}), lambda i: c.get(f"/document/{i}/status"),
                     lambda i: c.post(f"/document/{i}/reindex"), lambda i: c.delete(f"/document/{i}")):
            foreign, absent = call(CASE_B), call(missing)
            assert foreign.status_code == absent.status_code == 404
            assert foreign.json() == absent.json(), "a foreign id must not be distinguishable from a missing one"
    assert {r["id"] for r in db.rows("cases")} == {CASE_A, CASE_B}
    assert {r["id"] for r in db.rows("document_chunks")} == {"ca", "cb"}
    assert db.rows("session_documents"), "foreign deletes must not touch the other user's session links"


def test_malformed_ids_are_404_not_500(db):
    with signed_in(USER_A, db) as c:
        for bad in ("not-a-uuid", "1' OR '1'='1", "..%2f..%2fetc", "0" * 10):
            assert c.get(f"/case/{bad}").status_code == 404
            assert c.get(f"/document/{bad}/status").status_code == 404


def test_deleting_own_case_removes_its_chunks_only(db):
    with signed_in(USER_A, db) as c:
        assert c.delete(f"/case/{CASE_A}").status_code == 200
    assert {r["id"] for r in db.rows("cases")} == {CASE_B}
    assert {r["id"] for r in db.rows("document_chunks")} == {"cb"}


def test_clear_all_only_clears_the_callers_cases(db):
    with signed_in(USER_A, db) as c:
        assert c.delete("/case/clear/all").json()["cleared_count"] == 1
    assert {r["id"] for r in db.rows("cases")} == {CASE_B} and {r["id"] for r in db.rows("document_chunks")} == {"cb"}


def test_notes_are_written_only_to_the_owners_case(db):
    with signed_in(USER_B, db) as c:
        assert c.put(f"/case/{CASE_A}/notes", json={"notes": "overwrite"}).status_code == 404
    assert db.rows("cases")[0].get("notes") is None


# ------------------------------------------------------------------ ownership: chat sessions

def test_foreign_sessions_cannot_be_read_renamed_or_deleted(db):
    with signed_in(USER_A, db) as c:
        assert c.get(f"/chat/sessions/{SESSION_B}/messages").status_code == 404
        c.patch(f"/chat/sessions/{SESSION_B}", json={"title": "hijacked", "pinned": True})
        c.delete(f"/chat/sessions/{SESSION_B}")
    session_b = next(s for s in db.rows("chat_sessions") if s["id"] == SESSION_B)
    assert session_b["title"] == "B's chat" and "pinned" not in session_b
    assert any(s["id"] == SESSION_B for s in db.rows("chat_sessions"))


def test_session_list_contains_only_own_sessions(db):
    with signed_in(USER_A, db) as c:
        assert [s["id"] for s in c.get("/chat/sessions").json()] == [SESSION_A]


# ------------------------------------------------------------------ status endpoint

def test_status_reports_partial_indexing_honestly(db):
    db.rows("cases")[0]["index_report"] = {"complete": False, "pages_indexed": 2, "pages_with_text": 4, "failed_pages": [3, 4]}
    db.rows("cases")[0]["timeline"] = "- 12 March 2019 -- Filing: x (Page 1)"
    with signed_in(USER_A, db) as c:
        body = c.get(f"/document/{CASE_A}/status").json()
    assert body["status"] == "ready" and body["indexing_complete"] is False
    assert "Only 2 of 4 pages" in body["index_warning"] and body["timeline"].startswith("- 12 March 2019")


def test_status_of_a_complete_index_has_no_warning(db):
    db.rows("cases")[0]["index_report"] = {"complete": True, "pages_indexed": 4, "pages_with_text": 4}
    with signed_in(USER_A, db) as c:
        body = c.get(f"/document/{CASE_A}/status").json()
    assert body["indexing_complete"] is True and "index_warning" not in body


def test_a_stuck_processing_document_is_reported_failed(db):
    old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    db.rows("cases")[0].update(status="processing", created_at=old)
    with signed_in(USER_A, db) as c:
        body = c.get(f"/document/{CASE_A}/status").json()
    assert body["status"] == "failed" and "did not finish" in body["rejection_reason"]


# ------------------------------------------------------------------ roles

def _user(email="x@example.test", confirmed=True, meta=None):
    return SimpleNamespace(email=email, email_confirmed_at="2026-01-01" if confirmed else None, user_metadata=meta or {})


def test_admin_role_requires_whitelisted_and_confirmed_email():
    assert get_user_effective_role(_user("admin@example.test")) == "admin"
    assert get_user_effective_role(_user("admin@example.test", confirmed=False)) == "public"
    assert get_user_effective_role(_user("someone@example.test", meta={"role": "admin"})) == "public", "user_metadata can never grant admin"
    assert get_user_effective_role(_user("someone@example.test", meta={"role": "professional"})) == "professional"
    with pytest.raises(Exception) as e:
        require_role(_user("someone@example.test"), ["admin"])
    assert e.value.status_code == 403


def test_admin_routes_are_forbidden_to_ordinary_users(db):
    with signed_in(USER_A, db) as c:
        assert c.get("/admin/metrics").status_code == 403
        assert c.get("/admin/judgments-count").status_code == 403


# ------------------------------------------------------------------ limits

def test_upload_quota_is_enforced(db, monkeypatch):
    from tests.helpers import make_pdf
    monkeypatch.setenv("MAX_CASES_PER_USER", "1")
    patches = [patch("backend.routers.document_router.read_case_file_with_gemini", return_value=S.JUDGMENT_TEXT)]
    with signed_in(USER_A, db, patches) as c:
        r = c.post("/document/upload", files={"file": ("a.pdf", make_pdf(), "application/pdf")})
    assert r.status_code == 429 and "limit" in r.json()["detail"].lower()


def test_upload_rate_limit(db, monkeypatch):
    from tests.helpers import make_pdf
    monkeypatch.setenv("RATE_LIMIT_UPLOAD_PER_HOUR", "2")
    with signed_in(USER_A, db) as c:
        codes = [c.post("/document/upload", files={"file": ("a.exe", b"x", "application/octet-stream")}).status_code for _ in range(3)]
    assert codes[:2] == [415, 415] and codes[2] == 429


def test_search_payload_is_bounded(db):
    with signed_in(USER_A, db) as c:
        assert c.post("/search/precedents", json={"query": ""}).status_code == 422
        assert c.post("/search/precedents", json={"query": "x" * 1001}).status_code == 422
        assert c.post("/search/precedents", json={"query": "theft", "match_count": 51}).status_code == 422
        assert c.post("/search/precedents", json={"query": "theft", "match_count": 0}).status_code == 422


def test_brief_is_rate_limited_and_redacts_identifiers_before_the_llm(db, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_BRIEF_PER_MIN", "2")
    monkeypatch.setattr("ai_core.llm_gateway.time.sleep", lambda s: None)
    llm = ScriptedLLM([("senior Indian High Court advocate", "# CASE BRIEF: x")])
    patches = [patch("ai_core.llm_gateway.litellm.completion", side_effect=lambda **kw: llm(**kw))]
    with signed_in(USER_A, db, patches) as c:
        r1 = c.get(f"/case/{CASE_A}/brief")
        c.get(f"/case/{CASE_A}/brief")
        r3 = c.get(f"/case/{CASE_A}/brief")
    assert r1.status_code == 200 and r3.status_code == 429
    assert llm.prompts and all("9876543210" not in p and "2345 6789 0123" not in p for p in llm.prompts)
    assert any("[REDACTED_PHONE]" in p for p in llm.prompts)
