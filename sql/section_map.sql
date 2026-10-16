create table if not exists section_map (
  id bigserial primary key,
  new_act text not null,          -- BNS | BNSS | BSA
  new_section text not null,      -- e.g. 103(1)
  new_top text not null,          -- e.g. 103
  subject text,
  old_act text not null,          -- IPC | CrPC | IEA
  old_section text,               -- NULL = NEW (no old equivalent)
  change_type text not null,      -- NO_CHANGE | MODIFIED | NEW
  pdf_page int,
  unique (new_act, new_section, old_section)
);
create index if not exists sm_old on section_map (old_act, old_section);
create index if not exists sm_new on section_map (new_act, new_top);
alter table section_map enable row level security;