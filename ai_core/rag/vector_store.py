"""
Vector Store — Supabase pgvector wrapper for judgments, statutes, and
per-document page chunks.
Multi-strategy retrieval with robust RPC fallbacks and direct-table similarity
to guarantee live document retrieval never fails.
"""
from supabase import create_client
import os
import uuid
import json
import re
import threading
import time
from dotenv import load_dotenv

from ai_core.rag.lexical import Bm25, reciprocal_rank_fusion, tokens as lexical_tokens

load_dotenv()


def get_supabase_client():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


# ---------------- Judgments ----------------

def insert_judgment(case_name, court, year, jurisdiction_type, full_text, embedding):
    client = get_supabase_client()
    return client.table("judgments").insert({
        "case_name": case_name, "court": court, "year": year,
        "jurisdiction_type": jurisdiction_type, "full_text": full_text, "embedding": embedding,
    }).execute()


def hybrid_search_judgments(query_embedding, query_text, match_count=5):
    client = get_supabase_client()
    return client.rpc("hybrid_search_judgments", {
        "query_embedding": query_embedding, "query_text": query_text, "match_count": match_count,
    }).execute().data


def hybrid_search_statutes(query_embedding, query_text, match_count=5):
    client = get_supabase_client()
    return client.rpc("hybrid_search_statutes", {
        "query_embedding": query_embedding, "query_text": query_text, "match_count": match_count,
    }).execute().data


KNOWN_ACT_ALIASES = {
    "bns": ["bharatiya nyaya sanhita", "bns"],
    "bnss": ["bharatiya nagarik suraksha sanhita", "bnss"],
    "bsa": ["bharatiya sakshya adhiniyam", "bsa"],
    "ipc": ["indian penal code", "ipc"],
    "crpc": ["code of criminal procedure", "crpc"],
    "cpc": ["code of civil procedure", "cpc"],
    "it act": ["information technology act", "it act"],
    "limitation act": ["limitation act"],
    "constitution": ["constitution of india", "constitution"],
}


