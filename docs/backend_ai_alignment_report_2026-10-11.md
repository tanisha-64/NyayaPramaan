# Backend and AI/ML alignment with the README — change report (2026-10-11)

Scope: backend and AI/ML code only. Nothing was pushed, deployed or migrated; no production data, secrets or `.env` were read or used.
Backup of the pre-change tree: `C:\Users\dell\OneDrive\Desktop\Nyayapramaan_backup_20261011` (see "Restore" below).

## 0. Something you need to know first

The README and `ci.yml` describe `tests/`, `eval/`, `sql/proposed|diagnostics/`, `docs/*.md` and `constraints-ci.txt`. **None of them existed in the working tree at the start of this session** (the four old `tests/test_*.py` and two `docs/*.md` are tracked in git but deleted from disk; the rest were never on disk). I did not restore or delete anything from git. I created new files in `tests/`, `eval/`, `sql/` and `docs/` under new names. If you recover the lost folders (OneDrive recycle bin / another machine), keep both sets and diff them. `constraints-ci.txt` is still missing, so the CI workflow as written would fail on `pip install -c constraints-ci.txt`.

## 1. README architecture → implementation

| README component | Implementation | State |
|---|---|---|
| Input guardrails | `ai_core/guardrails/input_guard.py` | pre-existing, unchanged |
| Intent classifier (4-way) | `ai_core/router/intent_classifier.py` | fixed one routing defect (§2) |
| Async ingestion, live progress | `backend/routers/document_router.py`, `ai_core/rag/document_chunker.py` | pre-existing; hardened (§2) |
| Classifier (legal-case gate) | `ai_core/rag/document_classifier.py` | **rewritten** (content-based, fail-closed) |
| OCR / extraction | `ai_core/rag/document_reader.py` | local OCR sample added for scans |
| Chunker + embeddings + pgvector | `document_chunker.py`, `embeddings.py`, `vector_store.py` | provenance, dimension checks, degradation |
| Multi-doc retrieval, hybrid | `vector_store.search_document_chunks` | pre-existing; no-embedding fallback added |
| CRAG | `ai_core/rag/crag_corrector.py`, `retrieval_quality.py` | **hardened** (host matching, official vs secondary, bounded) |
| TrustAgent | `ai_core/trustagent/*` | table-claim gap fixed, cap visible, provenance in sources |
| Judge / Self-RAG | `evaluation/llm_judge.py`, `rag/self_rag.py` | unchanged; behaviour now covered by tests |
| PII redaction / hash-chain log | `guardrails/output_guard.py`, `trust_log/hash_chain.py` | redaction applied at provider/log boundaries |
| Timeline | `ai_core/timeline/extractor.py` | **rewritten** (deterministic, page-linked) |
| Memory / follow-ups | `ai_core/memory/query_rewriter.py` | unchanged; covered by tests |
| Access control | `backend/security.py`, routers | audited; gaps fixed (§2) |
| Evaluation | `ai_core/evaluation/*`, `eval/` | datasets recreated; routing/policy eval added |

## 2. Confirmed issues and fixes (each has a test)

