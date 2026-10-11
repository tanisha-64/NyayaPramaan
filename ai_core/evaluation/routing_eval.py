"""
Deterministic evaluation of the parts of the pipeline that are rules, not models: question routing, legal-period
detection, source-class policy, privacy redaction and timeline extraction.

No network, no keys, no LLM: the intent classifier's LLM fallback is replaced by an exception, which is exactly what
production does when the provider fails, so the report also shows how much routing depends on the LLM at all.

What it does NOT measure (stated so no number is over-read):
  * the quality of LLM answers, the claim judge, or live web retrieval (run judge_eval --live and the integration
    tests on staging for those)
  * whether a legal statement is correct: that needs a human legal reviewer
  * the datasets are small and written by the developer; they are regression gates, not benchmarks.

Run:  python -m ai_core.evaluation.routing_eval [--check] [--out eval/reports]
Metrics are gated by the "routing" / "timeline" / "source_policy" / "legal_period" / "privacy" entries in eval/thresholds.json.
"""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
GENERAL_LAW = ROOT / "eval" / "golden" / "general_law_v1.json"
LAND_DISPUTE = ROOT / "eval" / "golden" / "land_dispute_v1.json"
THRESHOLDS = ROOT / "eval" / "thresholds.json"


def _rate(num: int, den: int):
    return round(num / den, 4) if den else None


def evaluate_routing(items: list[dict]) -> dict:
    from ai_core.router.intent_classifier import classify_intent
    llm_calls = {"n": 0}

    def provider_down(model, prompt):
        llm_calls["n"] += 1
        raise RuntimeError("provider unavailable (offline evaluation)")

    rows, per_label = [], {}
    with patch("ai_core.router.intent_classifier.call_llm", side_effect=provider_down):
        for it in items:
            got = classify_intent(it["question"], it["has_document"])["label"]
            ok = got == it["expected"]
            rows.append({"id": it["id"], "expected": it["expected"], "got": got, "ok": ok})
            bucket = per_label.setdefault(it["expected"], {"n": 0, "correct": 0})
            bucket["n"] += 1
            bucket["correct"] += int(ok)
    return {
        "questions": len(rows),
        "accuracy": _rate(sum(r["ok"] for r in rows), len(rows)),
        "document_question_leak_rate": _rate(                     # a CASE_SPECIFIC question sent to the general pipeline
            sum(1 for r in rows if r["expected"] == "CASE_SPECIFIC" and r["got"] != "CASE_SPECIFIC"),
            sum(1 for r in rows if r["expected"] == "CASE_SPECIFIC")),
        "general_misrouted_to_document_rate": _rate(              # a GENERAL_LAW question pulled into the open document
            sum(1 for r in rows if r["expected"] == "GENERAL_LAW" and r["got"] in ("CASE_SPECIFIC", "MIXED")),
            sum(1 for r in rows if r["expected"] == "GENERAL_LAW")),
        "llm_calls_needed": llm_calls["n"],
        "per_label": per_label,
        "misses": [r for r in rows if not r["ok"]],
    }


def evaluate_legal_period(items: list[dict]) -> dict:
    from ai_core.trustagent.legal_framework import analyze_legal_framework
    misses, period_ok, note_ok = [], 0, 0
    for it in items:
        a = analyze_legal_framework(it["question"])
        p_ok = a["period"] == it["expected_period"]
        n_ok = bool(a["note"]) == it["expects_note"]
        period_ok += int(p_ok)
        note_ok += int(n_ok)
        if not (p_ok and n_ok):
            misses.append({"id": it["id"], "expected_period": it["expected_period"], "got": a["period"], "note": bool(a["note"])})
    return {"questions": len(items), "period_accuracy": _rate(period_ok, len(items)), "note_accuracy": _rate(note_ok, len(items)),
            "misses": misses}


def evaluate_source_policy(items: list[dict]) -> dict:
    from ai_core.rag.crag_corrector import source_class
    misses = []
    for it in items:
        got = source_class(it["url"]) or "blocked"
        if got != it["expected"]:
            misses.append({"url": it["url"], "expected": it["expected"], "got": got})
    blocked = [i for i in items if i["expected"] == "blocked"]
    return {
        "urls": len(items), "accuracy": _rate(len(items) - len(misses), len(items)),
        "blocked_url_pass_rate": _rate(sum(1 for m in misses if m["expected"] == "blocked"), len(blocked)),   # must be 0
        "misses": misses,
    }


