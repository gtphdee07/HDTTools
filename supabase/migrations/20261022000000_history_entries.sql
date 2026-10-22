-- History (past checks) synced to the account (ADR-0005, issue #29).
--
-- Apply once to the Supabase project: Dashboard > SQL Editor > paste this file > Run.
-- Behaviour is pinned by web/src/historySchema.test.ts (runs this file on a real Postgres)
-- and by the live External test web/src/external/supabaseTables.external.test.ts.

create table public.history_entries (
  id              uuid        primary key default gen_random_uuid(),
  user_id         uuid        not null default auth.uid() references auth.users (id) on delete cascade,
  rig_nickname    text        not null check (char_length(btrim(rig_nickname)) between 1 and 80),
  verdict         text        not null check (verdict in ('pass', 'fail', 'partial', 'insufficient')),
  checked_at      timestamptz not null default clock_timestamp(),
  -- the client-supplied key of the add that created this row; a retry of that add finds the row
  idempotency_key text        not null check (char_length(idempotency_key) between 1 and 100)
);

-- One row per idempotency key per account; the index also serves "newest first" and "oldest to prune".
create unique index history_entries_user_idempotency_key on public.history_entries (user_id, idempotency_key);
create index history_entries_user_checked_at on public.history_entries (user_id, checked_at desc, id desc);

alter table public.history_entries enable row level security;

-- Rows are visible only to the owning account.
create policy history_entries_select_own on public.history_entries
  for select to authenticated using (user_id = auth.uid());

-- Supabase grants new tables to every API role by default; start from nothing. A History entry is a
-- record of a past result: it is read, never edited, and removed only by the cap below (or with its
-- account). There is deliberately no insert grant: new entries go through add_history_entry(), the only
-- path that applies the cap.
revoke all on public.history_entries from public, anon, authenticated;
grant select on public.history_entries to authenticated;

-- Adds a check to the caller's History and drops whatever falls past the cap, oldest first.
--   * A repeat of an earlier add (same key) returns that entry and adds nothing, so a retried request
--     is never counted twice. (An entry that has already been pruned is no longer found, so a retry
--     that arrives after it rolled off, ten checks later, would add it again; the client retries at
--     once, so it does not.)
-- The per-account advisory lock serialises adds from the same account, so two devices finishing a
-- check at the same moment cannot both prune on a stale count.
create function public.add_history_entry(
  p_idempotency_key text,
  p_rig_nickname    text,
  p_verdict         text
) returns public.history_entries
language plpgsql
security definer
set search_path = ''
as $$
declare
  -- Free plan cap. Pro raises it with the entitlement work (#24); the number is a pricing decision.
  free_cap constant int := 10;
  uid      uuid := auth.uid();
  entry    public.history_entries;
begin
  if uid is null then
    raise exception 'not_authenticated' using errcode = '28000';
  end if;

  perform pg_advisory_xact_lock(hashtextextended('history:' || uid::text, 0));

  select * into entry from public.history_entries
   where user_id = uid and idempotency_key = p_idempotency_key;
  if found then
    return entry;
  end if;

  insert into public.history_entries (user_id, rig_nickname, verdict, idempotency_key)
  values (uid, btrim(p_rig_nickname), p_verdict, p_idempotency_key)
  returning * into entry;

  delete from public.history_entries
   where user_id = uid
     and id in (
       select id from public.history_entries
        where user_id = uid
        order by checked_at desc, id desc
       offset free_cap
     );

  return entry;
end;
$$;

revoke all on function public.add_history_entry(text, text, text) from public, anon;
grant execute on function public.add_history_entry(text, text, text) to authenticated;
