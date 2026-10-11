"""CRAG source policy, PII redaction rules, LLM gateway guards and retrieval isolation."""
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

from ai_core import llm_gateway
from ai_core.evaluation.fake_supabase import FakeSupabase
from ai_core.evaluation.rag_suites import build_db, hash_embed
from ai_core.guardrails.output_guard import redact_pii
from ai_core.rag import crag_corrector as crag
from ai_core.rag import vector_store as vs
from tests import sample_docs as S


# ------------------------------------------------------------------ allowlist / source classes

@pytest.mark.parametrize("url,expected", [
    ("https://www.indiacode.nic.in/handle/123456789/2062", "official"),
    ("https://indiacode.nic.in/x", "official"),
    ("https://main.sci.gov.in/judgment", "official"),
    ("https://delhihighcourt.nic.in/orders", "official"),
    ("https://www.livelaw.in/top-stories/x", "secondary"),
    ("https://indiankanoon.org/doc/123/", "secondary"),
    # spoofs the old substring check accepted
    ("https://indiacode.nic.in.evil.example/x", None),
    ("https://evilindiacode.nic.in/x", None),
    ("https://evil.example/?next=https://indiacode.nic.in", None),
    ("https://evil.example/indiacode.nic.in", None),
    ("http://user@indiacode.nic.in.attacker.test/", None),
    # explicitly blocked and unrelated
    ("https://en.wikipedia.org/wiki/Theft", None), ("https://www.quora.com/q", None), ("https://example.com", None),
    ("", None), ("not a url", None),
])
def test_source_class_uses_the_parsed_hostname(url, expected):
    assert crag.source_class(url) == expected
    assert crag.is_allowed_legal_url(url) is (expected is not None)


def test_dictionary_and_off_topic_content_is_filtered():
    assert not crag.is_legally_relevant_content("Bluetooth pairing guide", "troubleshoot your headset")
    assert crag.is_legally_relevant_content("Section 303", "theft is an offence under the Act")


class FakeDDGS:
    """Replaces the web-search client. `script` maps a substring of the query to raw results."""
    instances = []

    def __init__(self, script, timeout=None):
        self.script, self.queries = script, []
        FakeDDGS.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def text(self, query, max_results=5):
        self.queries.append(query)
        for marker, results in self.script:
            if marker in query:
                if isinstance(results, Exception):
                    raise results
                return results
        return []


def run_search(script, query="theft punishment BNS"):
    searches = []

    def factory(timeout=None):
        d = FakeDDGS(script, timeout)
        searches.append(d)
        return d

    with patch.object(crag, "DDGS", side_effect=factory):
        result = crag.corrective_web_search(query)
    return result, [q for d in searches for q in d.queries]


def hit(title, url, body="theft is an offence under the law and court judgment"):
    return {"title": title, "href": url, "body": body}


def test_official_sources_are_found_first_and_stop_the_search():
    result, queries = run_search([("site:indiacode.nic.in", [hit("BNS 2023", "https://www.indiacode.nic.in/bns"),
                                                            hit("Blog", "https://evil.example/theft")])])
    assert len(queries) == 1, "stop widening once an official source was found"
    assert result["has_official_source"] and result["source_links"][0]["source_class"] == "official"
    assert [l["url"] for l in result["source_links"]] == ["https://www.indiacode.nic.in/bns"], "non-allowlisted hits are dropped"
    assert "[Official source: India Code" in result["full_text"] and result["retrieved_on"]


def test_corrective_widening_falls_back_to_secondary_and_labels_it():
    result, queries = run_search([("site:livelaw.in", [hit("Explained", "https://www.livelaw.in/x")])])
    # official sites (empty) -> secondary (hit) -> generic: with no official source yet it keeps looking, within budget
    assert len(queries) == crag.MAX_SEARCHES and "site:indiacode.nic.in" in queries[0] and "site:livelaw.in" in queries[1]
    assert result["has_official_source"] is False
    assert result["source_links"][0]["source_class"] == "secondary" and "not an authority" in result["full_text"]


