-- ==============================================================================
-- NyayaPramaan: Database Updates for Multi-Document Processing & Cancellations
-- Run this in your Supabase SQL Editor:
-- ==============================================================================

-- 1. Add status and filename to cases table if not present
alter table cases add column if not exists filename text;
alter table cases add column if not exists status text default 'processing';
-- status values: 'processing' | 'ready' | 'failed' | 'cancelled' | 'rejected'

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

-- ==============================================================================
-- 4. Progress tracking & rejection support (background processing + live UX)
-- ==============================================================================
-- Live progress: pages_processed / total_pages for frontend polling
alter table cases add column if not exists pages_processed int default 0;
alter table cases add column if not exists total_pages int default 0;

-- Rejection reason: stored when classifier rejects a document in background
alter table cases add column if not exists rejection_reason text;

-- File URL: stored after background storage upload completes
alter table cases add column if not exists file_url text;

-- ==============================================================================
-- 5. User Game & Quiz Progress Isolation Table
-- ==============================================================================
create table if not exists user_game_progress (
  id uuid default gen_random_uuid() primary key,
  user_id uuid not null,
  total_points int default 0,
  scenarios_completed int default 0,
  streak int default 0,
  best_streak int default 0,
  updated_at timestamp default now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_game_progress TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_game_progress TO authenticated;
ALTER TABLE public.user_game_progress DISABLE ROW LEVEL SECURITY;

