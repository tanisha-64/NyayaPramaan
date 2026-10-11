"""
Reproducible RAG evaluation.

OFFLINE mode (default, used in CI): no network, no API keys, deterministic.
  * Document text goes through the REAL chunker (ai_core.rag.document_chunker.build_page_chunks), so chunk size and
    page tracking are exercised.
  * Ranking uses a pure-Python BM25 baseline. This is NOT the production embedding retriever; it measures the
    chunking / page-tracking / ranking-metric pipeline and catches regressions in it.
  * Groundedness is a lexical PROXY (share of answer sentences whose content words appear in the cited evidence).
    Production groundedness is judged by the LLM judge; use `--live` plumbing in your own harness for that.

Metrics (page-level; a "relevant" page is one listed in expected_pages):
  Recall@K, Hit@K, MRR, nDCG@K          - ranking quality over answerable questions
  correct_abstention_rate               - share of unanswerable questions the system abstains on
  false_abstention_rate                 - share of answerable questions it wrongly abstains on
  citation precision / recall / F1      - cited pages vs expected pages, for the candidate answers
  invalid_citation_rate                 - cited pages that were not in the retrieved top-K
  groundedness (proxy)                  - good answers should score high, hallucinated answers low

Run:  python -m ai_core.evaluation.rag_eval [--k 3] [--check] [--out eval/reports]
"""
import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

from ai_core.rag.lexical import Bm25, tokens, _stem, _STOP  # noqa: F401 (re-exported for tests)
from ai_core.rag.document_chunker import build_page_chunks, MAX_CHUNK_CHARS, CHUNK_OVERLAP_CHARS, PAGE_BREAK
from ai_core.trustagent.citations import check_citations, extract_cited_pages

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "eval" / "golden" / "land_dispute_v1.json"
DEFAULT_THRESHOLDS = ROOT / "eval" / "thresholds.json"
DISTRACTOR_DATASET = ROOT / "eval" / "golden" / "land_dispute_b_v1.json"
CONFLICT_DATASET = ROOT / "eval" / "golden" / "conflict_v1.json"

ROUTING_SECTIONS = ("routing", "legal_period", "source_policy", "privacy", "timeline")
ABSTAIN_COVERAGE_THRESHOLD = 0.34    # abstain if no chunk covers at least this share of the query's content terms
GROUNDED_SENTENCE_OVERLAP = 0.6       # a sentence is "supported" if >= 60% of its content words are in the evidence

# tokenizer, stemmer and BM25 live in ai_core.rag.lexical (shared with production hybrid retrieval)


# ---------------------------------------------------------------- ranking metrics (page level)

def dedupe_pages(ranked_pages: list) -> list:
    seen, out = set(), []
    for p in ranked_pages:
        if p is not None and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def recall_at_k(ranked_pages: list, expected: list, k: int) -> float:
    if not expected:
        return 0.0
    top = set(dedupe_pages(ranked_pages)[:k])
    return len(top & set(expected)) / len(set(expected))


def hit_at_k(ranked_pages: list, expected: list, k: int) -> float:
    return 1.0 if set(dedupe_pages(ranked_pages)[:k]) & set(expected) else 0.0


def reciprocal_rank(ranked_pages: list, expected: list) -> float:
    for i, p in enumerate(dedupe_pages(ranked_pages), start=1):
        if p in expected:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked_pages: list, expected: list, k: int) -> float:
    exp = set(expected)
    if not exp:
        return 0.0
    ranked = dedupe_pages(ranked_pages)[:k]
    dcg = sum(1.0 / math.log2(i + 2) for i, p in enumerate(ranked) if p in exp)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(exp), k)))
    return dcg / ideal if ideal else 0.0


# ---------------------------------------------------------------- citation + groundedness metrics

def citation_scores(answer: str, expected_pages: list, retrieved_pages: set) -> dict:
    cited = extract_cited_pages(answer)
    exp = set(expected_pages)
    hits = cited & exp
    precision = len(hits) / len(cited) if cited else 0.0
    recall = len(hits) / len(exp) if exp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    invalid = check_citations(answer, retrieved_pages)["invalid"]
    return {"precision": precision, "recall": recall, "f1": f1, "cited": sorted(cited),
            "invalid_citations": invalid, "invalid_rate": (len(invalid) / len(cited)) if cited else 0.0}


def groundedness_proxy(answer: str, evidence_text: str) -> float:
    """Share of answer sentences whose content words are (mostly) present in the evidence. Lexical proxy only."""
    ev = set(tokens(evidence_text))
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", re.sub(r"\[[^\]]*\]", "", answer)) if tokens(s)]
    if not sentences:
        return 0.0
    ok = 0
    for s in sentences:
        toks = tokens(s)
        if toks and sum(1 for t in toks if t in ev) / len(toks) >= GROUNDED_SENTENCE_OVERLAP:
            ok += 1
    return ok / len(sentences)


# ---------------------------------------------------------------- offline retriever (BM25 over real chunks)

