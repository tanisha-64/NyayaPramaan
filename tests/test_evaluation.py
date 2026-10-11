"""The reproducible evaluation: datasets are well-formed, the harness is deterministic, and the regression gates hold."""
import json
from pathlib import Path

import pytest

from ai_core.evaluation import rag_eval, routing_eval, judge_eval
from ai_core.router.intent_classifier import classify_intent
from unittest.mock import patch

GOLDEN = Path(rag_eval.ROOT) / "eval" / "golden"


def load(name):
    return json.loads((GOLDEN / name).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ datasets are internally consistent

def test_land_dispute_dataset_is_consistent():
    d = load("land_dispute_v1.json")
    n = len(d["pages"])
    ids = [q["id"] for q in d["questions"]]
    assert len(ids) == len(set(ids))
    for q in d["questions"]:
        if q["answerable"]:
            assert q["expected_pages"] and all(1 <= p <= n for p in q["expected_pages"]), q["id"]
    assert {q["category"] for q in d["questions"]} >= {"fact", "paraphrase", "short", "hinglish", "multi-page", "unanswerable"}
    for c in d["candidate_answers"]:
        assert c["question_id"] in ids and c["kind"] in ("good", "wrong_page", "hallucinated")
    assert {c["kind"] for c in d["candidate_answers"]} == {"good", "wrong_page", "hallucinated"}
    for f in d["followups"]:
        assert f["history"] and f["standalone"] and all(1 <= p <= n for p in f["expected_pages"])
    assert [q for q in d["questions"] if not q["answerable"] and q.get("hard_negative")], "hard negatives must be present"


def test_every_timeline_label_really_occurs_on_its_page():
    d = load("land_dispute_v1.json")
    for t in d["timeline"]:
        assert t["date"] in d["pages"][t["page"] - 1], t


def test_distractor_markers_exist_only_in_the_distractor():
    a, b = load("land_dispute_v1.json"), load("land_dispute_b_v1.json")
    text_a, text_b = " ".join(a["pages"]).lower(), " ".join(b["pages"]).lower()
    for m in b["unique_markers"]:
        assert m.lower() in text_b and m.lower() not in text_a, m


def test_judge_labels_cover_all_four_verdicts_and_state_their_limits():
    d = load("judge_labels_v1.json")
    assert {i["gold"] for i in d["items"]} == set(judge_eval.VERDICTS)
    assert "not a lawyer" in d["_meta"]["annotator"].lower() and "too few" in d["_meta"]["caution"].lower()
    ids = [i["id"] for i in d["items"]]
    assert len(ids) == len(set(ids)) == d["_meta"]["items"]


def test_general_law_dataset_asserts_no_unverified_legal_answers():
    d = load("general_law_v1.json")
    assert "NO gold answer texts" in d["description"]
    assert {r["expected"] for r in d["routing"]} == {"GENERAL_LAW", "CASE_SPECIFIC", "MIXED", "OUT_OF_DOMAIN"}


# ------------------------------------------------------------------ the harness is deterministic and the gates hold

@pytest.fixture(scope="module")
def rag_report():
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        return rag_eval.evaluate_all(rag_eval.load_dataset(), k=3)


def test_rag_evaluation_is_reproducible(rag_report):
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        again = rag_eval.evaluate_all(rag_eval.load_dataset(), k=3)
    assert json.dumps(again, sort_keys=True, default=str) == json.dumps(rag_report, sort_keys=True, default=str)
    assert rag_report["dataset_sha256"] == again["dataset_sha256"]


def test_rag_regression_gates_hold(rag_report):
    thresholds = json.loads(rag_eval.DEFAULT_THRESHOLDS.read_text(encoding="utf-8"))
    assert rag_eval.check_thresholds(rag_report, thresholds) == []


def test_report_covers_the_requested_metrics(rag_report):
    for key in ("recall@3", "hit@3", "mrr", "ndcg@3"):
        assert key in rag_report["retrieval"]
    assert {"correct_abstention_rate", "false_abstention_rate"} <= set(rag_report["abstention"])
    assert {"good_answers_f1", "good_answers_invalid_rate"} <= set(rag_report["citations"])
    assert "cross_case_chunk_rate" in rag_report["leakage"]
    assert "rpc_unavailable_recall@3" in rag_report["failure_modes"] and "no_query_embedding_recall@3" in rag_report["failure_modes"]


def test_a_regression_in_isolation_would_be_caught_by_the_gate(rag_report):
    broken = json.loads(json.dumps(rag_report, default=str))
    broken["leakage"]["cross_case_chunk_rate"] = 0.05
    thresholds = json.loads(rag_eval.DEFAULT_THRESHOLDS.read_text(encoding="utf-8"))
    assert any("cross_case_chunk_rate" in f for f in rag_eval.check_thresholds(broken, thresholds))


def test_routing_policy_and_timeline_gates_hold():
    report = routing_eval.evaluate_all()
    thresholds = json.loads(routing_eval.THRESHOLDS.read_text(encoding="utf-8"))
    assert routing_eval.check_thresholds(report, thresholds) == []
    assert report["routing"]["llm_calls_needed"] == 0, "the benchmark questions are routed by rules, not by an LLM"


def test_judge_baseline_runs_offline_and_is_labelled_as_a_baseline():
    items = judge_eval.load_labels()
    report = judge_eval.evaluate_judge(items, judge_eval.lexical_baseline_judge)
    assert report["items"] == 25 and 0 <= report["accuracy"] <= 1 and report["unavailable_rate"] == 0


# ------------------------------------------------------------------ regressions found by the evaluation

def test_adverse_possession_question_is_not_pulled_into_the_open_document():
    with patch("ai_core.router.intent_classifier.call_llm", side_effect=AssertionError("no LLM expected")):
        assert classify_intent("Explain adverse possession in Indian law", True)["label"] == "GENERAL_LAW"
        # but a question that is ALSO about the document's parties is still mixed / document-bound
        assert classify_intent("Did the plaintiff prove adverse possession?", True)["label"] == "MIXED"
