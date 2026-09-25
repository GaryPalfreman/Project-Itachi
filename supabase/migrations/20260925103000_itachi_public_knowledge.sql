-- Itachi public knowledge: free-tier-friendly, provenance-aware, read-only to public clients.
create extension if not exists pgcrypto;

create table if not exists public.itachi_public_knowledge (
  id uuid primary key default gen_random_uuid(),
  url text not null unique,
  title text not null,
  content text not null,
  source_type text not null default 'web',
  license text not null default 'UNKNOWN',
  content_sha256 text not null,
  fetched_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists itachi_public_knowledge_fetched_at_idx
  on public.itachi_public_knowledge (fetched_at desc);

alter table public.itachi_public_knowledge enable row level security;

drop policy if exists "public can read itachi knowledge" on public.itachi_public_knowledge;
create policy "public can read itachi knowledge"
  on public.itachi_public_knowledge
  for select
  to anon, authenticated
  using (true);

revoke insert, update, delete on public.itachi_public_knowledge from anon, authenticated;
grant select on public.itachi_public_knowledge to anon, authenticated;

insert into storage.buckets (id, name, public)
values ('itachi-recovery', 'itachi-recovery', false)
on conflict (id) do nothing;