class Bm25Index:
    """Offline retriever over (page_number, chunk_text) pairs."""

    def __init__(self, chunks: list[tuple[int, str]], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self._bm25 = Bm25([t for _, t in chunks], k1=k1, b=b)

    def search(self, query: str, k: int = 8) -> list[dict]:
        scores, coverage = self._bm25.scores(query)
        scored = [{"page_number": self.chunks[i][0], "chunk_text": self.chunks[i][1], "score": scores[i], "coverage": coverage[i]}
                  for i in range(len(self.chunks))]
        scored.sort(key=lambda x: (-x["score"], x["page_number"]))
        return scored[:k]


# ---------------------------------------------------------------- the evaluation

def load_dataset(path: Path = DEFAULT_DATASET) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate(dataset: dict, k: int = 3, search_fn=None, abstain_threshold: float = ABSTAIN_COVERAGE_THRESHOLD) -> dict:
    """search_fn(query, k) -> [{"page_number","chunk_text","score","coverage"}]; defaults to BM25 over the real chunker."""
    text = PAGE_BREAK.join(dataset["pages"])
    chunks, estimated = build_page_chunks(text)
    if search_fn is None:
        index = Bm25Index(chunks)
        search_fn = index.search

    per_q, answerable, unanswerable = [], [], []
    for q in dataset["questions"]:
        hits = search_fn(q["question"], k)
        ranked_pages = [h["page_number"] for h in hits]
        top_cov = max((h.get("coverage", 0.0) for h in hits), default=0.0)
        abstain = top_cov < abstain_threshold
        row = {"id": q["id"], "answerable": q["answerable"], "hard_negative": bool(q.get("hard_negative")), "ranked_pages": dedupe_pages(ranked_pages)[:k],
               "top_coverage": round(top_cov, 3), "abstained": abstain}
        if q["answerable"]:
            exp = q["expected_pages"]
            row.update({
                "expected_pages": exp,
                "recall": recall_at_k(ranked_pages, exp, k), "hit": hit_at_k(ranked_pages, exp, k),
                "rr": reciprocal_rank(ranked_pages, exp), "ndcg": ndcg_at_k(ranked_pages, exp, k),
            })
            answerable.append(row)
        else:
            unanswerable.append(row)
        per_q.append(row)

    mean = lambda xs: round(sum(xs) / len(xs), 4) if xs else None
    retrieved_by_q = {r["id"]: set(r["ranked_pages"]) for r in per_q}
    pages_text = {i + 1: p for i, p in enumerate(dataset["pages"])}
    q_by_id = {q["id"]: q for q in dataset["questions"]}

    cand_rows = []
    for c in dataset.get("candidate_answers", []):
        q = q_by_id[c["question_id"]]
        cited = extract_cited_pages(c["answer"])
        evidence_pages = cited or set(q["expected_pages"])
        evidence = " ".join(pages_text.get(p, "") for p in evidence_pages)
        cs = citation_scores(c["answer"], q["expected_pages"], retrieved_by_q.get(q["id"], set()))
        cand_rows.append({"id": c["id"], "kind": c["kind"], **cs, "groundedness": round(groundedness_proxy(c["answer"], evidence), 3)})

    by_kind = lambda kind, key: mean([r[key] for r in cand_rows if r["kind"] == kind])
    report = {
        "dataset": dataset["name"],
        "dataset_sha256": hashlib.sha256(json.dumps(dataset, sort_keys=True).encode()).hexdigest()[:16],
        "config": {"k": k, "retriever": "bm25-offline-baseline", "chunk_max_chars": MAX_CHUNK_CHARS,
                   "chunk_overlap_chars": CHUNK_OVERLAP_CHARS, "abstain_coverage_threshold": abstain_threshold,
                   "chunks": len(chunks), "pages_estimated": estimated},
        "counts": {"questions": len(per_q), "answerable": len(answerable), "unanswerable": len(unanswerable)},
        "retrieval": {
            f"recall@{k}": mean([r["recall"] for r in answerable]),
            f"hit@{k}": mean([r["hit"] for r in answerable]),
            "mrr": mean([r["rr"] for r in answerable]),
            f"ndcg@{k}": mean([r["ndcg"] for r in answerable]),
        },
        "abstention": {
            "correct_abstention_rate": mean([1.0 if r["abstained"] else 0.0 for r in unanswerable if not r["hard_negative"]]),
            # Unanswerable questions that reuse the document's vocabulary. A lexical gate cannot refuse these; the
            # production LLM judge has to. Reported for visibility, deliberately NOT gated.
            "hard_negative_abstention_rate": mean([1.0 if r["abstained"] else 0.0 for r in unanswerable if r["hard_negative"]]),
            "false_abstention_rate": mean([1.0 if r["abstained"] else 0.0 for r in answerable]),
            "accuracy": mean([1.0 if r["abstained"] != r["answerable"] else 0.0 for r in per_q if not r["hard_negative"]]),
        },
        "citations": {
            "good_answers_f1": by_kind("good", "f1"),
            # A wrong page that WAS retrieved is not "invalid" (the invalid rate only catches pages that were never
            # retrieved); it is caught by precision against the pages that actually hold the evidence.
            "wrong_page_answers_precision": by_kind("wrong_page", "precision"),
            "wrong_page_answers_invalid_rate": by_kind("wrong_page", "invalid_rate"),
            "good_answers_invalid_rate": by_kind("good", "invalid_rate"),
        },
        "groundedness_proxy": {
            "good_answers": by_kind("good", "groundedness"),
            "hallucinated_answers": by_kind("hallucinated", "groundedness"),
            # share of sentences in hallucinated answers that the evidence does not support (1 - groundedness)
            "unsupported_claim_rate_hallucinated": (None if by_kind("hallucinated", "groundedness") is None
                                                    else round(1 - by_kind("hallucinated", "groundedness"), 4)),
            "unsupported_claim_rate_good": (None if by_kind("good", "groundedness") is None
                                            else round(1 - by_kind("good", "groundedness"), 4)),
        },
        "per_question": per_q,
        "candidate_answers": cand_rows,
    }
    return report


def evaluate_all(dataset: dict | None = None, k: int = 3) -> dict:
    """Core evaluation + the suites that run the production retrieval code (hybrid, leakage, follow-ups, conflicts)."""
    from ai_core.evaluation.rag_suites import evaluate_suites
    dataset = dataset or load_dataset()
    report = evaluate(dataset, k=k)
    suites = evaluate_suites(dataset, load_dataset(DISTRACTOR_DATASET), load_dataset(CONFLICT_DATASET), k=k)
    for key in ("hybrid", "leakage", "followups", "conflict"):
        report[key] = suites[key]
    report["failure_modes"] = {f"{mode}_{metric}": value for mode, metrics in suites["failure_modes"].items()
                               for metric, value in metrics.items()}
    report["by_category"] = suites["by_category"]
    report["suite_limits"] = suites["limits"]
    return report


# ---------------------------------------------------------------- gating + reporting

def check_thresholds(report: dict, thresholds: dict) -> list[str]:
    """Returns human-readable failures. thresholds: {"section.metric": {"min": x} | {"max": x}}."""
    failures = []
    for path, bound in thresholds.items():
        if path.startswith("_"):
            continue
        section, metric = path.split(".", 1)
        if section in ROUTING_SECTIONS:          # gated by ai_core.evaluation.routing_eval
            continue
        value = report.get(section, {}).get(metric)
        if value is None:
            failures.append(f"{path}: missing from report")
            continue
        if "min" in bound and value < bound["min"]:
            failures.append(f"{path} = {value} < min {bound['min']}")
        if "max" in bound and value > bound["max"]:
            failures.append(f"{path} = {value} > max {bound['max']}")
    return failures


def to_markdown(report: dict, failures: list[str] | None = None) -> str:
    lines = [f"# RAG evaluation: {report['dataset']} (sha {report['dataset_sha256']})", "",
             f"Retriever: `{report['config']['retriever']}`, K={report['config']['k']}, "
             f"chunks={report['config']['chunks']}, abstain threshold={report['config']['abstain_coverage_threshold']}", ""]
    for section in ("retrieval", "abstention", "citations", "groundedness_proxy", "hybrid", "leakage", "failure_modes", "followups", "conflict"):
        if section not in report:
            continue
        lines += [f"## {section}", "", "| metric | value |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in report[section].items()]
        lines.append("")
    if report.get("by_category"):
        lines += ["## hybrid vs semantic-only by question category", "", "| category | semantic-only recall | hybrid recall |", "|---|---|---|"]
        for cat, modes in report["by_category"].items():
            key = next(k for k in modes["hybrid"] if k.startswith("recall@"))
            lines.append(f"| {cat} | {modes['semantic_only'][key]} | {modes['hybrid'][key]} |")
        lines.append("")
    if report.get("suite_limits"):
        lines += ["> **Limits.** " + report["suite_limits"], ""]
    misses = [r for r in report["per_question"] if r["answerable"] and r["hit"] == 0.0]
    lines += ["## Answerable questions with no expected page in top-K", ""]
    lines += [f"- {r['id']}: expected {r['expected_pages']}, got {r['ranked_pages']}" for r in misses] or ["- none"]
    if failures is not None:
        lines += ["", "## Threshold check", ""] + ([f"- FAIL {f}" for f in failures] or ["- all thresholds met"])
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--dataset", default=str(DEFAULT_DATASET))
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--check", action="store_true", help="exit 1 if eval/thresholds.json is not met")
    ap.add_argument("--thresholds", default=str(DEFAULT_THRESHOLDS))
    ap.add_argument("--out", default=str(ROOT / "eval" / "reports"))
    args = ap.parse_args(argv)

    report = evaluate_all(load_dataset(Path(args.dataset)), k=args.k)
    failures = None
    if args.check:
        failures = check_thresholds(report, json.loads(Path(args.thresholds).read_text(encoding="utf-8")))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md = to_markdown(report, failures)
    (out / "latest.md").write_text(md, encoding="utf-8")
    sys.stdout.write(md)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
