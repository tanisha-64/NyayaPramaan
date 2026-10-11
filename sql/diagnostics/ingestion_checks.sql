-- READ-ONLY checks. Every statement is a SELECT; nothing here changes data, policies or schema.
-- Run in the Supabase SQL editor (staging first). Paste the output when reporting results.

-- A. Which of the columns the code uses (defensively) exist?
select table_name, column_name, data_type
from information_schema.columns
where table_schema = 'public'
  and ((table_name = 'cases' and column_name in ('user_id','filename','case_text','summary','status','pages_processed','total_pages','rejection_reason','index_report','timeline','created_at'))
    or (table_name = 'document_chunks' and column_name in ('id','case_id','page_number','chunk_text','embedding','content_hash'))
    or (table_name = 'chat_sessions' and column_name in ('user_id','case_id','case_filename'))
    or (table_name = 'query_log' and column_name in ('user_id','entry_hash','previous_hash')))
order by table_name, column_name;

-- B. Embedding dimension must be 768 (the code validates 768 before inserting)
select a.attname, format_type(a.atttypid, a.atttypmod) as type
from pg_attribute a join pg_class c on c.oid = a.attrelid
where c.relname = 'document_chunks' and a.attname = 'embedding';

-- C. Indexing health: cases with no chunks, cases whose chunk pages exceed total_pages, duplicate chunks
select c.id, c.status, c.total_pages, count(d.id) as chunks
from cases c left join document_chunks d on d.case_id = c.id
group by c.id, c.status, c.total_pages
having count(d.id) = 0 and c.status = 'ready';

select case_id, page_number, md5(chunk_text) as h, count(*) as copies
from document_chunks group by case_id, page_number, md5(chunk_text) having count(*) > 1;

-- D. Row Level Security: which tables have it, and which policies exist
select c.relname as table_name, c.relrowsecurity as rls_enabled, c.relforcerowsecurity as rls_forced
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r'
  and c.relname in ('cases','document_chunks','chat_sessions','chat_messages','session_documents','query_log','judgments','statutes')
order by 1;

select schemaname, tablename, policyname, cmd, roles, qual, with_check
from pg_policies where schemaname = 'public' order by tablename, policyname;

-- E. The retrieval functions the backend calls: signature, language and SECURITY mode
--    (a SECURITY DEFINER function bypasses RLS: it must filter by case_id itself)
select p.proname, pg_get_function_identity_arguments(p.oid) as args, l.lanname, p.prosecdef as security_definer
from pg_proc p join pg_namespace n on n.oid = p.pronamespace join pg_language l on l.oid = p.prolang
where n.nspname = 'public' and p.proname in ('match_document_chunks','match_document_chunks_multi','hybrid_search_statutes','hybrid_search_judgments');

-- F. Storage bucket privacy (case-files must NOT be public)
select id, name, public from storage.buckets where name = 'case-files';
