-- =========================================================================
-- Hybrid Search Functions (Supabase/Postgres)
-- These functions power the Precedent & Statute search (search_router.py).
-- They live in Supabase's database and are called via RPC from
-- ai_core/rag/vector_store.py (hybrid_search_judgments, hybrid_search_statutes).
--
-- IMPORTANT: This file is a reference copy. If you ever rebuild the database
-- from scratch, re-run both CREATE OR REPLACE statements below in the
-- Supabase SQL Editor, then run: NOTIFY pgrst, 'reload schema';
-- =========================================================================


-- -------------------------------------------------------------------------
-- 1. hybrid_search_judgments
-- Semantic (vector) + keyword hybrid search over the `judgments` table.
-- Fix applied: added 'extensions' to search_path so the pgvector `<=>`
-- operator resolves correctly (it was previously missing, causing
-- "operator does not exist: extensions.vector <=> extensions.vector").
-- -------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.hybrid_search_judgments(query_embedding vector, query_text text, match_count integer DEFAULT 5)
 RETURNS TABLE(id uuid, case_name text, court text, year integer, jurisdiction_type text, full_text text, combined_score double precision)
 LANGUAGE sql
 STABLE
 SET search_path TO 'public', 'extensions', 'pg_temp'
AS $function$
  select
    id, case_name, court, year, jurisdiction_type, full_text,
    (1 - (embedding <=> query_embedding)) * 0.7
      + ts_rank(to_tsvector('english', full_text), plainto_tsquery('english', query_text)) * 0.3
      as combined_score
  from judgments
  order by combined_score desc
  limit match_count;
$function$;


-- -------------------------------------------------------------------------
-- 2. hybrid_search_statutes
-- Keyword (full-text) search over the `statute_sections` table.
-- Note: this function does NOT use query_embedding/vector similarity —
-- it is pure keyword search via ts_rank. (query_embedding param is kept
-- only to match the RPC call signature from vector_store.py.)
-- Fix applied: boosts a row whose section number exactly matches a number
-- found in the query text (e.g. "Section 482 CrPC" -> section = '482'),
-- so exact section lookups rank first instead of being buried under
-- loosely-related keyword matches.
-- -------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.hybrid_search_statutes(query_embedding vector, query_text text, match_count integer DEFAULT 5)
 RETURNS TABLE(id bigint, act_name text, section_number text, section_title text, full_text text, combined_score double precision)
 LANGUAGE plpgsql
 STABLE
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
  or_query tsquery;
  section_num text;
BEGIN
  SELECT to_tsquery('english', string_agg(lexeme, ' | '))
  INTO or_query
  FROM unnest(tsvector_to_array(to_tsvector('english', query_text))) AS lexeme;

  IF or_query IS NULL THEN
    RETURN;
  END IF;

  -- extract a possible section number mentioned in the query (e.g. "482" from "Section 482 CrPC")
  SELECT (regexp_matches(query_text, '\d+[A-Za-z]?'))[1] INTO section_num;

  RETURN QUERY
  SELECT
    s.id,
    s.act_name,
    s.section AS section_number,
    s.heading AS section_title,
    s.text AS full_text,
    (
      ts_rank(to_tsvector('english', s.text || ' ' || coalesce(s.heading, '')), or_query)
      + CASE WHEN section_num IS NOT NULL AND s.section = section_num THEN 1.0 ELSE 0 END
    )::double precision AS combined_score
  FROM statute_sections s
  WHERE to_tsvector('english', s.text || ' ' || coalesce(s.heading, '')) @@ or_query
     OR (section_num IS NOT NULL AND s.section = section_num)
  ORDER BY combined_score DESC
  LIMIT match_count;
END;
$function$;


-- Run this after applying either function above, so Supabase's REST API
-- (PostgREST) picks up the change immediately instead of using a stale cache:
NOTIFY pgrst, 'reload schema';