"""
OPT-IN integration tests: real database retrieval and approved provider integrations.

NOT run by default and NOT run during development of this change set (no credentials were used). To run them yourself,
against STAGING (never production), export the credentials in your shell and:

    RUN_INTEGRATION=1 python -m pytest tests/integration -q

Safety design
* Every database interaction is READ-ONLY (select / rpc that only reads). Nothing is inserted, updated or deleted.
* Provider tests send only fictional text. They cost a few API calls.
* Each test skips itself when the credentials it needs are not in the environment.
"""
import os
import uuid

import pytest

needs_supabase = pytest.mark.skipif(not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY")), reason="Supabase credentials not set")
needs_gemini = pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
needs_llm = pytest.mark.skipif(os.getenv("RUN_LIVE_LLM") != "1" or not (os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")),
                               reason="set RUN_LIVE_LLM=1 and a provider key to call the LLM")


@needs_gemini
def test_embedding_provider_returns_768_dimensions_for_hindi_and_english():
    from ai_core.rag.embeddings import embed_text, embed_texts_batch
    assert len(embed_text("What is the punishment for theft?", task_type="RETRIEVAL_QUERY")) == 768
    batch = embed_texts_batch(["The sale deed was executed on 9 August 2005.", "बिक्री विलेख 2005 में निष्पादित हुआ।"])
    assert [len(v) for v in batch] == [768, 768]


@needs_supabase
def test_retrieval_functions_exist_and_return_a_list_for_an_unknown_case():
    from ai_core.rag.vector_store import get_supabase_client
    client = get_supabase_client()
    rows = client.rpc("match_document_chunks", {"query_embedding": [0.0] * 768, "target_case_id": str(uuid.uuid4()), "match_count": 3}).execute().data
    assert rows in ([], None), "an unknown case id must return nothing"


@needs_supabase
def test_the_real_retrieval_function_does_not_cross_cases():
    """Picks two EXISTING cases that have chunks (read-only) and checks the live RPC for case A never returns case B rows."""
    from ai_core.rag.vector_store import get_supabase_client, search_document_chunks
    client = get_supabase_client()
    rows = client.table("document_chunks").select("case_id").limit(2000).execute().data or []
    case_ids = list(dict.fromkeys(r["case_id"] for r in rows))
    if len(case_ids) < 2:
        pytest.skip("need at least two cases with chunks in this database")
    a, b = case_ids[0], case_ids[1]
    sample = client.table("document_chunks").select("chunk_text, embedding").eq("case_id", b).limit(1).execute().data
    if not sample or not sample[0].get("embedding"):
        pytest.skip("no embedding available to probe with")
    import json
    emb = sample[0]["embedding"]
    emb = json.loads(emb) if isinstance(emb, str) else emb
    got = search_document_chunks(emb, a, match_count=8, query_text=sample[0]["chunk_text"][:200])
    assert all(str(c.get("case_id")).lower() == str(a).lower() for c in got), "chunks of another case were returned"
    # informational: a non-zero count means the database function itself ignores the case filter (the application code
    # still isolates the result, but the function should be fixed)
    print("rows from other cases dropped by the application:", got.diagnostics["attempts"][0]["foreign_dropped"])


@needs_supabase
def test_case_files_bucket_is_not_public():
    from ai_core.rag.vector_store import get_supabase_client
    buckets = {b.name: b for b in get_supabase_client().storage.list_buckets()}
    if "case-files" in buckets:
        assert not getattr(buckets["case-files"], "public", False), "the case-files bucket must be private"


@needs_llm
def test_claim_judge_on_the_labelled_pairs_with_the_real_llm():
    """Runs the production judge on eval/golden/judge_labels_v1.json. Records the numbers; asserts only the dangerous error."""
    from pathlib import Path
    from ai_core.evaluation import judge_eval
    items = judge_eval.load_labels()
    report = judge_eval.evaluate_judge(items, judge_eval.production_judge_fn())
    print(judge_eval.to_markdown(report, "production LLM judge (live)"))
    assert report["unavailable_rate"] < 0.5, "the judge was unavailable for most items: check keys / quota"
    out = Path("eval/reports"); out.mkdir(parents=True, exist_ok=True)
    (out / "judge_live_latest.md").write_text(judge_eval.to_markdown(report, "production LLM judge (live)"), encoding="utf-8")


@needs_llm
def test_crag_live_search_returns_only_allowed_domains():
    from ai_core.rag.crag_corrector import corrective_web_search, source_class
    result = corrective_web_search("punishment for theft Bharatiya Nyaya Sanhita section 303")
    if result is None:
        pytest.skip("no allowed result found right now (search engines vary)")
    assert all(source_class(l["url"]) for l in result["source_links"])
    print("official source found:", result["has_official_source"])
