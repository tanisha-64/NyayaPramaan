-- ==============================================================================
-- NyayaPramaan: Database Updates for Multi-Document Processing & Cancellations
-- Run this in your Supabase SQL Editor:
-- ==============================================================================

-- 1. Add status and filename to cases table if not present
alter table cases add column if not exists filename text;
alter table cases add column if not exists status text default 'processing';
-- status values: 'processing' | 'ready' | 'failed' | 'cancelled'

-- 2. Create session_documents table for linking multiple documents to a chat session
create table if not exists session_documents (
  id uuid default gen_random_uuid() primary key,
  session_id uuid references chat_sessions(id) on delete cascade,
  case_id uuid references cases(id) on delete cascade,
  filename text,
  created_at timestamp default now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.session_documents TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.session_documents TO authenticated;
ALTER TABLE public.session_documents DISABLE ROW LEVEL SECURITY;

-- 3. Create or replace multi-document similarity match function
create or replace function match_document_chunks_multi (
  query_embedding vector(768),
  target_case_ids uuid[],
  match_count int default 5
) returns table (
  id uuid,
  case_id uuid,
  page_number int,
  chunk_text text,
  similarity float
)
language sql
stable
as $$
  select
    id,
    case_id,
    page_number,
    chunk_text,
    1 - (embedding <=> query_embedding) as similarity
  from document_chunks
  where case_id = any(target_case_ids)
  order by embedding <=> query_embedding
  limit match_count;
$$;
