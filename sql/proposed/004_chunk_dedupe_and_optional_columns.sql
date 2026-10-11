-- PROPOSED migration 004 -- NOT APPLIED. Nothing in the application requires it: the code works without it.
-- Review, run the read-only checks in sql/diagnostics/ingestion_checks.sql first, and apply on STAGING before production.
--
-- WHY
--   1. Duplicate chunks: two indexers of the same case running in DIFFERENT app instances can both insert (the in-process
--      lock only covers one instance). A unique index makes the database refuse the second copy.
--   2. Optional columns the code already writes/reads defensively (it falls back when they are absent):
--        cases.index_report  jsonb  - structured indexing outcome (complete / failed pages / ocr pages ...)
--        cases.timeline      text   - stored, evidence-linked timeline created at upload
--
-- WHAT IT DOES NOT TOUCH
--   RLS policies, RPC functions, storage buckets, roles, existing rows' contents. No data is deleted.
--
-- RISKS
--   * The unique index FAILS to build if duplicate chunks already exist. Step 0 lists them; remove duplicates (keep the
--     lowest id per group) before step 2. Do NOT run the cleanup blindly in production.
--   * ADD COLUMN with no default is metadata-only in PostgreSQL 11+: no table rewrite, no long lock.
--   * CREATE INDEX CONCURRENTLY cannot run inside a transaction block: run it as its own statement.
--
-- VERIFY (after applying)
--   select column_name from information_schema.columns where table_name='cases' and column_name in ('index_report','timeline');
--   select indexname from pg_indexes where tablename='document_chunks' and indexname='document_chunks_case_page_hash_uq';
--   Re-upload a small document twice; select count(*) from document_chunks where case_id = '<id>' must not change.
--
-- ROLLBACK
--   drop index concurrently if exists document_chunks_case_page_hash_uq;
--   alter table document_chunks drop column if exists content_hash;
--   alter table cases drop column if exists index_report; alter table cases drop column if exists timeline;  -- only if they did not exist before

-- 0. read-only: duplicates that would block the unique index
select case_id, page_number, md5(chunk_text) as h, count(*) as copies, min(id::text) as keep_id
from document_chunks
group by case_id, page_number, md5(chunk_text)
having count(*) > 1;

-- 1. optional columns
alter table cases add column if not exists index_report jsonb;
alter table cases add column if not exists timeline text;

-- 2. dedupe guard (generated column keeps the application unchanged: it never has to supply the hash)
alter table document_chunks add column if not exists content_hash text generated always as (md5(chunk_text)) stored;
create unique index concurrently if not exists document_chunks_case_page_hash_uq
    on document_chunks (case_id, page_number, content_hash);
