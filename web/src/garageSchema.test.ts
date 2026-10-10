// @vitest-environment node
import { readFileSync } from 'node:fs';
import { PGlite } from '@electric-sql/pglite';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

// Service-boundary tests for the Garage table (#28): the committed Supabase migration is run on a real
// Postgres (PGlite) and driven the way PostgREST drives it - as the `authenticated` role with the
// caller's id in the JWT claim - so row-level security, grants, the capacity check and idempotent
// retry are exercised as written, not re-implemented. Supabase's own pieces (the `auth` schema, the
// roles, `auth.uid()`) are stubbed below because they are not part of the migration.
//
// What this cannot show: two *simultaneous* transactions (PGlite has one connection). The lock that
// makes concurrent adds safe is exercised by the live External test, `[supabase-tables]`.

const MIGRATION = readFileSync(
  new URL('../../supabase/migrations/20261010000000_garage_rigs.sql', import.meta.url),
  'utf8',
);

const ALICE = '00000000-0000-4000-8000-00000000000a';
const BOB = '00000000-0000-4000-8000-00000000000b';
const FREE_CAP = 5;

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

async function addRig(userId: string | null, key: string, nickname: string, truck: object = {}, trailer: object = {}) {
  return asUser(userId, () =>
    db.query<{ id: string; nickname: string }>('select * from public.add_rig($1, $2, $3, $4)', [
      key,
      nickname,
      JSON.stringify(truck),
      JSON.stringify(trailer),
    ]),
  );
}

const listRigs = (userId: string) =>
  asUser(userId, () => db.query<{ nickname: string; last_used_at: string }>('select nickname, last_used_at from public.garage_rigs order by nickname'));

async function clearGarage() {
  await db.exec('delete from public.garage_rigs');
}

async function fillGarage(userId: string, count: number) {
  for (let i = 1; i <= count; i++) await addRig(userId, `fill-${userId}-${i}`, `Rig ${i}`);
}

describe('garage_rigs row-level security', () => {
  it('shows an account only its own rigs', async () => {
    await clearGarage();
    await addRig(ALICE, 'a-1', 'Alice Rig');
    await addRig(BOB, 'b-1', 'Bob Rig');

    expect((await listRigs(ALICE)).rows.map((r) => r.nickname)).toEqual(['Alice Rig']);
    expect((await listRigs(BOB)).rows.map((r) => r.nickname)).toEqual(['Bob Rig']);
  });

  it('shows a signed-out caller nothing, and refuses it writes', async () => {
    await clearGarage();
    await addRig(ALICE, 'a-1', 'Alice Rig');

    await expect(asUser(null, () => db.query('select * from public.garage_rigs'))).rejects.toThrow(/permission denied/);
    await expect(addRig(null, 'x-1', 'Sneaky')).rejects.toThrow(/permission denied/);
  });

  it('does not let an account update another account’s rig', async () => {
    await clearGarage();
    await addRig(ALICE, 'a-1', 'Alice Rig');

    const changed = await asUser(BOB, () => db.query(`update public.garage_rigs set nickname = 'Hijacked' returning id`));
    expect(changed.rows).toHaveLength(0);
    expect((await listRigs(ALICE)).rows.map((r) => r.nickname)).toEqual(['Alice Rig']);
  });

  it('does not let an account hand its rig to another account', async () => {
    await clearGarage();
    await addRig(ALICE, 'a-1', 'Alice Rig');

    await expect(asUser(ALICE, () => db.query(`update public.garage_rigs set user_id = '${BOB}'`))).rejects.toThrow();
    expect((await listRigs(BOB)).rows).toHaveLength(0);
  });

  it('refuses a direct insert, so the capacity check cannot be skipped', async () => {
    await clearGarage();

    await expect(
      asUser(ALICE, () => db.query(`insert into public.garage_rigs (nickname) values ('Direct')`)),
    ).rejects.toThrow(/permission denied/);
  });

  it('lets an account delete its own rig, which frees the slot, but not another account’s', async () => {
    await clearGarage();
    await fillGarage(ALICE, FREE_CAP);

    const bobDeleted = await asUser(BOB, () => db.query('delete from public.garage_rigs returning id'));
    expect(bobDeleted.rows).toHaveLength(0);
    expect((await listRigs(ALICE)).rows).toHaveLength(FREE_CAP);

    await asUser(ALICE, () => db.query("delete from public.garage_rigs where nickname = 'Rig 1'"));
    await addRig(ALICE, 'after-delete', 'Replacement');
    expect((await listRigs(ALICE)).rows).toHaveLength(FREE_CAP);
  });
});

