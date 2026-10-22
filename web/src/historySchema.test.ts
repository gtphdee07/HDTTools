// @vitest-environment node
import { readFileSync } from 'node:fs';
import { PGlite } from '@electric-sql/pglite';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

// Service-boundary tests for the History table (#29): the committed Supabase migration is run on a real
// Postgres (PGlite) and driven the way PostgREST drives it - as the `authenticated` role with the
// caller's id in the JWT claim - so row-level security, grants, the cap with oldest-entry pruning and
// idempotent retry are exercised as written, not re-implemented. Supabase's own pieces (the `auth`
// schema, the roles, `auth.uid()`) are stubbed below because they are not part of the migration.
//
// What this cannot show: two *simultaneous* transactions (PGlite has one connection). The lock that
// keeps concurrent adds from pruning on a stale count is exercised by the live External test,
// `[supabase-tables]`.

const MIGRATION = readFileSync(
  new URL('../../supabase/migrations/20261022000000_history_entries.sql', import.meta.url),
  'utf8',
);

const ALICE = '00000000-0000-4000-8000-00000000000a';
const BOB = '00000000-0000-4000-8000-00000000000b';
const FREE_CAP = 10;

let db: PGlite;

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
    insert into auth.users values ('${ALICE}'), ('${BOB}');
  `);
  await db.exec(MIGRATION);
});

afterAll(async () => {
  await db.close();
});

// Runs `fn` as the given account (null = signed out), the way a Supabase request arrives.
async function asUser<T>(userId: string | null, fn: () => Promise<T>): Promise<T> {
  await db.exec(
    userId
      ? `set role authenticated; select set_config('request.jwt.claim.sub', '${userId}', false);`
      : `set role anon; select set_config('request.jwt.claim.sub', '', false);`,
  );
  try {
    return await fn();
  } finally {
    await db.exec(`reset role; select set_config('request.jwt.claim.sub', '', false);`);
  }
}

async function addEntry(userId: string | null, key: string, rigNickname: string, verdict = 'pass') {
  return asUser(userId, () =>
    db.query<{ id: string; rig_nickname: string; verdict: string }>('select * from public.add_history_entry($1, $2, $3)', [
      key,
      rigNickname,
      verdict,
    ]),
  );
}

// Newest first, the order the app reads them in.
const listEntries = (userId: string) =>
  asUser(userId, () =>
    db.query<{ rig_nickname: string; verdict: string }>(
      'select rig_nickname, verdict from public.history_entries order by seq desc',
    ),
  );
const nicknames = async (userId: string) => (await listEntries(userId)).rows.map((r) => r.rig_nickname);

async function clearHistory() {
  await db.exec('delete from public.history_entries');
}

// Adds `count` checks named "Check 1" .. "Check <count>", the last one newest.
async function addChecks(userId: string, count: number) {
  for (let i = 1; i <= count; i++) await addEntry(userId, `fill-${userId}-${i}`, `Check ${i}`);
}

describe('history_entries row-level security', () => {
  it('shows an account only its own checks', async () => {
    await clearHistory();
    await addEntry(ALICE, 'a-1', 'Alice Rig');
    await addEntry(BOB, 'b-1', 'Bob Rig');

    expect(await nicknames(ALICE)).toEqual(['Alice Rig']);
    expect(await nicknames(BOB)).toEqual(['Bob Rig']);
  });

  it('shows a signed-out caller nothing, and refuses it writes', async () => {
    await clearHistory();
    await addEntry(ALICE, 'a-1', 'Alice Rig');

    await expect(asUser(null, () => db.query('select * from public.history_entries'))).rejects.toThrow(/permission denied/);
    await expect(addEntry(null, 'x-1', 'Sneaky')).rejects.toThrow(/permission denied/);
  });

  it('refuses a direct insert, so the cap cannot be skipped', async () => {
    await clearHistory();

    await expect(
      asUser(ALICE, () =>
        db.query(`insert into public.history_entries (rig_nickname, verdict, idempotency_key) values ('Direct', 'pass', 'k')`),
      ),
    ).rejects.toThrow(/permission denied/);
  });

  it('lets no account change or delete a check, its own or another’s', async () => {
    await clearHistory();
    await addEntry(ALICE, 'a-1', 'Alice Rig');

    await expect(asUser(ALICE, () => db.query(`update public.history_entries set verdict = 'fail'`))).rejects.toThrow(
      /permission denied/,
    );
    await expect(asUser(ALICE, () => db.query('delete from public.history_entries'))).rejects.toThrow(/permission denied/);
    await expect(asUser(BOB, () => db.query('delete from public.history_entries'))).rejects.toThrow(/permission denied/);
    expect(await nicknames(ALICE)).toEqual(['Alice Rig']);
  });
});

describe('add_history_entry cap', () => {
  it('keeps every check up to the Free cap', async () => {
    await clearHistory();

    await addChecks(ALICE, FREE_CAP);

    expect(await nicknames(ALICE)).toHaveLength(FREE_CAP);
    expect((await nicknames(ALICE))[0]).toBe(`Check ${FREE_CAP}`);
    expect((await nicknames(ALICE))[FREE_CAP - 1]).toBe('Check 1');
  });

  it('drops the oldest check when one more is added past the cap', async () => {
    await clearHistory();
    await addChecks(ALICE, FREE_CAP);

    await addEntry(ALICE, 'one-more', `Check ${FREE_CAP + 1}`);

    const kept = await nicknames(ALICE);
    expect(kept).toHaveLength(FREE_CAP);
    expect(kept[0]).toBe(`Check ${FREE_CAP + 1}`);
    expect(kept).not.toContain('Check 1');
    expect(kept[FREE_CAP - 1]).toBe('Check 2');
  });

  it('keeps dropping the oldest as more are added, never growing past the cap', async () => {
    await clearHistory();
    await addChecks(ALICE, FREE_CAP + 3);

    const kept = await nicknames(ALICE);
    expect(kept).toHaveLength(FREE_CAP);
    expect(kept[0]).toBe(`Check ${FREE_CAP + 3}`);
    expect(kept[FREE_CAP - 1]).toBe('Check 4');
  });

  it('goes by the order checks were added, not their timestamps, so a clock stepping back cannot prune the newest', async () => {
    await clearHistory();
    await addChecks(ALICE, FREE_CAP);
    // As if the server clock had since stepped back: every stored check now looks newer than the next one will.
    await db.exec(`update public.history_entries set checked_at = '2999-01-01T00:00:00Z'`);

    await addEntry(ALICE, 'after-clock-step', `Check ${FREE_CAP + 1}`);

    const kept = await nicknames(ALICE);
    expect(kept[0]).toBe(`Check ${FREE_CAP + 1}`);
    expect(kept).not.toContain('Check 1');
    expect(kept).toHaveLength(FREE_CAP);
  });

  it('counts and prunes each account separately', async () => {
    await clearHistory();
    await addChecks(BOB, 3);

    await addChecks(ALICE, FREE_CAP + 1);

    expect(await nicknames(BOB)).toEqual(['Check 3', 'Check 2', 'Check 1']);
    expect(await nicknames(ALICE)).toHaveLength(FREE_CAP);
  });

  it('keeps the same Rig’s checks as separate entries, each one a past result', async () => {
    await clearHistory();

    await addEntry(ALICE, 'k-1', 'Big Blue', 'fail');
    await addEntry(ALICE, 'k-2', 'Big Blue', 'pass');

    expect((await listEntries(ALICE)).rows).toEqual([
      { rig_nickname: 'Big Blue', verdict: 'pass' },
      { rig_nickname: 'Big Blue', verdict: 'fail' },
    ]);
  });
});

describe('add_history_entry idempotency', () => {
  it('creates one entry when the same add is retried', async () => {
    await clearHistory();

    const first = await addEntry(ALICE, 'retry-1', 'Big Blue');
    const retried = await addEntry(ALICE, 'retry-1', 'Big Blue');

    expect(retried.rows[0].id).toBe(first.rows[0].id);
    expect(await nicknames(ALICE)).toEqual(['Big Blue']);
  });

  it('does not prune again when an add is retried at the cap', async () => {
    await clearHistory();
    await addChecks(ALICE, FREE_CAP - 1);
    await addEntry(ALICE, 'last-slot', `Check ${FREE_CAP}`);

    await addEntry(ALICE, 'last-slot', `Check ${FREE_CAP}`);

    const kept = await nicknames(ALICE);
    expect(kept).toHaveLength(FREE_CAP);
    expect(kept[FREE_CAP - 1]).toBe('Check 1');
  });

  it('treats the same key from two accounts as two different adds', async () => {
    await clearHistory();

    await addEntry(ALICE, 'shared-key', 'Alice Rig');
    await addEntry(BOB, 'shared-key', 'Bob Rig');

    expect(await nicknames(ALICE)).toEqual(['Alice Rig']);
    expect(await nicknames(BOB)).toEqual(['Bob Rig']);
  });
});

describe('add_history_entry input', () => {
  it('stores the nickname without its surrounding spaces', async () => {
    await clearHistory();

    await addEntry(ALICE, 'k-1', '  Big Blue ');

    expect(await nicknames(ALICE)).toEqual(['Big Blue']);
  });

  it('refuses a verdict the app does not know, and a blank nickname', async () => {
    await clearHistory();

    await expect(addEntry(ALICE, 'k-1', 'Big Blue', 'maybe')).rejects.toThrow();
    await expect(addEntry(ALICE, 'k-2', '   ')).rejects.toThrow();
    expect(await nicknames(ALICE)).toEqual([]);
  });

  it('accepts each verdict the app produces', async () => {
    await clearHistory();

    for (const verdict of ['pass', 'fail', 'partial', 'insufficient']) await addEntry(ALICE, `k-${verdict}`, 'Big Blue', verdict);

    expect((await listEntries(ALICE)).rows.map((r) => r.verdict)).toEqual(['insufficient', 'partial', 'fail', 'pass']);
  });
});
