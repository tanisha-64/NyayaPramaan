"""
Evaluation of the claim-level judge against hand-labelled (claim, evidence) pairs
(eval/golden/judge_labels_v1.json: 25 pairs, one annotator, no inter-annotator agreement).

Scoring criteria (explicit):
  accuracy / macro-F1 / Cohen's kappa over the 4 verdicts SUPPORTED, PARTIALLY_SUPPORTED, CONTRADICTED, NOT_VERIFIABLE
  unsafe_support_rate   share of items whose gold verdict is CONTRADICTED or NOT_VERIFIABLE that the judge called
                        SUPPORTED or PARTIALLY_SUPPORTED. This is the dangerous error (an unsupported claim passes).
  missed_support_rate   share of gold SUPPORTED items the judge refused (over-caution; costs completeness)
  unavailable_rate      judge produced no verdict (counted as wrong, never as correct)

Modes
  default (CI, offline)  a deterministic LEXICAL BASELINE judge. It exercises the metrics and sets a floor; it is not
                         the production judge and its numbers say nothing about LLM quality.
  --live                 the production judge (llm_judge.judge_claims_against_evidence) via the configured providers.
                         Needs API keys and network; NOT run in CI and NOT run during development of this change, so
                         no LLM-judge accuracy figure exists yet. Run it on staging and record the output.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from ai_core.rag.lexical import tokens

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LABELS = ROOT / "eval" / "golden" / "judge_labels_v1.json"

VERDICTS = ("SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED", "NOT_VERIFIABLE")
_SUPPORTING = {"SUPPORTED", "PARTIALLY_SUPPORTED"}
_UNSUPPORTED_GOLD = {"CONTRADICTED", "NOT_VERIFIABLE"}


def load_labels(path: Path | str = DEFAULT_LABELS) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["items"]


def _kappa(gold: list[str], pred: list[str | None]) -> float | None:
    n = len(gold)
    if not n:
        return None
    po = sum(g == p for g, p in zip(gold, pred)) / n
    pe = sum((gold.count(v) / n) * (pred.count(v) / n) for v in VERDICTS)
    if pe == 1:
        return None
    return round((po - pe) / (1 - pe), 4)


def score(items: list[dict], predictions: list[str | None]) -> dict:
    gold = [it["gold"] for it in items]
    pred = list(predictions)
    n = len(gold)
    correct = sum(g == p for g, p in zip(gold, pred))

    per_class, f1s = {}, []
    for v in VERDICTS:
        tp = sum(g == v and p == v for g, p in zip(gold, pred))
        fp = sum(g != v and p == v for g, p in zip(gold, pred))
        fn = sum(g == v and p != v for g, p in zip(gold, pred))
        prec = (tp / (tp + fp)) if (tp + fp) else 0.0
        rec = (tp / (tp + fn)) if (tp + fn) else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
        per_class[v] = {
            "precision": round(prec, 3) if (tp + fp) else None,
            "recall": round(rec, 3) if (tp + fn) else None,
            "f1": round(f1, 3),
            "support": gold.count(v),
        }
        f1s.append(f1)

    unsup = [(g, p) for g, p in zip(gold, pred) if g in _UNSUPPORTED_GOLD]
    sup = [(g, p) for g, p in zip(gold, pred) if g == "SUPPORTED"]
    confusion = {g: {p_cand: sum(g_item == g and p_item == p_cand for g_item, p_item in zip(gold, pred)) for p_cand in list(VERDICTS) + [None]} for g in VERDICTS}

    return {
        "items": n,
        "accuracy": round(correct / n, 4) if n else None,
        "macro_f1": round(sum(f1s) / len(f1s), 4),
        "cohen_kappa": _kappa(gold, [p for p in pred]),
        "unsafe_support_rate": round(sum(p in _SUPPORTING for _, p in unsup) / len(unsup), 4) if unsup else None,
        "missed_support_rate": round(sum(p != "SUPPORTED" for _, p in sup) / len(sup), 4) if sup else None,
        "unavailable_rate": round(sum(p is None for p in pred) / n, 4) if n else None,
        "per_class": per_class,
        "confusion": confusion,
    }


def evaluate_judge(items: list[dict], judge_fn) -> dict:
    preds = []
    for item in items:
        try:
            preds.append(judge_fn(item))
        except Exception:
            preds.append(None)
    return score(items, preds)


def lexical_baseline_judge(item: dict) -> str:
    claim_t = tokens(item["claim"])
    ev_t = set(tokens(item["evidence"]))
    if not claim_t:
        return "NOT_VERIFIABLE"
    nums = [t for t in claim_t if any(c.isdigit() for c in t)]
    words = [t for t in claim_t if not any(c.isdigit() for c in t)]
    cov_words = (sum(w in ev_t for w in words) / len(words)) if words else 1.0
    numbers_ok = all(n in ev_t for n in nums)
    if nums and not numbers_ok and cov_words >= 0.5:
        return "CONTRADICTED"
    cov = sum(t in ev_t for t in claim_t) / len(claim_t)
    if cov >= 0.85:
        return "SUPPORTED"
    if cov >= 0.6:
        return "PARTIALLY_SUPPORTED"
    return "NOT_VERIFIABLE"


def production_judge_fn(call_llm=None):
    from ai_core.evaluation import llm_judge

    def fn(item: dict) -> str | None:
        evidence = f"[Chunk #1 (Page {item['page']})]\n{item['evidence']}"
        if call_llm is not None:
            from unittest.mock import patch
            with patch("ai_core.evaluation.llm_judge.call_llm", call_llm):
                j = llm_judge.judge_claims_against_evidence("", evidence, item["claim"], [item["claim"]])
        else:
            j = llm_judge.judge_claims_against_evidence("", evidence, item["claim"], [item["claim"]])
        if j.get("overall_verdict") == llm_judge.STATE_VERIFICATION_PENDING or not j.get("claim_verdicts"):
            return None
        return j["claim_verdicts"][0]["verdict"]

    return fn


def to_markdown(report: dict, title: str) -> str:
    lines = [f"# Judge evaluation: {title}", "", "| metric | value |", "|---|---|"]
    lines.extend([f"| {m} | {report[m]} |" for m in ("items", "accuracy", "macro_f1", "cohen_kappa", "unsafe_support_rate", "missed_support_rate", "unavailable_rate")])
    lines.extend(["", "| verdict | precision | recall | f1 | support |", "|---|---|---|---|---|"])
    lines.extend([f"| {v} | {m['precision']} | {m['recall']} | {m['f1']} | {m['support']} |" for v, m in report["per_class"].items()])
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Evaluate the claim judge on labelled pairs")
    ap.add_argument("--labels", type=str, default=str(DEFAULT_LABELS))
    ap.add_argument("--live", action="store_true", help="use the PRODUCTION LLM judge (needs API keys + network)")
    args = ap.parse_args(argv)
    items = load_labels(Path(args.labels))
    if args.live:
        report = evaluate_judge(items, production_judge_fn())
        title = "production LLM judge (live)"
    else:
        report = evaluate_judge(items, lexical_baseline_judge)
        title = "deterministic lexical baseline (NOT the LLM judge)"
    sys.stdout.write(to_markdown(report, title))
    return 0


if __name__ == "__main__":
    sys.exit(main())
