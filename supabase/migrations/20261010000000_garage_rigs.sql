-- Garage (saved Rigs) synced to the account (ADR-0005, issue #28).
--
-- Apply once to the Supabase project: Dashboard > SQL Editor > paste this file > Run.
-- Behaviour is pinned by web/src/garageSchema.test.ts (runs this file on a real Postgres)
-- and by the live External test web/src/external/supabaseTables.external.test.ts.

create table public.garage_rigs (
  id              uuid        primary key default gen_random_uuid(),
  user_id         uuid        not null default auth.uid() references auth.users (id) on delete cascade,
  nickname        text        not null check (char_length(btrim(nickname)) between 1 and 80),
  truck           jsonb       not null default '{}' check (octet_length(truck::text) <= 8192),
  trailer         jsonb       not null default '{}' check (octet_length(trailer::text) <= 8192),
  last_used_at    timestamptz not null default now(),
  created_at      timestamptz not null default now(),
  -- the client-supplied key of the add that created this row; a retry of that add finds the row
  idempotency_key text        not null check (char_length(idempotency_key) between 1 and 100)
);

-- One Rig per nickname per account, ignoring case (a saved nickname is refreshed, never duplicated),
-- and one row per idempotency key per account.
create unique index garage_rigs_user_nickname_key on public.garage_rigs (user_id, lower(btrim(nickname)));
create unique index garage_rigs_user_idempotency_key on public.garage_rigs (user_id, idempotency_key);

alter table public.garage_rigs enable row level security;

-- Rows are visible and writable only by the owning account.
create policy garage_rigs_select_own on public.garage_rigs
  for select to authenticated using (user_id = auth.uid());
create policy garage_rigs_update_own on public.garage_rigs
  for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy garage_rigs_delete_own on public.garage_rigs
  for delete to authenticated using (user_id = auth.uid());

-- Supabase grants new tables to every API role by default; start from nothing.
revoke all on public.garage_rigs from public, anon, authenticated;
grant select on public.garage_rigs to authenticated;
-- Changing an existing Rig (including its last-used time) consumes no capacity, so a plain
-- last-write-wins update is allowed, but only on these columns: ownership and the idempotency
-- key are fixed. Deleting your own Rig frees its slot. There is deliberately no insert grant: new
-- Rigs go through add_rig(), the only path that checks capacity.
grant update (nickname, truck, trailer, last_used_at) on public.garage_rigs to authenticated;
grant delete on public.garage_rigs to authenticated;

-- Adds a Rig to the caller's Garage, enforcing the Free cap atomically.
--   * A repeat of an earlier add (same key) returns that Rig and never counts again, even if the
--     Garage has since filled up.
--   * A nickname already in the Garage is refreshed in place (no capacity used).
--   * Otherwise a full Garage raises 'garage_full' with the cap in DETAIL.
-- The per-account advisory lock serialises concurrent adds from the same account, so two devices
-- adding at once cannot both see room for one more.
create function public.add_rig(
  p_idempotency_key text,
  p_nickname        text,
  p_truck           jsonb,
  p_trailer         jsonb
) returns public.garage_rigs
language plpgsql
security definer
set search_path = ''
as $$
declare
  -- Free plan cap. Pro raises it with the entitlement work (#24); the number is a pricing decision.
  free_cap constant int := 5;
  uid      uuid := auth.uid();
  rig      public.garage_rigs;
begin
  if uid is null then
    raise exception 'not_authenticated' using errcode = '28000';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(uid::text, 0));

  select * into rig from public.garage_rigs
   where user_id = uid and idempotency_key = p_idempotency_key;
  if found then
    return rig;
  end if;

  update public.garage_rigs
     set truck = coalesce(p_truck, '{}'), trailer = coalesce(p_trailer, '{}'), last_used_at = now()
   where user_id = uid and lower(btrim(nickname)) = lower(btrim(p_nickname))
   returning * into rig;
  if found then
    return rig;
  end if;

  if (select count(*) from public.garage_rigs where user_id = uid) >= free_cap then
    raise exception 'garage_full' using detail = free_cap::text, errcode = 'P0001';
  end if;

  insert into public.garage_rigs (user_id, nickname, truck, trailer, idempotency_key)
  values (uid, btrim(p_nickname), coalesce(p_truck, '{}'), coalesce(p_trailer, '{}'), p_idempotency_key)
  returning * into rig;
  return rig;
end;
$$;

revoke all on function public.add_rig(text, text, jsonb, jsonb) from public, anon;
grant execute on function public.add_rig(text, text, jsonb, jsonb) to authenticated;
