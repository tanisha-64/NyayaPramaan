"""TrustAgent claim extraction / judging / correction, Self-RAG control and citation checks (LLM calls scripted)."""
import json
from unittest.mock import patch

from ai_core.evaluation import llm_judge as lj
from ai_core.evaluation.llm_judge import STATE_GROUNDED, STATE_PARTIALLY_GROUNDED, STATE_CONTRADICTED, STATE_NO_EVIDENCE_FOUND, STATE_VERIFICATION_PENDING
from ai_core.rag.self_rag import should_retry_retrieval, is_better, retrieve_for_claims
from ai_core.trustagent import claim_extractor as ce
from ai_core.trustagent.citations import check_citations, strip_invalid_bracket_citations, ungrounded_specifics
from ai_core.trustagent.pipeline import verify_and_correct, build_document_sources

EVIDENCE = "[Chunk #1 (Page 2)]\nThe plaintiff relied on a sale agreement dated 14 January 2018."


def judge_replying(verdicts, accurate=True):
    reply = json.dumps({"claim_verdicts": [{"claim": "c", "verdict": v, "evidence_ids": ["1"], "page_numbers": p, "reason": "r"}
                                           for v, p in verdicts], "is_accurate": accurate, "issue": ""})
    return patch.object(lj, "call_llm", return_value=reply)


# ------------------------------------------------------------------ claim extraction

def test_table_rows_are_flattened_into_claims_not_deleted():
    answer = "Evidence found:\n\n| Item | Detail |\n|---|---|\n| Sale agreement | dated 14 January 2018, Page 2 |\n| Receipt | Rs. 1,00,000 |\n"
    flat = ce.flatten_markdown(answer)
    assert "Sale agreement; dated 14 January 2018, Page 2." in flat and "Receipt; Rs. 1,00,000." in flat
    assert "---" not in flat and "|" not in flat


def test_extraction_prompt_contains_the_table_content():
    seen = {}
    with patch.object(ce, "call_llm", side_effect=lambda m, p: seen.setdefault("p", p) and '["a claim"]'):
        claims, ok = ce.extract_claims("| Item | Detail |\n|---|---|\n| Receipt | Rs. 1,00,000 |")
    assert ok and claims == ["a claim"] and "Receipt; Rs. 1,00,000." in seen["p"]


def test_extraction_failure_is_distinct_from_zero_claims():
    with patch.object(ce, "call_llm", return_value="not json"):
        assert ce.extract_claims("answer") == ([], False)
    with patch.object(ce, "call_llm", return_value="[]"):
        assert ce.extract_claims("answer") == ([], True)


def test_hitting_the_claim_cap_is_visible_in_the_summary():
    claims = [f"claim {i}" for i in range(ce.MAX_CLAIMS)]
    r = verify_and_correct(query="q", draft="long answer", evidence=EVIDENCE, retrieved_pages={2},
                           extract=lambda t: (claims, True),
                           judge=lambda **kw: {"claim_verdicts": [{"claim": c, "verdict": "SUPPORTED", "page_numbers": [2]} for c in claims],
                                               "overall_verdict": STATE_GROUNDED, "supported_claims": claims, "unsupported_claims": [],
                                               "is_accurate": True, "issue": ""},
                           correct=lambda *a: "")
    assert r.summary["claims_capped"] is True and r.verdict_state == STATE_GROUNDED


# ------------------------------------------------------------------ the judge

def test_judge_verdicts_map_to_overall_states():
    claims = ["a", "b"]
    for verdicts, expected in [([("SUPPORTED", [2]), ("SUPPORTED", [2])], STATE_GROUNDED),
                               ([("SUPPORTED", [2]), ("NOT_VERIFIABLE", [])], STATE_PARTIALLY_GROUNDED),
                               ([("CONTRADICTED", []), ("CONTRADICTED", [])], STATE_CONTRADICTED),
                               ([("NOT_VERIFIABLE", []), ("NOT_VERIFIABLE", [])], STATE_NO_EVIDENCE_FOUND),
                               ([("SUPPORTED", [2]), ("CONTRADICTED", [])], STATE_PARTIALLY_GROUNDED)]:
        with judge_replying(verdicts):
            assert lj.judge_claims_against_evidence("q", EVIDENCE, "draft", claims)["overall_verdict"] == expected


def test_missing_verdicts_are_unverified_never_assumed_supported():
    with judge_replying([("SUPPORTED", [2])]):                              # 1 verdict for 2 claims
        j = lj.judge_claims_against_evidence("q", EVIDENCE, "draft", ["a", "b"])
    assert [v["verdict"] for v in j["claim_verdicts"]] == ["SUPPORTED", "NOT_VERIFIABLE"]
    assert j["overall_verdict"] == STATE_PARTIALLY_GROUNDED


