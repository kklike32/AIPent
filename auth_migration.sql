-- Auth ownership + visibility migration for InsForge
-- Safe/idempotent: uses IF NOT EXISTS and DROP POLICY IF EXISTS.

alter table sessions
  add column if not exists user_id uuid references auth.users(id),
  add column if not exists visibility text default 'private';

alter table chunk_summaries
  add column if not exists user_id uuid references auth.users(id);

alter table final_pseudocode
  add column if not exists user_id uuid references auth.users(id);

alter table workflow_insights
  add column if not exists user_id uuid references auth.users(id);

alter table workflow_templates
  add column if not exists user_id uuid references auth.users(id),
  add column if not exists visibility text default 'private',
  add column if not exists shared_with_team boolean default false;

alter table workflow_search_index
  add column if not exists user_id uuid references auth.users(id),
  add column if not exists visibility text default 'private';

alter table agent_handoff_queue
  add column if not exists user_id uuid references auth.users(id);

alter table sessions
  drop constraint if exists sessions_visibility_check;
alter table sessions
  add constraint sessions_visibility_check check (visibility in ('private', 'team', 'public'));

alter table workflow_templates
  drop constraint if exists workflow_templates_visibility_check;
alter table workflow_templates
  add constraint workflow_templates_visibility_check check (visibility in ('private', 'team', 'public'));

alter table workflow_search_index
  drop constraint if exists workflow_search_index_visibility_check;
alter table workflow_search_index
  add constraint workflow_search_index_visibility_check check (visibility in ('private', 'team', 'public'));

alter table sessions enable row level security;
alter table chunk_summaries enable row level security;
alter table final_pseudocode enable row level security;
alter table workflow_insights enable row level security;
alter table workflow_templates enable row level security;
alter table workflow_search_index enable row level security;
alter table agent_handoff_queue enable row level security;

drop policy if exists "users can manage own sessions" on sessions;
create policy "users can manage own sessions"
on sessions
for all
using (user_id = auth.uid())
with check (user_id = auth.uid());

drop policy if exists "users can manage own chunk summaries" on chunk_summaries;
create policy "users can manage own chunk summaries"
on chunk_summaries
for all
using (user_id = auth.uid())
with check (user_id = auth.uid());

drop policy if exists "users can manage own final pseudocode" on final_pseudocode;
create policy "users can manage own final pseudocode"
on final_pseudocode
for all
using (user_id = auth.uid())
with check (user_id = auth.uid());

drop policy if exists "users can manage own workflow insights" on workflow_insights;
create policy "users can manage own workflow insights"
on workflow_insights
for all
using (user_id = auth.uid())
with check (user_id = auth.uid());

drop policy if exists "users can manage own workflow templates" on workflow_templates;
create policy "users can manage own workflow templates"
on workflow_templates
for all
using (user_id = auth.uid())
with check (user_id = auth.uid());

drop policy if exists "authenticated users can read team workflow templates" on workflow_templates;
create policy "authenticated users can read team workflow templates"
on workflow_templates
for select
using (
  visibility = 'team'
  or user_id = auth.uid()
);

drop policy if exists "users can manage own search index records" on workflow_search_index;
create policy "users can manage own search index records"
on workflow_search_index
for all
using (user_id = auth.uid())
with check (user_id = auth.uid());

drop policy if exists "authenticated users can read team search index records" on workflow_search_index;
create policy "authenticated users can read team search index records"
on workflow_search_index
for select
using (
  visibility = 'team'
  or user_id = auth.uid()
);

drop policy if exists "users can manage own agent handoff drafts" on agent_handoff_queue;
create policy "users can manage own agent handoff drafts"
on agent_handoff_queue
for all
using (user_id = auth.uid())
with check (user_id = auth.uid());
