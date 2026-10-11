"""
Offline evaluation suites that exercise the REAL production retrieval code (ai_core.rag.vector_store) against an
in-memory Supabase fake.

IMPORTANT LIMITS (also printed in the report):
* Embeddings are a deterministic hashed bag-of-words stub, NOT Gemini. Semantic-vs-hybrid numbers therefore test the
  fusion / isolation CODE and catch regressions; they do not measure real embedding quality or compare real retrievers.
* The dataset is tiny (one fictional case plus a distractor). Metrics saturate easily. New question categories were
  written before their first run and the retrieval code was not tuned on them, but the offline tokenizer WAS adjusted
  earlier after inspecting failures on the original 18 questions, so those results are optimistic.

Suites
  hybrid     semantic-only vs hybrid (semantic + lexical, RRF + identifier rerank): Recall@K, Hit@K, MRR, nDCG@K
  leakage    case A questions against a DB that also holds a similar case B and an RPC that IGNORES the case filter
             (worst case): cross-case chunk rate and B-unique marker hits must both be zero
  followups  raw follow-up vs rewritten standalone question retrieval; the rewriter gate/prompt flow is exercised with
             a scripted LLM (rewrite QUALITY is not measured offline)
  conflict   pages that disagree must BOTH be retrieved so the conflict can be shown
"""
import contextlib
import hashlib
import io
import math
import uuid
from unittest.mock import patch

from ai_core.evaluation.fake_supabase import FakeSupabase
from ai_core.memory.query_rewriter import rewrite_followup_query
from ai_core.rag import vector_store as vs
from ai_core.rag.document_chunker import build_page_chunks, PAGE_BREAK
from ai_core.rag.lexical import tokens

DIM = 256


def hash_embed(text: str) -> list[float]:
    """Deterministic hashed bag-of-words vector, L2-normalised. A stub for Gemini embeddings."""
    v = [0.0] * DIM
    for t in tokens(text):
        h = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16)
        v[h % DIM] += 1.0 if (h >> 8) & 1 else -1.0
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def _cos(a, b):
    return sum(x * y for x, y in zip(a, b))


def build_db(cases: dict[str, list[str]]) -> tuple[FakeSupabase, dict[str, str]]:
    """cases: name -> pages. Returns (fake db with chunks + embeddings, name -> case uuid)."""
    ids = {name: str(uuid.uuid5(uuid.NAMESPACE_URL, f"eval-case-{name}")) for name in cases}
    chunks = []
    for name, pages in cases.items():
        built, _ = build_page_chunks(PAGE_BREAK.join(pages))
        for i, (page, text) in enumerate(built):
            chunks.append({"id": f"{name}-{i}", "case_id": ids[name], "page_number": page, "chunk_text": text,
                           "embedding": hash_embed(text)})
    db = FakeSupabase(tables={"document_chunks": chunks, "cases": [{"id": i} for i in ids.values()]})

    def leaky_rpc(params):
        """Worst case: ignores target_case_id and returns the globally nearest chunks, with case_id echoed."""
        q = params["query_embedding"]
        rows = sorted(db.tables["document_chunks"], key=lambda r: -_cos(q, r["embedding"]))[: params.get("match_count", 8)]
        return [{"id": r["id"], "case_id": r["case_id"], "page_number": r["page_number"], "chunk_text": r["chunk_text"],
                 "similarity": _cos(q, r["embedding"])} for r in rows]

    db.rpc_handlers = {"match_document_chunks": leaky_rpc, "match_document_chunks_multi": leaky_rpc}
    return db, ids


def run_search(db: FakeSupabase, case_id: str, question: str, k: int, hybrid: bool) -> list[dict]:
    vs._lex_cache.clear()
    with patch("ai_core.rag.vector_store.get_supabase_client", return_value=db), contextlib.redirect_stdout(io.StringIO()):
        if hybrid:
            return list(vs.search_document_chunks(hash_embed(question), case_id, match_count=k, query_text=question))
        # semantic-only baseline: SAME candidate depth the hybrid path starts from (over-fetch, because rows of other
        # cases are dropped after the RPC), then truncated to k. Without this the comparison would reward hybrid for
        # merely over-fetching.
        return list(vs.search_document_chunks(hash_embed(question), case_id, match_count=max(2 * k, 16), query_text=""))[:k]


# ---------------------------------------------------------------- metrics (page level; shared with rag_eval)

def _metrics(rows: list[dict], k: int) -> dict:
    from ai_core.evaluation.rag_eval import recall_at_k, hit_at_k, reciprocal_rank, ndcg_at_k
    mean = lambda xs: round(sum(xs) / len(xs), 4) if xs else None
    return {
        f"recall@{k}": mean([recall_at_k(r["pages"], r["expected"], k) for r in rows]),
        f"hit@{k}": mean([hit_at_k(r["pages"], r["expected"], k) for r in rows]),
        "mrr": mean([reciprocal_rank(r["pages"], r["expected"]) for r in rows]),
        f"ndcg@{k}": mean([ndcg_at_k(r["pages"], r["expected"], k) for r in rows]),
    }


def _search_raw(db, case_id: str, question: str, k: int, embedding):
    vs._lex_cache.clear()
    with patch("ai_core.rag.vector_store.get_supabase_client", return_value=db), contextlib.redirect_stdout(io.StringIO()):
        return list(vs.search_document_chunks(embedding, case_id, match_count=k, query_text=question))


