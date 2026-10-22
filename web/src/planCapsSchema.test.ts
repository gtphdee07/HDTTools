// @vitest-environment node
import { readFileSync } from 'node:fs';
import { PGlite } from '@electric-sql/pglite';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

// Service-boundary tests for the plan caps (#30): the committed Supabase migrations are run in order on a
// real Postgres (PGlite) and driven as the `authenticated` role, the way PostgREST drives them, so what
// is pinned is the plan's effect on add_rig and add_history_entry as written, not a re-implementation.
// The Free-plan behaviour of the two functions is pinned in garageSchema.test.ts and historySchema.test.ts;
// this file is what Pro (and an app that could not read its plan) changes. No cap number is written here:
// they are read from plan_caps, where the one copy lives, and are placeholders until launch pricing (#33).

const MIGRATIONS = [
  '20261010000000_garage_rigs.sql',
  '20261022000000_history_entries.sql',
  '20261023000000_plan_caps.sql',
].map((file) => readFileSync(new URL(`../../supabase/migrations/${file}`, import.meta.url), 'utf8'));

const ALICE = '00000000-0000-4000-8000-00000000000a';

let db: PGlite;
let FREE_RIGS: number;
let PRO_RIGS: number;
let FREE_CHECKS: number;
let PRO_CHECKS: number;

beforeAll(async () => {
  db = new PGlite();
  await db.exec(`
    create schema auth;
    create table auth.users (id uuid primary key);
    create function auth.uid() returns uuid language sql stable as $$
      select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
    $$;
    create role anon nologin;
    create role authenticated nologin;
    grant usage on schema auth, public to anon, authenticated;
    grant execute on function auth.uid() to anon, authenticated;
    insert into auth.users values ('${ALICE}');
  `);
  for (const migration of MIGRATIONS) await db.exec(migration);
  const caps = await db.query<{ plan: string; garage_cap: number; history_cap: number }>('select * from public.plan_caps');
  const of = (plan: string) => caps.rows.find((r) => r.plan === plan)!;
  FREE_RIGS = of('free').garage_cap;
  PRO_RIGS = of('pro').garage_cap;
  FREE_CHECKS = of('free').history_cap;
  PRO_CHECKS = of('pro').history_cap;
});

afterAll(async () => {
  await db.close();
});

async function asAlice<T>(fn: () => Promise<T>): Promise<T> {
  await db.exec(`set role authenticated; select set_config('request.jwt.claim.sub', '${ALICE}', false);`);
  try {
    return await fn();
  } finally {
    await db.exec(`reset role; select set_config('request.jwt.claim.sub', '', false);`);
  }
}

// `pro` is what the app reports: true, false, null (could not read the plan), or undefined (an older
// app build that does not send it).
const addRig = (key: string, nickname: string, pro?: boolean | null) =>
  asAlice(() =>
    pro === undefined
      ? db.query('select * from public.add_rig($1, $2, $3, $4)', [key, nickname, '{}', '{}'])
      : db.query('select * from public.add_rig($1, $2, $3, $4, $5)', [key, nickname, '{}', '{}', pro]),
  );

const addEntry = (key: string, nickname: string, pro?: boolean | null) =>
  asAlice(() =>
    pro === undefined
      ? db.query('select * from public.add_history_entry($1, $2, $3)', [key, nickname, 'pass'])
      : db.query('select * from public.add_history_entry($1, $2, $3, $4)', [key, nickname, 'pass', pro]),
  );

const rigCount = async () => (await asAlice(() => db.query('select 1 from public.garage_rigs'))).rows.length;
const checks = async () =>
  (await asAlice(() => db.query<{ rig_nickname: string }>('select rig_nickname from public.history_entries order by seq desc'))).rows.map(
    (r) => r.rig_nickname,
  );

async function fillRigs(count: number, pro: boolean | null | undefined) {
  await db.exec('delete from public.garage_rigs');
  for (let i = 1; i <= count; i++) await addRig(`fill-${i}`, `Rig ${i}`, pro);
}

async function fillChecks(count: number, pro: boolean | null | undefined) {
  await db.exec('delete from public.history_entries');
  for (let i = 1; i <= count; i++) await addEntry(`fill-${i}`, `Check ${i}`, pro);
}

const refusal = (p: Promise<unknown>) => p.then(() => null, (e: Error & { detail?: string }) => e);

describe('the plan caps', () => {
  it('give Pro more Rigs and more checks than Free', () => {
    expect(PRO_RIGS).toBeGreaterThan(FREE_RIGS);
    expect(PRO_CHECKS).toBeGreaterThan(FREE_CHECKS);
  });

  it('can be read by a signed-in account, so the app can say what Free keeps and Pro adds, but not by a signed-out caller', async () => {
    const seen = await asAlice(() => db.query<{ plan: string }>('select plan from public.plan_caps order by plan'));
    expect(seen.rows.map((r) => r.plan)).toEqual(['free', 'pro']);

    await db.exec(`set role anon`);
    try {
      await expect(db.query('select * from public.plan_caps')).rejects.toThrow(/permission denied/);
    } finally {
      await db.exec('reset role');
    }
  });

  it('cannot be changed through the API, so an account cannot raise its own cap', async () => {
    await expect(asAlice(() => db.query('update public.plan_caps set garage_cap = 1000'))).rejects.toThrow(/permission denied/);
    await expect(asAlice(() => db.query("insert into public.plan_caps values ('pro', 1000, 1000)"))).rejects.toThrow(/permission denied/);
    await expect(asAlice(() => db.query('delete from public.plan_caps'))).rejects.toThrow(/permission denied/);
  });
});

