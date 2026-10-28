"""
Local eval script for NyayaPramaan.
Run: python -m backend.eval.run_eval
Checks three things and prints a report, also saved to eval_report.json:
  1. citation accuracy   -- does the found section match the expected one?
  2. retrieval quality    -- for document queries, was the expected page retrieved?
  3. faithfulness         -- (LLM-judged) is a given answer fully supported by its evidence?
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, so backend.* imports work

from backend.routers.chat_router import find_sections, explicit_lookup, _hybrid_retrieve, _load_pages
from ai_core.rag.vector_store import get_supabase_client
from ai_core.llm_gateway import call_llm, is_llm_failure
from ai_core.router.adaptive_router import choose_model

TEST_CASES_PATH = Path(__file__).parent / "test_cases.json"
REPORT_PATH = Path(__file__).parent / "eval_report.json"


def check_citation(case, client):
    ex = explicit_lookup(case["query"])
    rows = find_sections(client, case["query"])
    found_section = ex[1] if ex else (rows[0].get("section") if rows else None)
    expected = str(case.get("expected_section") or "")
    passed = bool(expected) and str(found_section) == expected
    return {"passed": passed, "found_section": found_section, "expected_section": expected}


def check_retrieval(case, client):
    if not case.get("case_id"):
        return None
    chunks, info = _hybrid_retrieve(case["query"], case["case_id"], "", pages=_load_pages(client, case["case_id"]))
    pages = {c.get("page_number") for c in chunks}
    expected_pages = set(case.get("expected_pages") or [])
    passed = bool(expected_pages) and bool(pages & expected_pages)
    return {"passed": passed, "retrieved_pages": sorted(p for p in pages if p), "expected_pages": sorted(expected_pages)}


def check_faithfulness(case):
    answer, evidence = case.get("expected_answer_sample"), case.get("evidence_override")
    if not answer or not evidence:
        return None
    prompt = (
        "You are a fact-checker for a legal answer. Judge ONLY whether the FACTS in the ANSWER (section numbers, "
        "Act names, punishments, dates, amounts) are supported by the EVIDENCE. Paraphrasing, rewording and "
        "summarizing are completely fine and should NOT count as unsupported -- only flag it if the ANSWER states "
        "a fact that is missing from or contradicted by the EVIDENCE.\n"
        "Reply with ONLY one word: YES (facts match) or NO (facts don't match).\n\n"
        f"EVIDENCE:\n{evidence[:4000]}\n\nANSWER:\n{answer[:2000]}\n\nYOUR VERDICT (YES/NO):"
    )
    verdict = call_llm(choose_model(case["query"]), prompt)
    if is_llm_failure(verdict):
        return None
    return {"passed": verdict.strip().upper().startswith("YES"), "raw_verdict": verdict.strip()[:80]}


def run():
    cases = json.loads(TEST_CASES_PATH.read_text(encoding="utf-8"))
    client = get_supabase_client()
    results = []
    for case in cases:
        results.append({
            "id": case["id"], "query": case["query"],
            "citation": check_citation(case, client),
            "retrieval": check_retrieval(case, client),
            "faithfulness": check_faithfulness(case),
        })

    def pct(key):
        rel = [r[key]["passed"] for r in results if r.get(key) is not None]
        return f"{sum(rel)}/{len(rel)}" if rel else "n/a"

    print(f"\nCitation accuracy:   {pct('citation')}")
    print(f"Retrieval quality:   {pct('retrieval')}")
    print(f"Faithfulness:        {pct('faithfulness')}\n")
    for r in results:
        flags = [f"{k}={'PASS' if r[k]['passed'] else 'FAIL'}" for k in ("citation", "retrieval", "faithfulness") if r.get(k) is not None]
        print(f"[{r['id']}] {r['query'][:60]:<60} {' '.join(flags)}")

    REPORT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nFull report saved to {REPORT_PATH}")


if __name__ == "__main__":
    run()