def _failure_modes(db, ids, answerable, k, markers) -> dict:
    """Retrieval under injected infrastructure failures. 'rpc_unavailable': both pgvector RPCs error (function missing or
    broken); 'no_query_embedding': the embedding provider is down. Reported: Recall@K/MRR for each, plus any chunk of
    another case or any case-B marker that surfaced (must stay zero)."""
    saved = db.rpc_handlers
    out = {}
    try:
        for mode in ("rpc_unavailable", "no_query_embedding"):
            db.rpc_handlers = {} if mode == "rpc_unavailable" else saved
            rows, leaked = [], 0
            for q in answerable:
                emb = None if mode == "no_query_embedding" else hash_embed(q["question"])
                got = _search_raw(db, ids["A"], q["question"], k, emb)
                rows.append({"pages": [c["page_number"] for c in got], "expected": q["expected_pages"]})
                leaked += sum(1 for c in got if c.get("case_id") != ids["A"] or any(m in c["chunk_text"].lower() for m in markers))
            m = _metrics(rows, k)
            out[mode] = {**m, "cross_case_chunks": leaked, "questions": len(rows)}
    finally:
        db.rpc_handlers = saved
    return out


def evaluate_suites(dataset: dict, distractor: dict, conflict: dict, k: int = 3) -> dict:
    db, ids = build_db({"A": dataset["pages"], "B": distractor["pages"], "C": conflict["pages"]})
    answerable = [q for q in dataset["questions"] if q["answerable"]]

    # ---- hybrid vs semantic-only, by category
    per = {"semantic_only": [], "hybrid": []}
    leaked_chunks = total_chunks = marker_hits = 0
    markers = [m.lower() for m in distractor.get("unique_markers", [])]
    for q in answerable:
        for mode in ("semantic_only", "hybrid"):
            got = run_search(db, ids["A"], q["question"], k, hybrid=(mode == "hybrid"))
            per[mode].append({"id": q["id"], "category": q.get("category", "fact"), "pages": [c["page_number"] for c in got],
                              "expected": q["expected_pages"]})
            if mode == "hybrid":
                total_chunks += len(got)
                leaked_chunks += sum(1 for c in got if c.get("case_id") != ids["A"])
                marker_hits += sum(1 for c in got if any(m in c["chunk_text"].lower() for m in markers))
    # also the unanswerable ones: they must not pull case B content either
    for q in dataset["questions"]:
        if not q["answerable"]:
            got = run_search(db, ids["A"], q["question"], k, hybrid=True)
            total_chunks += len(got)
            leaked_chunks += sum(1 for c in got if c.get("case_id") != ids["A"])
            marker_hits += sum(1 for c in got if any(m in c["chunk_text"].lower() for m in markers))

    categories = sorted({r["category"] for r in per["hybrid"]})
    by_cat = {cat: {mode: _metrics([r for r in per[mode] if r["category"] == cat], k) for mode in per} for cat in categories}

    # ---- follow-ups: raw vs rewritten
    fu_rows = {"raw": [], "rewritten": []}
    gate_ok = 0
    for f in dataset.get("followups", []):
        scripted = lambda model, prompt, f=f: f["standalone"]
        rw = rewrite_followup_query(f["question"], f["history"], scripted)
        gate_ok += 1 if (rw["rewritten"] and rw["query"] == f["standalone"]) else 0
        for name, text in (("raw", f["question"]), ("rewritten", rw["query"])):
            got = run_search(db, ids["A"], text, k, hybrid=True)
            fu_rows[name].append({"pages": [c["page_number"] for c in got], "expected": f["expected_pages"]})
    n_fu = len(dataset.get("followups", []))

    # ---- conflict: both disagreeing pages retrieved
    conflict_rows = []
    for q in conflict["questions"]:
        got = run_search(db, ids["C"], q["question"], k, hybrid=True)
        conflict_rows.append({"pages": [c["page_number"] for c in got], "expected": q["expected_pages"]})

    # ---- failure modes: what retrieval still delivers when infrastructure fails (and that it still never leaks)
    failure = _failure_modes(db, ids, answerable, k, markers)

    return {
        "failure_modes": failure,
        "hybrid": {**{f"hybrid_{m}": v for m, v in _metrics(per["hybrid"], k).items()},
                   **{f"semantic_only_{m}": v for m, v in _metrics(per["semantic_only"], k).items()}},
        "by_category": by_cat,
        "leakage": {
            "cross_case_chunk_rate": round(leaked_chunks / total_chunks, 4) if total_chunks else None,
            "other_case_marker_hits": marker_hits,
            "chunks_checked": total_chunks,
        },
        "followups": {
            "followups": n_fu,
            f"raw_recall@{k}": _metrics(fu_rows["raw"], k)[f"recall@{k}"] if n_fu else None,
            f"rewritten_recall@{k}": _metrics(fu_rows["rewritten"], k)[f"recall@{k}"] if n_fu else None,
            "rewriter_gate_hit_rate": round(gate_ok / n_fu, 4) if n_fu else None,
        },
        "conflict": {f"both_pages_recall@{k}": _metrics(conflict_rows, k)[f"recall@{k}"], "questions": len(conflict_rows)},
        "limits": ("Hashed bag-of-words stub embeddings, one small fictional case: a regression gate for fusion and isolation "
                   "code, not a measurement of real embedding quality."),
    }
