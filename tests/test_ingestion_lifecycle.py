"""Document processing and indexing lifecycle: extraction, page-aware chunking, provenance, embeddings, storage, and
how partial failures are reported. Embeddings and the database are faked; everything else is the real code."""
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ai_core.evaluation.fake_supabase import FakeSupabase
from ai_core.evaluation.rag_suites import hash_embed
from ai_core.rag import document_chunker as dch
from ai_core.rag import embeddings as emb
from ai_core.rag.document_reader import read_case_file_with_gemini
from ai_core.rag.provenance import paragraph_numbers, locate
from tests import sample_docs as S
from tests.helpers import make_text_pdf

CASE = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase(tables={"document_chunks": [], "cases": [{"id": CASE, "status": "processing"}]})
    for target in ("ai_core.rag.vector_store.get_supabase_client", "ai_core.rag.document_chunker.get_supabase_client"):
        patcher = patch(target, return_value=fake)
        patcher.start()
    monkeypatch.setattr(dch.time, "sleep", lambda s: None)
    yield fake
    patch.stopall()


def _embed_ok(texts):
    return [hash_embed(t) for t in texts]


def rows(db, case=CASE):
    return [r for r in db.rows("document_chunks") if r["case_id"] == case]


# ------------------------------------------------------------------ extraction + page-aware chunking

def test_text_pdf_pages_survive_extraction_and_chunking():
    pdf = make_text_pdf([f"Page {i} heading line.\n{i}. Paragraph text for page {i} that is long enough to be indexed properly." for i in (1, 2, 3)])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(pdf)
    try:
        text = read_case_file_with_gemini(f.name)
    finally:
        os.remove(f.name)
    chunks, estimated = dch.build_page_chunks(text)
    assert not estimated
    assert sorted({p for p, _ in chunks}) == [1, 2, 3]
    for page, chunk in chunks:
        assert f"page {page}" in chunk.lower(), "a chunk must sit on the page its text came from"


def test_chunks_respect_size_limit_and_pages_are_real():
    chunks, estimated = dch.build_page_chunks(S.JUDGMENT_TEXT)
    assert not estimated and chunks
    assert all(len(t) <= dch.MAX_CHUNK_CHARS for _, t in chunks)
    by_page = {}
    for p, t in chunks:
        by_page.setdefault(p, []).append(t)
    assert sorted(by_page) == [1, 2, 3, 4]
    assert any("30 November 2021" in t for t in by_page[4])
    assert any("sale agreement dated 14 January 2018" in t for t in by_page[2])
    assert not any("sale agreement dated 14 January 2018" in t for t in by_page[1] + by_page[3] + by_page[4])


def test_paragraph_markers_are_preserved_and_read_back():
    chunks, _ = dch.build_page_chunks(S.JUDGMENT_TEXT)
    page3 = [t for p, t in chunks if p == 3]
    paras = sorted({n for t in page3 for n in paragraph_numbers(t)})
    assert paras == [9, 10, 11, 12]
    loc = locate({"page_number": 3, "chunk_text": page3[0]}, "case.pdf")
    assert loc["page"] == 3 and loc["document"] == "case.pdf" and loc["paragraphs"][0] == 9 and loc["snippet"]


def test_no_paragraph_is_invented_for_text_without_markers():
    loc = locate({"page_number": 2, "chunk_text": "A continuation of an earlier paragraph with no number at all."}, "c.pdf")
    assert loc["paragraphs"] == [] and "no explicit paragraph" in loc["paragraph_note"]
    assert paragraph_numbers("In 2019. The court said 12 days later that Rs. 5, 000 was due.") == []


def test_exact_duplicates_on_one_page_are_dropped_but_other_pages_keep_theirs():
    assert dch._dedupe([(1, "a"), (1, "a"), (2, "a"), (1, "b"), (1, "a")]) == [(1, "a"), (2, "a"), (1, "b")]
    line = "The same sentence appears on two different pages of the document and is long enough."
    two_pages, _ = dch.build_page_chunks(f"{line}\f{line}")
    assert [p for p, _ in two_pages] == [1, 2], "identical text on different pages is a different citation"