| # | Confirmed problem (evidence) | Fix |
|---|---|---|
| 1 | Classifier accepted on ONE keyword, including substrings of the filename (`"fir"` in "first", `"act"`, `"vs"`), and **accepted whenever the LLM failed** (code comment: "fail-SAFE toward ACCEPTING"). | Content-based accept / reject / uncertain; record-signal vs reference-signal groups (law text or a textbook is not a case); LLM tie-break only for ambiguous cases and **fail-closed**; filename never counts as legal evidence. |
| 2 | Upload checks were extension + `%PDF` prefix only. Encrypted/corrupt/huge PDFs reached the reader. | Magic-byte check per format, encrypted (password) PDF, corrupt PDF, page cap (`MAX_PDF_PAGES`, 600) rejected with clear 4xx before any processing. |
| 3 | Scanned PDF with no text was classified on the *filename*. | Local OCR sample (if installed) else rejected as unreadable. |
| 4 | Timeline: one unbounded LLM call over the whole text, no page, never stored (`/status` always returned `""`), re-run on every `GET /case/{id}`. | Deterministic extractor: each event = date found in the text + its sentence + page; hearing status derived from wording (listed ≠ recorded); stored at upload; also used as evidence for chronology questions. |
| 5 | TrustAgent's claim extractor **deleted markdown table rows** (`re.sub(r"\|.*\|","")`): table claims were never verified. | Tables flattened into claims; hitting the 10-claim cap is reported (`trust_summary.claims_capped`). |
| 6 | Identifiers reached providers: the query, evidence, the model's own draft and claims, the audit log (`query_log`), summary/brief prompts, web-search queries. Phone regex also redacted any 10-digit number (case/account numbers). | `redact_pii` at each provider/log boundary; precise phone/Aadhaar rules; stored document and page citations untouched. Found by a test that failed on the first run (draft and claims leaked). |
| 7 | CRAG allowlist used substring matching: `indiacode.nic.in.evil.example` passed. No distinction between official and secondary sources; no timeout. | Parsed-hostname matching; official vs secondary classes (labelled in sources and answer); official-first, ≤3 searches; timeout. |
| 8 | No IPC/BNS period logic beyond a fixed sentence. | `trustagent/legal_framework.py`: reads only dates/acts stated in the question; hedged note + "law as of" date; never maps section numbers. |
| 9 | Query-embedding failure aborted the whole request. | Degrades to keyword-only retrieval and says so (`retrieval.degraded`). |
| 10 | Embedding responses were not validated (count / 768 dims / empty). | `EmbeddingError` on any mismatch; indexing reports the failure (never silent). |
| 11 | "Adverse possession" in a general question with a document open was routed MIXED (the word "possession" is a document signal). Found by the evaluation. | Concept phrases ignored for document-signal detection. |
| 12 | No paragraph provenance. | Explicit paragraph markers are kept at line starts and read back; sources now carry `document`, `page`, `paragraphs` (only if present in the text), `snippet`. |
| 13 | `/case/{id}/brief` (LLM call) had no rate limit; `/search/precedents` payload unbounded; LLM calls had no timeout/token cap; `/status` hid partial indexing. | Rate limit, bounds, gateway timeout (60 s) and 8192-token cap (env-tunable; shared with quiz/game, they need little), `indexing_complete` + `index_warning`. |

Not changed on purpose: statuses written to the DB (`processing/ready/failed`), JSON field names the frontend reads (only fields were **added**), RLS, RPCs, roles.

## 3. Files

Modified (backend/AI only): `ai_core/guardrails/output_guard.py`, `ai_core/llm_gateway.py`, `ai_core/rag/{crag_corrector,document_chunker,document_classifier,document_reader,embeddings,summarizer,vector_store}.py`, `ai_core/router/intent_classifier.py`, `ai_core/timeline/extractor.py`, `ai_core/trustagent/{claim_extractor,evidence_report,pipeline}.py`, `ai_core/evaluation/{fake_supabase,rag_eval,rag_suites}.py`, `backend/rate_limit.py`, `backend/security.py`, `backend/routers/{case,chat,document,search}_router.py`, `.env.example` (comments only).
Added: `ai_core/rag/provenance.py`, `ai_core/trustagent/legal_framework.py`, `ai_core/evaluation/routing_eval.py`, `eval/golden/*.json`, `eval/thresholds.json`, `tests/**`, `sql/proposed/004_*.sql`, `sql/diagnostics/ingestion_checks.sql`, this report.
Deleted: none. Not touched: frontend, `app/`, Quiz, Right Rakshak (game), Daily News, `quiz_router.py`, `news_router.py`, `game_router.py`, the lawyer workspace.

## 4. How to verify locally

```
backend\venv\Scripts\python.exe -m pytest tests -q                       # unit + behaviour (hermetic: network blocked, dummy keys)
backend\venv\Scripts\python.exe -m ai_core.evaluation.rag_eval --check   # retrieval/leakage/failure-mode gates
backend\venv\Scripts\python.exe -m ai_core.evaluation.routing_eval --check
backend\venv\Scripts\python.exe -m ai_core.evaluation.judge_eval         # offline lexical BASELINE (not the LLM judge)
```
Manual checks (staging): upload a resume PDF (expect 422 + polite message), a password-protected PDF (422), a real judgment (200, `status: processing` → `ready`), ask a document question (sources carry page + paragraph + snippet), ask "What is BNS section 303?" with the document open (no case text in the answer, official/secondary label), ask in Hindi/Hinglish, ask "when was the next hearing?", upload as user B and try user A's `case_id` (indistinguishable from missing).
Opt-in integration tests (read-only DB, your staging keys): `set RUN_INTEGRATION=1` then `pytest tests/integration -q`; add `RUN_LIVE_LLM=1` for the live judge/CRAG tests.

