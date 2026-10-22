-- Pro raises the Garage and History caps (ADR-0005/0006, issue #30).
--
-- Apply once to the Supabase project, after the Garage and History migrations: Dashboard > SQL Editor >
-- paste this file > Run. Behaviour is pinned by web/src/garageSchema.test.ts and
-- web/src/historySchema.test.ts (they run the migrations in order on a real Postgres) and by the live
-- External test web/src/external/supabaseTables.external.test.ts.
--
-- Where the numbers live: plan_caps below is the one place the caps are written. They are placeholders
-- until launch pricing is set (#33); to change one, edit its row (Dashboard > SQL Editor):
--   update public.plan_caps set garage_cap = 30 where plan = 'pro';
-- The functions read the row on every call, so nothing is redeployed.
--
-- How the database knows an account is Pro: it does not look it up (RevenueCat holds that fact and
-- nothing copies it here). The app passes p_pro on each save, from the Pro status it reads from
-- RevenueCat (owner's decision on #30). So the cap is only as honest as the app: a hand-edited request
-- could claim Pro and get the larger Garage and History. That costs storage, not scans (the Worker
-- charges those). A server-verified plan would replace p_pro with a lookup; plan_caps stays as it is.
--
--   p_pro = true     the Pro caps
--   p_pro = false    the Free caps (also what a caller that omits it gets, such as an older app build)
--   p_pro = null     the app could not read the plan. Both functions use the Pro caps, so a Pro account
--                    whose RevenueCat read failed is neither refused a Rig it paid for nor has its
--                    History pruned to the Free count. Storage stays bounded by the Pro caps.

create table public.plan_caps (
  plan        text primary key check (plan in ('free', 'pro')),
  garage_cap  int  not null check (garage_cap >= 1),
  history_cap int  not null check (history_cap >= 1)
);

insert into public.plan_caps (plan, garage_cap, history_cap) values
  ('free', 5, 10),
  ('pro', 25, 50);

-- A signed-in account may read the caps (the app says what Free keeps and what Pro adds) but nobody can
-- change them through the API: only the Dashboard edit above does. The functions below read it as definer.
alter table public.plan_caps enable row level security;
create policy plan_caps_select_all on public.plan_caps for select to authenticated using (true);
revoke all on public.plan_caps from public, anon, authenticated;
grant select on public.plan_caps to authenticated;

-- Garage: the same function as before with the cap taken from plan_caps. A new parameter is a new
-- function in Postgres, so the old one is dropped first.
drop function public.add_rig(text, text, jsonb, jsonb);

create function public.add_rig(
  p_idempotency_key text,
  p_nickname        text,
  p_truck           jsonb,
  p_trailer         jsonb,
  p_pro             boolean default false
) returns public.garage_rigs
language plpgsql
security definer
set search_path = ''
as $$
declare
  uid uuid := auth.uid();
  rig public.garage_rigs;
  cap int;
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

  select garage_cap into cap from public.plan_caps
   where plan = case when p_pro is false then 'free' else 'pro' end;

  if (select count(*) from public.garage_rigs where user_id = uid) >= cap then
    raise exception 'garage_full' using detail = cap::text, errcode = 'P0001';
  end if;

  insert into public.garage_rigs (user_id, nickname, truck, trailer, idempotency_key)
  values (uid, btrim(p_nickname), coalesce(p_truck, '{}'), coalesce(p_trailer, '{}'), p_idempotency_key)
  returning * into rig;
  return rig;
end;
$$;

revoke all on function public.add_rig(text, text, jsonb, jsonb, boolean) from public, anon;
grant execute on function public.add_rig(text, text, jsonb, jsonb, boolean) to authenticated;

-- History: the same function as before with the count taken from plan_caps.
drop function public.add_history_entry(text, text, text);

create function public.add_history_entry(
  p_idempotency_key text,
  p_rig_nickname    text,
  p_verdict         text,
  p_pro             boolean default false
) returns public.history_entries
language plpgsql
security definer
set search_path = ''
as $$
declare
  uid   uuid := auth.uid();
  entry public.history_entries;
  cap   int;
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

  select history_cap into cap from public.plan_caps
   where plan = case when p_pro is false then 'free' else 'pro' end;

  delete from public.history_entries
   where user_id = uid
     and id in (
       select id from public.history_entries
        where user_id = uid
        order by seq desc
       offset cap
     );

  return entry;
end;
$$;

revoke all on function public.add_history_entry(text, text, text, boolean) from public, anon;
grant execute on function public.add_history_entry(text, text, text, boolean) to authenticated;