def test_text_without_page_information_is_flagged_as_estimated():
    text = " ".join(f"Sentence number {i} about the dispute." for i in range(200))
    chunks, estimated = dch.build_page_chunks(text)
    assert estimated and chunks


# ------------------------------------------------------------------ indexing, status, retry

def test_successful_index_is_complete_and_isolated_to_the_case(db):
    with patch.object(dch, "embed_texts_batch", side_effect=_embed_ok):
        report = dch.index_case_text(S.JUDGMENT_TEXT, CASE)
    assert report.complete and report.error is None and report.failed_pages == []
    assert report.pages_indexed == report.pages_with_text == 4
    stored = rows(db)
    assert len(stored) == report.chunks_inserted > 0
    assert all(r["case_id"] == CASE and r["page_number"] in (1, 2, 3, 4) and len(r["embedding"]) == 256 for r in stored)
    assert dch.record_index_result(CASE, report) == "ready"
    case = db.rows("cases")[0]
    assert case["status"] == "ready" and case["index_report"]["complete"] is True


def test_reindexing_never_duplicates_chunks(db):
    with patch.object(dch, "embed_texts_batch", side_effect=_embed_ok):
        first = dch.index_case_text(S.JUDGMENT_TEXT, CASE)
        again = dch.index_case_text(S.JUDGMENT_TEXT, CASE)                      # identical, complete: left alone
        assert again.skipped_existing and len(rows(db)) == first.chunks_inserted
        old_ids = {r["id"] for r in rows(db)}
        forced = dch.index_case_text(S.JUDGMENT_TEXT, CASE, force=True)         # explicit rebuild
    new_ids = {r["id"] for r in rows(db)}
    assert len(new_ids) == first.chunks_inserted == forced.chunks_inserted
    assert not (old_ids & new_ids), "a forced re-index replaces the rows instead of adding to them"


def test_embedding_failure_is_never_silent_partial_index_is_reported(db, monkeypatch):
    monkeypatch.setattr(dch, "BATCH_SIZE", 1)           # 3 chunks per round so there are several rounds
    long_text = "\f".join(f"{i}. " + (f"Finding number {i} of the court is recorded here. " * 12) for i in range(1, 9))
    calls = {"n": 0}

    def flaky(texts):
        calls["n"] += 1
        if calls["n"] > 1:                              # first round succeeds, every later call fails (after retries)
            raise RuntimeError("provider quota exceeded")
        return _embed_ok(texts)

    with patch.object(dch, "embed_texts_batch", side_effect=flaky):
        report = dch.index_case_text(long_text, CASE)
    assert not report.complete and report.failed_pages and report.error == "RuntimeError"
    assert report.pages_indexed < report.pages_with_text
    assert report.chunks_inserted == len(rows(db)) > 0        # what is stored is exactly what is reported
    assert dch.record_index_result(CASE, report) == "ready"
    stored = db.rows("cases")[0]
    assert stored["index_report"]["complete"] is False and stored["index_report"]["failed_pages"]


def test_total_embedding_failure_marks_the_document_failed(db):
    with patch.object(dch, "embed_texts_batch", side_effect=RuntimeError("provider down")):
        report = dch.index_case_text(S.JUDGMENT_TEXT, CASE)
    assert report.chunks_inserted == 0 and not report.complete
    assert rows(db) == []
    assert dch.record_index_result(CASE, report) == "failed"
    assert db.rows("cases")[0]["status"] == "failed" and db.rows("cases")[0]["rejection_reason"]


def test_failed_reindex_keeps_the_previous_working_index(db):
    with patch.object(dch, "embed_texts_batch", side_effect=_embed_ok):
        dch.index_case_text(S.JUDGMENT_TEXT, CASE)
    before = {r["id"] for r in rows(db)}
    with patch.object(dch, "embed_texts_batch", side_effect=RuntimeError("provider down")):
        report = dch.index_case_text(S.JUDGMENT_TEXT, CASE, force=True)
    assert report.kept_previous_index and {r["id"] for r in rows(db)} == before
    assert dch.record_index_result(CASE, report) == "ready", "the old index is still searchable"