## 5. Results (this run)

* `pytest tests`: **211 passed, 6 skipped** (the 6 are the opt-in integration tests; they were **not run**). Baseline characterization tests (13) passed on the untouched code before any change.
* `rag_eval` (offline, stub embeddings, 5-chunk corpus): Recall@3 1.0, MRR 0.944, nDCG@3 0.955, correct abstention 1.0, hard-negative abstention 0.5 (a lexical gate cannot refuse look-alike questions; the LLM judge must), cross-case chunk rate 0.0 incl. with a vector function that ignores the case filter, recall with RPCs down 0.97, with no query embedding 1.0, conflict both-pages recall 1.0. **These saturate: the corpus is 5 chunks and K=3. They are regression gates, not a measure of real accuracy.**
* `routing_eval`: routing 16/16 (after fix #11; 15/16 before), legal-period 8/8, source policy 10/10, identifier leak 0, timeline recall 1.0 / precision 1.0, false "recorded hearing" 0. One timeline label was corrected after the first run (my labelling mistake; recorded in the dataset).
* `judge_eval` offline baseline (lexical, **not** the LLM judge): accuracy 0.68, unsafe-support rate 0.27 on 25 pairs labelled by one annotator (the AI assistant, not a lawyer). **No LLM-judge accuracy figure exists.**
* Thresholds in `eval/thresholds.json` were set from the first run with margin: they detect regression only.

## 6. Not verified / limitations

* Never run against real Supabase, Gemini, Groq, OpenRouter or live web search. Real embedding quality, real answer quality, real LLM-judge accuracy and CRAG against the live web are **unmeasured**.
* The real definitions of `match_document_chunks*`, `hybrid_search_*`, table DDL, RLS policies and the storage bucket's privacy are **unknown** (not in the repo). `sql/diagnostics/ingestion_checks.sql` (read-only) answers these. The application re-checks case ownership of RPC rows in code, so a leaky RPC cannot leak through, but RLS has not been audited.
* Service-role key: every route uses it (bypasses RLS). Per-route ownership checks were reviewed and tested for cases, documents, sessions and messages; they live in code, not in the database.
* `ADMIN_EMAILS` falls back to a hard-coded address in `supabase_auth.py` when unset. Left as is (changing it could lock the owner out); set the variable in production.
* Paragraph numbers appear only when the passage text carries an explicit marker; continuation chunks report none (stated in the response). Page numbers are real for PDFs/page-broken text and flagged approximate otherwise.
* Local OCR needs Tesseract/pdf2image; they are not installed in the test venv, so OCR paths were tested with a stub. Gemini OCR (a provider call) still happens for scanned PDFs *before* classification: unavoidable, because classification needs the text.
* The claim judge is an LLM; `claim_support_ratio` is a documented ratio over its verdicts, not a probability of correctness.
* Multi-instance deployments: the in-process indexing lock and rate limiter do not coordinate across instances (migration 004 adds a DB-level duplicate guard).

## 7. Proposed migration (not applied)

`sql/proposed/004_chunk_dedupe_and_optional_columns.sql`: optional `cases.index_report`, `cases.timeline`, generated `content_hash` + unique index on `(case_id, page_number, content_hash)`. Reasons, risks (index build fails if duplicates exist → step 0 lists them), verification and rollback are in the file. The application works without it.

## 8. Decisions for you

1. **Statutes / law-student material are no longer accepted as uploads** (spec: case-related documents only). The old message allowed them. Say so if the product should keep that.
2. Phone numbers: only Indian-mobile-format numbers or numbers next to a "phone/mobile/Aadhaar" word are masked (bare 10-digit numbers are kept).
3. Whether to restore the four old `tests/test_*.py` and two `docs/*.md` from git (they are tracked; I did not touch them).

## Restore

The backup folder holds `ai_core/`, `backend/` (without `venv`), `trust_log/`, `data/`, config files and `working_tree_vs_HEAD.diff` (a diff of tracked files against HEAD `HEAD.txt`). `app/` could not be copied (OneDrive placeholders) and was not modified. `.env` was deliberately not copied. To undo my changes to a file, copy it back from the backup; nothing was deleted or reverted without you.