def _word_in(phrase: str, text: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def detect_target_acts(query_text: str) -> list[str] | None:
    """Alias patterns (full name + abbreviation) of every act the query names, or None if it names none.

    Whole-word matching is essential: "bns" is a substring of "bnss", so substring matching sent every BNSS
    (procedure) question to the BNS (offences) filter and dropped the BNSS sections. Several acts in one
    question (e.g. "BNS 303 and BNSS 187") are all kept."""
    lowered = (query_text or "").lower()
    patterns: list[str] = []
    for alias_key, aliases in KNOWN_ACT_ALIASES.items():
        if _word_in(alias_key, lowered) or any(_word_in(a, lowered) for a in aliases):
            patterns.extend(a for a in aliases if a not in patterns)
    return patterns or None


def search_knowledge_base(query_embedding, query_text, match_count=5):
    judgments = hybrid_search_judgments(query_embedding, query_text, match_count) or []
    statutes = hybrid_search_statutes(query_embedding, query_text, match_count) or []

    target_act_patterns = detect_target_acts(query_text)

    valid_statutes = []
    for s in statutes:
        act_name_low = (s.get("act_name") or "").lower()
        if target_act_patterns:
            if any(_word_in(p, act_name_low) for p in target_act_patterns):
                s["source_type"] = "statute"
                s["display_name"] = f"{s['act_name']} — Section {s['section_number']}"
                s["score"] = s.get("combined_score", 0)
                valid_statutes.append(s)
        else:
            s["source_type"] = "statute"
            s["display_name"] = f"{s['act_name']} — Section {s['section_number']}"
            s["score"] = s.get("combined_score", 0)
            valid_statutes.append(s)

    for j in judgments:
        j["source_type"] = "judgment"
        j["display_name"] = j.get("case_name", "Landmark Judgment")
        j["score"] = j.get("combined_score", 0)

    combined = judgments + valid_statutes
    combined.sort(key=lambda x: x["score"], reverse=True)
    return combined[:match_count]


# ---------------- Document chunks (single-document-per-conversation) ----------------

INSERT_ROW_BATCH = 50
TABLE_PAGE_SIZE = 1000          # PostgREST default max-rows
TABLE_FALLBACK_MAX_ROWS = 5000  # hard cap on the direct-table fallback scan

_STOP_WORDS = {
    "what", "which", "where", "when", "does", "did", "the", "and", "for", "with", "this", "case",
    "file", "document", "hai", "hain", "kya", "me", "mein", "ne", "ko", "ke", "liye", "ka", "ki",
}


class PartialInsertError(RuntimeError):
    """Raised when an insert fails midway; carries the ids that WERE written so callers can roll back."""

    def __init__(self, message: str, inserted_ids: list[str]):
        super().__init__(message)
        self.inserted_ids = inserted_ids


def insert_document_chunks_batch(case_id: str, pages: list[tuple[int, str]], embeddings: list[list[float]]) -> list[str]:
    """Inserts (page_number, chunk_text) rows with their embeddings. Returns the new row ids.

    Refuses mismatched input instead of silently truncating with zip(), which would drop chunks."""
    if len(pages) != len(embeddings):
        raise ValueError(f"embedding/chunk count mismatch: {len(embeddings)} embeddings for {len(pages)} chunks")
    client = get_supabase_client()
    rows = [{"case_id": case_id, "page_number": p, "chunk_text": t, "embedding": e}
            for (p, t), e in zip(pages, embeddings)]
    inserted_ids: list[str] = []
    for i in range(0, len(rows), INSERT_ROW_BATCH):
        try:
            res = client.table("document_chunks").insert(rows[i:i + INSERT_ROW_BATCH]).execute()
        except Exception as e:
            raise PartialInsertError(str(e)[:200], inserted_ids) from e
        inserted_ids.extend(r["id"] for r in (res.data or []) if isinstance(r, dict) and r.get("id"))
    return inserted_ids


def count_document_chunks(case_id: str) -> int | None:
    """Number of indexed chunk rows for a case, or None if it could not be determined."""
    try:
        clean = str(uuid.UUID(str(case_id).strip()))
        res = get_supabase_client().table("document_chunks").select("id", count="exact").eq("case_id", clean).limit(1).execute()
        return res.count if isinstance(res.count, int) else None
    except Exception:
        return None


def list_document_chunk_ids(case_id: str) -> list[str]:
    """All chunk ids currently stored for a case (paginated, ids only)."""
    client = get_supabase_client()
    ids: list[str] = []
    start = 0
    while True:
        page = (client.table("document_chunks").select("id").eq("case_id", case_id)
                .range(start, start + TABLE_PAGE_SIZE - 1).execute().data) or []
        ids.extend(str(r["id"]) for r in page if isinstance(r, dict) and r.get("id"))
        if len(page) < TABLE_PAGE_SIZE:
            return ids
        start += len(page)


def delete_document_chunks(chunk_ids: list[str]) -> None:
    client = get_supabase_client()
    for i in range(0, len(chunk_ids), 100):
        client.table("document_chunks").delete().in_("id", chunk_ids[i:i + 100]).execute()


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _as_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_rpc_rows(payload) -> list[dict]:
    """Coerces every RPC response shape we have seen or can reasonably expect into a list of row dicts.

    Handled: list of dicts, None/empty, a JSON string, a single row dict, a {"data"|"rows"|"results": [...]}
    envelope, and lists whose items are JSON strings (functions returning setof json/jsonb)."""
    if payload is None:
        return []
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError):
            return []
    if isinstance(payload, dict):
        for key in ("data", "rows", "results"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
        else:
            payload = [payload] if ("chunk_text" in payload or "id" in payload) else []
    if not isinstance(payload, list):
        return []

    rows: list[dict] = []
    for item in payload:
        if isinstance(item, (str, bytes)):
            try:
                item = json.loads(item)
            except (ValueError, TypeError):
                continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _normalize_chunk_row(row: dict) -> dict | None:
    text = row.get("chunk_text")
    if text is None:
        text = row.get("content") or row.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    page = row.get("page_number")
    try:
        page = int(page) if page is not None else None
    except (TypeError, ValueError):
        page = None
    sim = _as_float(row.get("similarity"))
    if sim is None:
        sim = _as_float(row.get("score"))
    out = dict(row)
    out["chunk_text"] = text
    out["page_number"] = page
    if sim is not None:
        out["similarity"] = sim
        out.setdefault("score", sim)
    return out


def _chunk_ids_in_case(client, ids: list[str], case_id: str) -> set[str]:
    """Server-side ownership check for RPC rows that do not echo case_id. Fails CLOSED (empty set)."""
    if not ids:
        return set()
    try:
        owned: set[str] = set()
        for i in range(0, len(ids), 100):
            res = (client.table("document_chunks").select("id")
                   .eq("case_id", case_id).in_("id", ids[i:i + 100]).execute())
            owned.update(str(r["id"]) for r in (res.data or []) if isinstance(r, dict) and r.get("id"))
        return owned
    except Exception:
        return set()


def _isolate_to_case(client, rows: list[dict], case_id: str, attempt: dict) -> list[dict]:
    """Keeps only rows PROVEN to belong to case_id.

    Rows that echo a different case_id are dropped. Rows that echo none (an RPC whose RETURNS TABLE omits
    case_id) are verified against the table instead of being discarded wholesale, which is what used to turn
    a working RPC into zero chunks."""
    kept: list[dict] = []
    unknown: list[dict] = []
    for r in rows:
        cid = r.get("case_id")
        if cid in (None, ""):
            unknown.append(r)
        elif str(cid).lower() == case_id:
            kept.append(r)
        else:
            attempt["foreign_dropped"] += 1
    if unknown:
        owned = _chunk_ids_in_case(client, [str(r["id"]) for r in unknown if r.get("id")], case_id)
        for r in unknown:
            if r.get("id") is not None and str(r["id"]) in owned:
                r["case_id"] = case_id
                kept.append(r)
            else:
                attempt["unverifiable_dropped"] += 1
    return kept


def _fetch_case_rows(client, case_id: str) -> list[dict]:
    cols = "id, case_id, page_number, chunk_text, embedding"
    rows = list((client.table("document_chunks").select(cols).eq("case_id", case_id).execute().data) or [])
    if len(rows) >= TABLE_PAGE_SIZE:
        start = len(rows)
        while start < TABLE_FALLBACK_MAX_ROWS:
            page = (client.table("document_chunks").select(cols).eq("case_id", case_id)
                    .range(start, start + TABLE_PAGE_SIZE - 1).execute().data) or []
            rows.extend(page)
            if len(page) < TABLE_PAGE_SIZE:
                break
            start += len(page)
    return rows


def _rank_rows_locally(rows: list[dict], query_embedding: list[float], query_text: str, match_count: int) -> list[dict]:
    tokens = [w.lower() for w in re.findall(r"\w+", query_text or "")]
    meaningful = [t for t in tokens if t not in _STOP_WORDS and len(t) > 2]
    scored = []
    for r in rows:
        emb = r.get("embedding")
        if isinstance(emb, str):
            try:
                emb = json.loads(emb)
            except ValueError:
                emb = []
        cos = _cosine_similarity(query_embedding, emb) if isinstance(emb, list) and emb else 0.0
        text = (r.get("chunk_text") or "").lower()
        kw = (sum(1 for t in meaningful if t in text) / len(meaningful)) if meaningful else 0.0
        combined = 0.75 * cos + 0.25 * kw if meaningful else cos
        scored.append({
            "id": r.get("id"), "case_id": r.get("case_id"), "page_number": r.get("page_number"),
            "chunk_text": r.get("chunk_text", ""), "similarity": cos, "score": combined,
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:match_count]


# ---------------- lexical side of hybrid retrieval ----------------

LEXICAL_TTL_SECONDS = 60.0
LEXICAL_TOP = 20
SEMANTIC_WEIGHT = 1.0
LEXICAL_WEIGHT = 1.0
_lex_lock = threading.Lock()
_lex_cache: dict[str, tuple[float, list[dict], "Bm25"]] = {}
_LEX_CACHE_MAX = 64


def invalidate_case_cache(case_id: str) -> None:
    """Call after any write to a case's chunks so the next query sees them."""
    with _lex_lock:
        _lex_cache.pop(str(case_id).lower(), None)


def _case_lexical_index(client, case_id: str) -> tuple[list[dict], "Bm25"]:
    """(rows, BM25) for ALL chunks of ONE case, cached for a short time. Rows are re-checked for case membership."""
    key = case_id.lower()
    now = time.monotonic()
    with _lex_lock:
        hit = _lex_cache.get(key)
        if hit and now - hit[0] < LEXICAL_TTL_SECONDS:
            return hit[1], hit[2]
    cols = "id, case_id, page_number, chunk_text"
    rows: list[dict] = []
    start = 0
    while len(rows) < TABLE_FALLBACK_MAX_ROWS:
        page = normalize_rpc_rows(client.table("document_chunks").select(cols).eq("case_id", case_id)
                                  .range(start, start + TABLE_PAGE_SIZE - 1).execute().data)
        rows.extend(r for r in page if str(r.get("case_id", "")).lower() == key and isinstance(r.get("chunk_text"), str))
        if len(page) < TABLE_PAGE_SIZE:
            break
        start += len(page)
    index = Bm25([r["chunk_text"] for r in rows])
    with _lex_lock:
        if len(_lex_cache) >= _LEX_CACHE_MAX:
            _lex_cache.pop(next(iter(_lex_cache)))
        _lex_cache[key] = (now, rows, index)
    return rows, index


def _lexical_candidates(client, case_id: str, query_text: str, top: int = LEXICAL_TOP) -> tuple[list[dict], int]:
    rows, index = _case_lexical_index(client, case_id)
    scores, coverage = index.scores(query_text)
    ranked = sorted((i for i in range(len(rows)) if scores[i] > 0), key=lambda i: (-scores[i], i))[:top]
    out = []
    for i in ranked:
        r = dict(rows[i])
        r["page_number"] = _normalize_chunk_row(r)["page_number"] if _normalize_chunk_row(r) else None
        r["lexical_score"] = round(scores[i], 4)
        r["lexical_coverage"] = round(coverage[i], 3)
        out.append(r)
    return out, len(rows)


IDENTIFIER_BOOST = 0.02      # larger than the gap between adjacent RRF ranks (~0.0003), smaller than a full two-list hit


def _identifier_match(query_text: str, chunk_text: str) -> float:
    """Share of the query's numeric identifiers (registration numbers, years, amounts, exhibit numbers) that appear
    verbatim in the chunk. Embeddings blur exactly these, so an exact hit is a strong, deterministic rerank signal."""
    wanted = {t for t in lexical_tokens(query_text) if t.isdigit() and len(t) >= 3}
    if not wanted:
        return 0.0
    have = set(lexical_tokens(chunk_text))
    return len(wanted & have) / len(wanted)


def _fuse(semantic: list[dict], lexical: list[dict], match_count: int, query_text: str = "") -> list[dict]:
    """Reciprocal-rank fusion of the semantic and lexical rankings, deduplicated by chunk id, then a deterministic
    identifier-match rerank."""
    by_id: dict = {}
    for c in semantic:
        by_id[str(c.get("id"))] = dict(c, retrieved_by=["semantic"])
    for c in lexical:
        key = str(c.get("id"))
        if key in by_id:
            by_id[key]["lexical_score"] = c["lexical_score"]
            by_id[key]["lexical_coverage"] = c["lexical_coverage"]
            by_id[key]["retrieved_by"].append("lexical")
        else:
            by_id[key] = dict(c, retrieved_by=["lexical"])
    fused = reciprocal_rank_fusion(
        [[str(c.get("id")) for c in semantic], [str(c.get("id")) for c in lexical]],
        [SEMANTIC_WEIGHT, LEXICAL_WEIGHT])
    for key, c in by_id.items():
        ident = _identifier_match(query_text, c.get("chunk_text", "")) if query_text else 0.0
        c["identifier_match"] = round(ident, 3)
        c["rrf_score"] = round(fused.get(key, 0.0) + IDENTIFIER_BOOST * ident, 5)
    ordered = sorted(by_id.values(), key=lambda c: (-c["rrf_score"], -(c.get("similarity") or 0.0)))
    return ordered[:match_count]


class ChunkList(list):
    """A plain list of chunks that also carries the retrieval diagnostics (no document text, no secrets)."""
    diagnostics: dict = {}


def search_document_chunks(query_embedding: list[float], case_id: str, match_count: int = 8, query_text: str = "") -> list[dict]:
    """Top-k chunks for ONE case. Always returns a list; `result.diagnostics` explains how it was produced.

    Strategy chain (stops at the first strategy that yields >=1 chunk PROVEN to belong to the case):
      1. RPC match_document_chunks
      2. RPC match_document_chunks_multi
      3. direct table scan ranked locally (cosine + keyword)
    A strategy whose rows are all removed by case isolation no longer ends the search."""
    diag: dict = {"case_id": None, "strategy": None, "attempts": [], "returned": 0}
    result = ChunkList()
    result.diagnostics = diag
    try:
        clean_case_id = str(uuid.UUID(str(case_id).strip()))
    except (ValueError, AttributeError, TypeError):
        diag["error"] = "invalid_case_id"
        return result
    diag["case_id"] = clean_case_id

    client = get_supabase_client()
    hybrid = bool(query_text and query_text.strip())
    sem_k = max(match_count * 2, 16) if hybrid else match_count      # over-fetch so fusion has candidates to promote

    def run_single():
        return client.rpc("match_document_chunks", {
            "query_embedding": query_embedding, "target_case_id": clean_case_id, "match_count": sem_k,
        }).execute().data

    def run_multi():
        return client.rpc("match_document_chunks_multi", {
            "query_embedding": query_embedding, "target_case_ids": [clean_case_id], "match_count": sem_k,
        }).execute().data

    def run_table():
        all_rows = _fetch_case_rows(client, clean_case_id)
        diag["case_chunk_rows"] = len(all_rows)      # lets callers tell "nothing indexed" from "nothing relevant"
        return _rank_rows_locally(all_rows, query_embedding, query_text, sem_k)

    chunks: list[dict] = []
    # No query embedding (embedding provider down): semantic strategies are skipped and retrieval degrades to the
    # lexical index only. This is reported in the diagnostics so the answer can say so; it is never silent.
    diag["semantic_available"] = bool(query_embedding)
    for name, runner in (("rpc_single", run_single), ("rpc_multi", run_multi), ("table_scan", run_table)):
        attempt = {"strategy": name, "rows": 0, "kept": 0, "foreign_dropped": 0, "unverifiable_dropped": 0, "error": None}
        diag["attempts"].append(attempt)
        if not query_embedding:
            attempt["error"] = "no_query_embedding"
            continue
        try:
            rows = normalize_rpc_rows(runner())
        except Exception as e:
            attempt["error"] = f"{type(e).__name__}: {str(e)[:160]}"
            continue
        attempt["rows"] = len(rows)
        normalized = [n for n in (_normalize_chunk_row(r) for r in rows) if n is not None]
        kept = _isolate_to_case(client, normalized, clean_case_id, attempt)
        attempt["kept"] = len(kept)
        if kept:
            chunks = kept[:sem_k]
            diag["strategy"] = name
            break

    if hybrid:
        diag["hybrid"] = {"semantic": len(chunks), "lexical": 0, "lexical_error": None}
        try:
            lexical, total_rows = _lexical_candidates(client, clean_case_id, query_text)
            diag["hybrid"]["lexical"] = len(lexical)
            diag.setdefault("case_chunk_rows", total_rows)
            if lexical:
                chunks = _fuse(chunks, lexical, match_count, query_text)
                diag["strategy"] = diag["strategy"] or "lexical_only"
                diag["hybrid"]["lexical_only_in_result"] = sum(1 for c in chunks if c["retrieved_by"] == ["lexical"])
        except Exception as e:
            diag["hybrid"]["lexical_error"] = f"{type(e).__name__}: {str(e)[:120]}"
    chunks = chunks[:match_count]

    result.extend(chunks)
    diag["returned"] = len(chunks)
    diag["pages"] = [c.get("page_number") for c in chunks]
    diag["similarities"] = [round(c["similarity"], 3) for c in chunks if isinstance(c.get("similarity"), float)]
    print(f"[DOC_RETRIEVAL] {json.dumps(diag, default=str)}")
    return result