def test_a_reply_that_just_says_accurate_is_not_a_verification():
    reply = json.dumps({"is_accurate": True, "issue": ""})
    with patch.object(lj, "call_llm", return_value=reply):
        j = lj.judge_claims_against_evidence("q", EVIDENCE, "draft", ["a"])
    assert j["overall_verdict"] == STATE_VERIFICATION_PENDING and j["claim_verdicts"] == []


def test_judge_retries_are_bounded_and_failure_is_pending():
    with patch.object(lj, "call_llm", return_value="garbage") as m:
        j = lj.judge_claims_against_evidence("q", EVIDENCE, "draft", ["a"])
    assert m.call_count == lj.JUDGE_ATTEMPTS and j["overall_verdict"] == STATE_VERIFICATION_PENDING


def test_judge_cannot_cite_pages_that_were_not_retrieved():
    r = verify_and_correct(query="q", draft="A [Page 2]", evidence=EVIDENCE, retrieved_pages={2},
                           extract=lambda t: (["A"], True),
                           judge=lambda **kw: {"claim_verdicts": [{"claim": "A", "verdict": "SUPPORTED", "page_numbers": [2, 99]}],
                                               "overall_verdict": STATE_GROUNDED, "supported_claims": ["A"], "unsupported_claims": [],
                                               "is_accurate": True, "issue": ""},
                           correct=lambda *a: "")
    assert r.claim_verdicts[0]["page_numbers"] == [2]


# ------------------------------------------------------------------ correction + re-verification

def _verdicts(mapping):
    def judge(query, evidence, draft_answer, claims):
        vs = [{"claim": c, "verdict": mapping.get(c, "NOT_VERIFIABLE"), "page_numbers": [2] if mapping.get(c) == "SUPPORTED" else []} for c in claims]
        sup = [v["claim"] for v in vs if v["verdict"] in ("SUPPORTED", "PARTIALLY_SUPPORTED")]
        uns = [v["claim"] for v in vs if v["verdict"] not in ("SUPPORTED", "PARTIALLY_SUPPORTED")]
        state = (STATE_GROUNDED if not uns else STATE_PARTIALLY_GROUNDED if sup
                 else STATE_CONTRADICTED if all(v["verdict"] == "CONTRADICTED" for v in vs) else STATE_NO_EVIDENCE_FOUND)
        return {"claim_verdicts": vs, "overall_verdict": state, "supported_claims": sup, "unsupported_claims": uns, "is_accurate": True, "issue": ""}
    return judge


def test_corrected_answer_is_reverified_and_a_failed_rewrite_falls_back_to_supported_claims():
    mapping = {"A": "SUPPORTED", "B": "NOT_VERIFIABLE"}
    extract = lambda t: (["A", "B"] if "B" in t else ["A"], True)

    good = verify_and_correct(query="q", draft="A and B", evidence=EVIDENCE, retrieved_pages={2}, extract=extract,
                              judge=_verdicts(mapping), correct=lambda *a: "A only")
    assert good.corrected and good.reverified and good.correction_method == "llm_rewrite" and good.answer == "A only"

    bad = verify_and_correct(query="q", draft="A and B", evidence=EVIDENCE, retrieved_pages={2}, extract=extract,
                             judge=_verdicts(mapping), correct=lambda *a: "A and B again")      # rewrite still contains B
    assert bad.correction_method == "supported_claims_only" and "- A" in bad.answer and "B" not in bad.answer.replace("Based", "")

    broken = verify_and_correct(query="q", draft="A and B", evidence=EVIDENCE, retrieved_pages={2}, extract=extract,
                                judge=_verdicts(mapping), correct=lambda *a: (_ for _ in ()).throw(RuntimeError("llm down")))
    assert broken.correction_method == "supported_claims_only" and "B" not in broken.answer.replace("Based", "")


def test_contradicted_answers_are_withheld_and_refusals_are_not_verified():
    r = verify_and_correct(query="q", draft="A", evidence=EVIDENCE, retrieved_pages={2}, extract=lambda t: (["A"], True),
                           judge=_verdicts({"A": "CONTRADICTED"}), correct=lambda *a: "")
    assert r.verdict_state == STATE_CONTRADICTED and "withheld" in r.answer and not r.verified
    refusal = verify_and_correct(query="q", draft="No supporting evidence was found in the uploaded document regarding x.",
                                 evidence=EVIDENCE, retrieved_pages={2}, extract=lambda t: (_ for _ in ()).throw(AssertionError("no LLM")),
                                 judge=None, correct=None)
    assert refusal.verdict_state == STATE_NO_EVIDENCE_FOUND and not refusal.verified