def test_wrong_number_of_embeddings_is_an_error_not_a_truncation(db):
    with patch.object(dch, "embed_texts_batch", side_effect=lambda texts: _embed_ok(texts)[:-1]):
        report = dch.index_case_text(S.JUDGMENT_TEXT, CASE)
    assert report.chunks_inserted == 0 and rows(db) == [] and report.error


def test_partial_database_insert_is_rolled_back(monkeypatch):
    from ai_core.rag import vector_store as vs
    monkeypatch.setattr(vs, "INSERT_ROW_BATCH", 2)
    seen = {"inserts": 0}

    def fail_second(_payload):
        seen["inserts"] += 1
        return seen["inserts"] == 2

    fake = FakeSupabase(tables={"document_chunks": [], "cases": [{"id": CASE}]}, fail_on={("document_chunks", "insert"): fail_second})
    with patch("ai_core.rag.vector_store.get_supabase_client", return_value=fake), \
         patch("ai_core.rag.document_chunker.get_supabase_client", return_value=fake), \
         patch.object(dch, "embed_texts_batch", side_effect=_embed_ok), patch.object(dch.time, "sleep"):
        report = dch.index_case_text(S.JUDGMENT_TEXT, CASE)
    assert report.error and not report.complete
    assert [r for r in fake.rows("document_chunks")] == [], "rows written before the failure must be removed"


def test_record_index_result_survives_a_missing_report_column():
    def reject_new_column(payload):
        return isinstance(payload, dict) and "index_report" in payload

    fake = FakeSupabase(tables={"cases": [{"id": CASE}]}, fail_on={("cases", "update"): reject_new_column})
    with patch("ai_core.rag.document_chunker.get_supabase_client", return_value=fake):
        report = dch.IndexReport(chunks_inserted=3, pages_indexed=1, pages_with_text=1, total_pages=1)
        assert dch.record_index_result(CASE, report) == "ready"
    assert fake.rows("cases")[0]["status"] == "ready"


def test_scanned_page_goes_through_ocr_and_blank_page_is_not_a_failure(db):
    pdf = make_text_pdf(["1. First page text of the judgment that is plainly readable.", "", ""])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(pdf)
    try:
        ocr = lambda path, page: "2. Text recovered by OCR from a scanned page." if page == 2 else ""
        with patch.object(dch, "embed_texts_batch", side_effect=_embed_ok), patch.object(dch, "_try_ocr", side_effect=ocr):
            report = dch.index_pdf(f.name, CASE)
    finally:
        os.remove(f.name)
    assert report.total_pages == 3 and report.ocr_pages == 1
    assert report.pages_with_text == 2 and report.pages_indexed == 2 and report.complete
    assert sorted({r["page_number"] for r in rows(db)}) == [1, 2]


# ------------------------------------------------------------------ embedding validation

def _client_returning(vectors):
    result = SimpleNamespace(embeddings=[SimpleNamespace(values=v) for v in vectors])
    return SimpleNamespace(models=SimpleNamespace(embed_content=lambda **kw: result))


def test_embeddings_must_have_the_expected_dimension():
    with patch.object(emb, "_get_client", return_value=_client_returning([[0.1] * 3])):
        with pytest.raises(emb.EmbeddingError):
            emb.embed_text("hello")
    with patch.object(emb, "_get_client", return_value=_client_returning([[0.1] * 768])):
        assert len(emb.embed_text("hello")) == 768


def test_embedding_batch_count_and_empty_text_are_checked():
    with patch.object(emb, "_get_client", return_value=_client_returning([[0.1] * 768])):
        with pytest.raises(emb.EmbeddingError):
            emb.embed_texts_batch(["a", "b"])                    # 1 vector for 2 texts
        with pytest.raises(emb.EmbeddingError):
            emb.embed_texts_batch(["a", "  "])
        with pytest.raises(emb.EmbeddingError):
            emb.embed_text("")