def test_official_ranks_ahead_of_secondary_in_the_same_result_set():
    result, _ = run_search([("site:indiacode.nic.in", [hit("Commentary", "https://www.livelaw.in/a"), hit("Act", "https://indiacode.nic.in/b")])])
    assert [l["source_class"] for l in result["source_links"]] == ["official", "secondary"]


def test_search_is_bounded_and_returns_none_when_nothing_allowed_is_found():
    result, queries = run_search([("", [hit("Spam", "https://spam.example/x")])])
    assert result is None and len(queries) <= crag.MAX_SEARCHES


def test_search_errors_are_contained():
    result, queries = run_search([("", RuntimeError("network down"))])
    assert result is None and len(queries) == crag.MAX_SEARCHES


def test_identifiers_are_removed_from_outgoing_web_queries():
    _, queries = run_search([], query="my phone 9876543210 aadhaar 2345 6789 0123 mail a@b.org punishment for theft")
    assert queries and all("9876543210" not in q and "2345 6789 0123" not in q and "a@b.org" not in q for q in queries)


# ------------------------------------------------------------------ PII redaction rules

@pytest.mark.parametrize("text,gone", [
    ("call 9876543210 now", "9876543210"), ("+91 98765 43210".replace(" 98765 43210", "-9876543210"), "9876543210"),
    ("Aadhaar 2345 6789 0123", "2345 6789 0123"), ("UID: 234567890123", "234567890123"), ("PAN ABCDE1234F", "ABCDE1234F"),
    ("mail me at name.surname@example.co.in", "name.surname@example.co.in"), ("mobile no: 0123456789", "0123456789"),
    ("Contact - 0221234567", "0221234567"),
])
def test_structured_identifiers_are_redacted(text, gone):
    assert gone not in redact_pii(text) and "REDACTED" in redact_pii(text)


@pytest.mark.parametrize("text", [
    "CNR DLCT010012342019 filed on 12.03.2019", "Case No. 118 of 2019, sale price Rs. 1234567890", "Page 3, paragraph 12",
    "decree dated 30 November 2021 for Rs. 4,50,000", "Account number 1234567890123 of the plaintiff", "Section 138 and Article 21",
    "Exhibit P-1 dated 14 January 2018", "Writ Petition (C) No. 4567/2020",
])
def test_legal_identifiers_and_citations_are_not_destroyed(text):
    assert redact_pii(text) == text


def test_redaction_preserves_meaning_and_page_citations():
    src = "The defendant (mobile 9876543210) deposed at page 3 that the amount of Rs. 4,50,000 was paid on 14.01.2018 [Page 3]."
    out = redact_pii(src)
    assert "[Page 3]" in out and "Rs. 4,50,000" in out and "14.01.2018" in out and "defendant" in out
    assert redact_pii("") == "" and redact_pii(None) is None


def test_the_stored_document_is_not_modified_by_redaction():
    original = S.JUDGMENT_TEXT
    redact_pii(original)
    assert "9876543210" in original and "2345 6789 0123" in original


# ------------------------------------------------------------------ LLM gateway guards

def _completion(text):
    return {"choices": [{"message": {"content": text}}]}


def test_gateway_passes_timeout_and_token_cap(monkeypatch):
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("LLM_MAX_OUTPUT_TOKENS", "321")
    with patch.object(llm_gateway.litellm, "completion", return_value=_completion("ok")) as m:
        assert llm_gateway.call_llm("groq/x", "prompt") == "ok"
    assert m.call_args.kwargs["timeout"] == 7 and m.call_args.kwargs["max_tokens"] == 321


def test_gateway_visits_each_model_at_most_once_then_reports_unavailable(monkeypatch):
    monkeypatch.setattr(llm_gateway.time, "sleep", lambda s: None)
    with patch.object(llm_gateway.litellm, "completion", side_effect=RuntimeError("down")) as m:
        assert llm_gateway.call_llm("gemini/g", "p") == llm_gateway.LLM_UNAVAILABLE_MESSAGE
    models = [c.kwargs["model"] for c in m.call_args_list]
    assert models[0] == "gemini/g" and "openrouter/deepseek/deepseek-r1:free" in models
    assert len(models) == len(set(models)) <= 4, "no model is retried: a request has a bounded provider budget"