def test_the_only_number_reported_is_a_documented_ratio_not_a_probability():
    r = verify_and_correct(query="q", draft="A. B. C.", evidence=EVIDENCE, retrieved_pages={2}, extract=lambda t: (["A", "B", "C"], True),
                           judge=lambda **kw: {"claim_verdicts": [{"claim": "A", "verdict": "SUPPORTED", "page_numbers": [2]},
                                                                  {"claim": "B", "verdict": "PARTIALLY_SUPPORTED", "page_numbers": [2]},
                                                                  {"claim": "C", "verdict": "SUPPORTED", "page_numbers": [2]}],
                                               "overall_verdict": STATE_PARTIALLY_GROUNDED, "supported_claims": ["A", "B", "C"],
                                               "unsupported_claims": [], "is_accurate": True, "issue": ""},
                           correct=lambda *a: "")
    assert r.summary["claim_support_ratio"] == 0.833                      # (2 + 0.5) / 3
    assert "not the probability" in r.summary["method"]
    assert not any("confidence" in k or "probab" in k for k in r.summary)


# ------------------------------------------------------------------ citations and sources

def test_citation_checks():
    assert check_citations("See [Page 2] and pages 3-4, p. 9", {2, 3})["invalid"] == [4, 9]
    assert strip_invalid_bracket_citations("Fact [Page 9]. Other [Page 2].", [9]) == "Fact. Other [Page 2]."
    assert ungrounded_specifics("Decreed on 30 November 2021 for Rs. 9,99,999 under Section 420", "decreed on 30 November 2021") == ["Rs. 9,99,999", "Section 420"]


def test_cited_page_without_a_claim_attributed_to_it_is_flagged_not_deleted():
    r = verify_and_correct(query="q", draft="A [Page 2]. Also see [Page 3].", evidence=EVIDENCE, retrieved_pages={2, 3},
                           extract=lambda t: (["A"], True), judge=_verdicts({"A": "SUPPORTED"}), correct=lambda *a: "")
    assert r.citations["not_backed"] == [3] and "[Page 3]" in r.answer


def test_sources_expose_document_page_paragraph_and_excerpt_from_chunks_only():
    chunks = [{"page_number": 2, "chunk_text": "5. PW-1 deposed about the sale agreement.\n6. PW-2 stated that he saw the plaintiff."},
              {"page_number": 2, "chunk_text": "7. Exhibit P-1 is the sale agreement."}, {"page_number": 4, "chunk_text": "no markers here at all"}]
    r = verify_and_correct(query="q", draft="A [Page 2]", evidence=EVIDENCE, retrieved_pages={2, 4}, extract=lambda t: (["A"], True),
                           judge=_verdicts({"A": "SUPPORTED"}), correct=lambda *a: "")
    sources = build_document_sources("case.pdf", chunks, r, "verified", pages_estimated=False)
    assert [s["page_number"] for s in sources] == [2, 4]
    assert sources[0]["document"] == "case.pdf" and sources[0]["paragraphs"] == [5, 6, 7] and "PW-1 deposed" in sources[0]["snippet"]
    assert sources[1]["paragraphs"] == [], "no paragraph number is invented"


# ------------------------------------------------------------------ Self-RAG control

def test_self_rag_retry_policy_is_bounded():
    assert should_retry_retrieval("PARTIALLY_GROUNDED", ["x"], False)
    assert not should_retry_retrieval("PARTIALLY_GROUNDED", ["x"], True), "never a second retry"
    assert not should_retry_retrieval("GROUNDED", ["x"], False) and not should_retry_retrieval("CONTRADICTED", ["x"], False)
    assert not should_retry_retrieval("PARTIALLY_GROUNDED", [], False)


def test_regenerated_answer_replaces_the_first_only_if_strictly_better():
    assert is_better("GROUNDED", "PARTIALLY_GROUNDED") and not is_better("PARTIALLY_GROUNDED", "PARTIALLY_GROUNDED")
    assert is_better("PARTIALLY_GROUNDED", "PARTIALLY_GROUNDED", new_removed=0, old_removed=2)
    assert not is_better("NO_EVIDENCE_FOUND", "PARTIALLY_GROUNDED")


def test_claim_retrieval_only_returns_new_relevant_chunks_of_the_selected_case():
    calls = []

    def search(q, k):
        calls.append(q)
        return [{"id": "1", "chunk_text": "seen", "lexical_coverage": 1.0}, {"id": "2", "chunk_text": "new", "lexical_coverage": 0.9},
                {"id": "3", "chunk_text": "weak", "lexical_coverage": 0.1}, {"id": None, "chunk_text": "noid", "lexical_coverage": 1.0}]

    out = retrieve_for_claims(["c1", "c2", "c3", "c4", "c5"], search, {"1"})
    assert [c["id"] for c in out] == ["2"] and len(calls) <= 3, "at most 3 claim queries"