def evaluate_privacy(items: list[dict]) -> dict:
    from ai_core.guardrails.output_guard import redact_pii
    leaked = destroyed = 0
    redact_cases = [i for i in items if "must_not_contain" in i]
    keep_cases = [i for i in items if "must_preserve" in i]
    for it in redact_cases:
        leaked += int(it["must_not_contain"] in redact_pii(it["text"]))
    for it in keep_cases:
        out = redact_pii(it["text"])
        destroyed += int(any(token not in out for token in it["must_preserve"]))
    return {"identifier_leak_rate": _rate(leaked, len(redact_cases)), "legal_text_destroyed_rate": _rate(destroyed, len(keep_cases)),
            "cases": len(items)}


def evaluate_timeline(dataset: dict) -> dict:
    from ai_core.rag.document_chunker import PAGE_BREAK
    from ai_core.timeline.extractor import extract_timeline_events
    events = extract_timeline_events(PAGE_BREAK.join(dataset["pages"]))
    got = {(e["date"], e["page"]) for e in events}
    want = {(t["date"], t["page"]) for t in dataset.get("timeline", [])}
    recorded = [e for e in events if e["event_type"] == "hearing" and e["status"] == "recorded"]
    allowed = {(r["date"], r["page"]) for r in dataset.get("recorded_hearings", [])}
    return {
        "expected_events": len(want), "extracted_events": len(got),
        "date_page_recall": _rate(len(got & want), len(want)),
        "date_page_precision": _rate(len(got & want), len(got)),
        # a date that is not described as a hearing that happened must never be shown as one
        "false_recorded_hearings": sum(1 for e in recorded if (e["date"], e["page"]) not in allowed),
        "missing": sorted(want - got), "unexpected": sorted(got - want),
    }


def evaluate_all() -> dict:
    general = json.loads(GENERAL_LAW.read_text(encoding="utf-8"))
    land = json.loads(LAND_DISPUTE.read_text(encoding="utf-8"))
    return {
        "dataset": {"general_law": general["name"], "land_dispute": land["name"]},
        "routing": evaluate_routing(general["routing"]),
        "legal_period": evaluate_legal_period(general["legal_period"]),
        "source_policy": evaluate_source_policy(general["source_policy"]),
        "privacy": evaluate_privacy(general["privacy"]),
        "timeline": evaluate_timeline(land),
    }


def check_thresholds(report: dict, thresholds: dict) -> list[str]:
    failures = []
    for path, bound in thresholds.items():
        if path.startswith("_"):
            continue
        section, metric = path.split(".", 1)
        if section not in ("routing", "legal_period", "source_policy", "privacy", "timeline"):
            continue
        value = report.get(section, {}).get(metric)
        if value is None:
            failures.append(f"{path}: missing from report")
        elif "min" in bound and value < bound["min"]:
            failures.append(f"{path} = {value} < min {bound['min']}")
        elif "max" in bound and value > bound["max"]:
            failures.append(f"{path} = {value} > max {bound['max']}")
    return failures


def to_markdown(report: dict, failures: list[str] | None = None) -> str:
    lines = ["# Routing / policy / timeline evaluation (deterministic, offline)", ""]
    for section in ("routing", "legal_period", "source_policy", "privacy", "timeline"):
        lines += [f"## {section}", "", "| metric | value |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in report[section].items() if not isinstance(v, (list, dict))]
        for key in ("misses", "missing", "unexpected"):
            if report[section].get(key):
                lines.append(f"\n{key}: `{json.dumps(report[section][key], ensure_ascii=False)}`")
        lines.append("")
    if failures is not None:
        lines += ["## Threshold check", ""] + ([f"- FAIL {f}" for f in failures] or ["- all thresholds met"])
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic routing / policy / timeline evaluation")
    ap.add_argument("--check", action="store_true", help="exit 1 if eval/thresholds.json is not met")
    ap.add_argument("--out", default=str(ROOT / "eval" / "reports"))
    args = ap.parse_args(argv)
    report = evaluate_all()
    failures = check_thresholds(report, json.loads(THRESHOLDS.read_text(encoding="utf-8"))) if args.check else None
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "routing_latest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md = to_markdown(report, failures)
    (out / "routing_latest.md").write_text(md, encoding="utf-8")
    sys.stdout.write(md)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