describe('add_rig capacity', () => {
  it('accepts rigs up to the Free cap and refuses the next one with the cap in the error', async () => {
    await clearGarage();
    await fillGarage(ALICE, FREE_CAP);

    const refused = await addRig(ALICE, 'one-too-many', 'Rig 6').catch((e: Error & { detail?: string }) => e);
    expect(refused).toBeInstanceOf(Error);
    expect((refused as Error).message).toBe('garage_full');
    expect((refused as Error & { detail?: string }).detail).toBe(String(FREE_CAP));
    expect((await listRigs(ALICE)).rows).toHaveLength(FREE_CAP);
  });

  it('counts each account separately', async () => {
    await clearGarage();
    await fillGarage(ALICE, FREE_CAP);

    await addRig(BOB, 'b-1', 'Bob Rig');
    expect((await listRigs(BOB)).rows).toHaveLength(1);
  });

  it('refuses a caller with no account', async () => {
    await clearGarage();

    await expect(asUser(null, () => db.query(`select * from public.add_rig('k', 'Rig', '{}', '{}')`))).rejects.toThrow(
      /permission denied/,
    );
  });

  it('refuses a blank nickname and an oversized tag payload', async () => {
    await clearGarage();

    await expect(addRig(ALICE, 'k-1', '   ')).rejects.toThrow();
    await expect(addRig(ALICE, 'k-2', 'Big', { notes: 'x'.repeat(20_000) })).rejects.toThrow();
    expect((await listRigs(ALICE)).rows).toHaveLength(0);
  });
});

describe('add_rig idempotency', () => {
  it('creates one rig when the same key is sent twice, and returns the same rig both times', async () => {
    await clearGarage();

    const first = await addRig(ALICE, 'retry-1', 'Big Blue', { manufacturer: 'Ford' });
    const second = await addRig(ALICE, 'retry-1', 'Big Blue', { manufacturer: 'Ford' });

    expect(second.rows[0].id).toBe(first.rows[0].id);
    expect((await listRigs(ALICE)).rows).toHaveLength(1);
  });

  it('does not charge a retry against capacity', async () => {
    await clearGarage();
    await fillGarage(ALICE, FREE_CAP - 1);
    await addRig(ALICE, 'retry-1', 'Last Slot');
    await addRig(ALICE, 'retry-1', 'Last Slot');

    expect((await listRigs(ALICE)).rows).toHaveLength(FREE_CAP);
  });

  it('answers a retry of a successful add with the rig, not a full-garage error, even once the garage is full', async () => {
    await clearGarage();
    await fillGarage(ALICE, FREE_CAP - 1);
    const first = await addRig(ALICE, 'retry-1', 'Last Slot');

    const retried = await addRig(ALICE, 'retry-1', 'Last Slot');
    expect(retried.rows[0].id).toBe(first.rows[0].id);
  });

  it('still recognises a retry after the rig was renamed on another device', async () => {
    await clearGarage();
    const first = await addRig(ALICE, 'retry-1', 'Big Blue');
    await asUser(ALICE, () => db.query(`update public.garage_rigs set nickname = 'Renamed' where id = '${first.rows[0].id}'`));

    const retried = await addRig(ALICE, 'retry-1', 'Big Blue');

    expect(retried.rows[0].id).toBe(first.rows[0].id);
    expect((await listRigs(ALICE)).rows.map((r) => r.nickname)).toEqual(['Renamed']);
  });

  it('treats the same key from two accounts as two different adds', async () => {
    await clearGarage();

    await addRig(ALICE, 'shared-key', 'Alice Rig');
    await addRig(BOB, 'shared-key', 'Bob Rig');

    expect((await listRigs(ALICE)).rows).toHaveLength(1);
    expect((await listRigs(BOB)).rows).toHaveLength(1);
  });
});

describe('capacity-free changes to an existing rig', () => {
  it('lets the last-used time change when the garage is full', async () => {
    await clearGarage();
    await fillGarage(ALICE, FREE_CAP);

    const updated = await asUser(ALICE, () =>
      db.query(`update public.garage_rigs set last_used_at = '2030-01-01T00:00:00Z' where nickname = 'Rig 1' returning id`),
    );
    expect(updated.rows).toHaveLength(1);
    expect((await listRigs(ALICE)).rows).toHaveLength(FREE_CAP);
  });

  it('lets the tag data of an existing rig be rewritten when the garage is full', async () => {
    await clearGarage();
    await fillGarage(ALICE, FREE_CAP);

    const updated = await asUser(ALICE, () =>
      db.query(`update public.garage_rigs set truck = '{"manufacturer":"Ram"}' where nickname = 'Rig 2' returning truck`),
    );
    expect(updated.rows).toHaveLength(1);
  });

  it('treats add_rig for a nickname already in the garage as a refresh, not a new rig, even when full', async () => {
    await clearGarage();
    await fillGarage(ALICE, FREE_CAP);

    const refreshed = await addRig(ALICE, 'new-key', 'rig 3', { manufacturer: 'Ram' });

    expect(refreshed.rows).toHaveLength(1);
    expect((await listRigs(ALICE)).rows).toHaveLength(FREE_CAP);
    const stored = await asUser(ALICE, () => db.query<{ truck: { manufacturer: string } }>(`select truck from public.garage_rigs where nickname = 'Rig 3'`));
    expect(stored.rows[0].truck.manufacturer).toBe('Ram');
  });

  it('refuses a rename onto a nickname the account already uses', async () => {
    await clearGarage();
    await addRig(ALICE, 'a-1', 'Rig A');
    await addRig(ALICE, 'a-2', 'Rig B');

    await expect(
      asUser(ALICE, () => db.query(`update public.garage_rigs set nickname = 'rig a' where nickname = 'Rig B'`)),
    ).rejects.toThrow();
  });
});