def test_gateway_treats_an_empty_reply_as_a_failure_and_falls_through(monkeypatch):
    replies = iter([_completion("   "), _completion("real answer")])
    with patch.object(llm_gateway.litellm, "completion", side_effect=lambda **k: next(replies)):
        assert llm_gateway.call_llm("groq/x", "p2") == "real answer"


def test_unavailable_message_is_never_cached(monkeypatch):
    monkeypatch.setattr(llm_gateway.time, "sleep", lambda s: None)
    with patch.object(llm_gateway.litellm, "completion", side_effect=RuntimeError("down")):
        llm_gateway.call_llm("openrouter/x", "same prompt")
    with patch.object(llm_gateway.litellm, "completion", return_value=_completion("recovered")):
        assert llm_gateway.call_llm("openrouter/x", "same prompt") == "recovered"


# ------------------------------------------------------------------ retrieval isolation (direct)

@pytest.fixture
def two_cases():
    db, ids = build_db({"A": S.JUDGMENT_PAGES, "B": ["Plaintiff Anil Rao ZEBRA-7781 gift deed orchard sale agreement 14 January 2018 amount Rs. 4,50,000 possession."]})
    vs._lex_cache.clear()
    with patch("ai_core.rag.vector_store.get_supabase_client", return_value=db):
        yield db, ids
    vs._lex_cache.clear()


def test_a_vector_function_that_ignores_the_case_filter_cannot_leak_another_case(two_cases):
    db, ids = two_cases
    q = "sale agreement 14 January 2018 amount possession"
    got = vs.search_document_chunks(hash_embed(q), ids["A"], match_count=8, query_text=q)
    assert got and all(c["case_id"] == ids["A"] for c in got)
    assert not any("ZEBRA-7781" in c["chunk_text"] for c in got)
    assert got.diagnostics["attempts"][0]["foreign_dropped"] > 0, "the leaky rows were seen and dropped"


def test_rows_without_a_case_id_are_verified_against_the_table_before_use(two_cases):
    db, ids = two_cases
    leaky = db.rpc_handlers["match_document_chunks"]
    db.rpc_handlers["match_document_chunks"] = lambda p: [{k: v for k, v in r.items() if k != "case_id"} for r in leaky(p)]
    q = "sale agreement possession"
    got = vs.search_document_chunks(hash_embed(q), ids["A"], match_count=8, query_text=q)
    assert got and all(c["case_id"] == ids["A"] for c in got)
    assert not any("ZEBRA-7781" in c["chunk_text"] for c in got)


def test_failing_rpcs_fall_back_to_a_case_scoped_table_scan(two_cases):
    db, ids = two_cases
    db.rpc_handlers = {}
    q = "sale agreement possession"
    got = vs.search_document_chunks(hash_embed(q), ids["A"], match_count=5, query_text=q)
    assert got and got.diagnostics["strategy"] in ("table_scan", "lexical_only") and all(c["case_id"] == ids["A"] for c in got)


def test_without_an_embedding_retrieval_is_lexical_only_and_still_isolated(two_cases):
    db, ids = two_cases
    q = "ZEBRA-7781 gift deed orchard"                                  # words that exist ONLY in case B
    got = vs.search_document_chunks(None, ids["A"], match_count=5, query_text=q)
    assert got.diagnostics["semantic_available"] is False
    assert not any("ZEBRA-7781" in c["chunk_text"] for c in got)
    q2 = "sale agreement 14 January 2018"
    got2 = vs.search_document_chunks(None, ids["A"], match_count=5, query_text=q2)
    assert got2 and all(c["case_id"] == ids["A"] for c in got2) and got2.diagnostics["strategy"] == "lexical_only"


def test_malformed_case_id_returns_nothing_and_never_queries(two_cases):
    db, ids = two_cases
    db.calls.clear()
    got = vs.search_document_chunks(hash_embed("x"), "not-a-uuid'; drop table cases;--", match_count=5, query_text="x")
    assert list(got) == [] and got.diagnostics["error"] == "invalid_case_id" and db.calls == []