describe('add_rig by plan', () => {
  it('lets a Pro account keep Rigs past the Free cap, up to the Pro cap, and says the Pro cap when full', async () => {
    await fillRigs(PRO_RIGS, true);
    expect(await rigCount()).toBe(PRO_RIGS);

    const refused = await refusal(addRig('one-too-many', 'One Too Many', true));
    expect(refused?.message).toBe('garage_full');
    expect(refused?.detail).toBe(String(PRO_RIGS));
    expect(await rigCount()).toBe(PRO_RIGS);
  });

  it('holds a Free account at the Free cap, and an older app build that sends no plan counts as Free', async () => {
    for (const pro of [false, undefined]) {
      await fillRigs(FREE_RIGS, pro);

      const refused = await refusal(addRig('one-too-many', 'One Too Many', pro));
      expect(refused?.message).toBe('garage_full');
      expect(refused?.detail).toBe(String(FREE_RIGS));
    }
  });

  it('uses the Pro cap when the app could not read the plan, so a Pro account is not refused a Rig', async () => {
    await fillRigs(FREE_RIGS, true);

    await addRig('unknown-plan', 'Sixth Rig', null);

    expect(await rigCount()).toBe(FREE_RIGS + 1);
  });

  it('gives the larger cap straight away once the app reports Pro, with no change to the Rigs already saved', async () => {
    await fillRigs(FREE_RIGS, false);
    expect((await refusal(addRig('before-purchase', 'Extra', false)))?.message).toBe('garage_full');

    await addRig('after-purchase', 'Extra', true);

    expect(await rigCount()).toBe(FREE_RIGS + 1);
  });

  it('follows an edit to the cap row, so launch pricing needs no redeploy', async () => {
    await fillRigs(FREE_RIGS, false);
    await db.exec(`update public.plan_caps set garage_cap = ${FREE_RIGS + 1} where plan = 'free'`);
    try {
      await addRig('now-fits', 'Extra', false);
      expect((await refusal(addRig('still-too-many', 'Another', false)))?.detail).toBe(String(FREE_RIGS + 1));
    } finally {
      await db.exec(`update public.plan_caps set garage_cap = ${FREE_RIGS} where plan = 'free'`);
    }
  });

  it('answers a retry of an add that landed under Pro with the Rig, even when this retry reports Free', async () => {
    await fillRigs(FREE_RIGS, true);
    const first = await addRig('past-free-cap', 'Past The Cap', true);

    const retried = await addRig('past-free-cap', 'Past The Cap', false);

    expect(retried.rows[0]).toMatchObject({ id: (first.rows[0] as { id: string }).id });
  });
});

describe('add_history_entry by plan', () => {
  it('keeps a Pro account’s checks past the Free count, up to the Pro count, then drops the oldest', async () => {
    await fillChecks(PRO_CHECKS, true);
    expect(await checks()).toHaveLength(PRO_CHECKS);

    await addEntry('one-more', 'Check Newest', true);

    const kept = await checks();
    expect(kept).toHaveLength(PRO_CHECKS);
    expect(kept[0]).toBe('Check Newest');
    expect(kept).not.toContain('Check 1');
  });

  it('keeps a Free account to the Free count, and an older app build that sends no plan counts as Free', async () => {
    for (const pro of [false, undefined]) {
      await fillChecks(FREE_CHECKS + 3, pro);
      expect(await checks()).toHaveLength(FREE_CHECKS);
    }
  });

  it('does not prune a Pro account’s History to the Free count when the app could not read the plan', async () => {
    await fillChecks(FREE_CHECKS + 1, true);

    await addEntry('unknown-plan', 'Check Newest', null);

    const kept = await checks();
    expect(kept).toHaveLength(FREE_CHECKS + 2);
    expect(kept[0]).toBe('Check Newest');
  });

  it('prunes to the Pro count when the app could not read the plan, so unknown never grows History without bound', async () => {
    await fillChecks(PRO_CHECKS, true);

    await addEntry('unknown-plan', 'Check Newest', null);

    expect(await checks()).toHaveLength(PRO_CHECKS);
  });

  it('follows an edit to the cap row, so launch pricing needs no redeploy', async () => {
    await fillChecks(FREE_CHECKS, false);
    await db.exec(`update public.plan_caps set history_cap = ${FREE_CHECKS + 1} where plan = 'free'`);
    try {
      await addEntry('now-fits', 'Check Newest', false);
      expect(await checks()).toHaveLength(FREE_CHECKS + 1);
    } finally {
      await db.exec(`update public.plan_caps set history_cap = ${FREE_CHECKS} where plan = 'free'`);
    }
  });
});
