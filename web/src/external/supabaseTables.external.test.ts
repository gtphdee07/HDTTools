import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { createClient } from '@supabase/supabase-js';
import type { SupabaseClient } from '@supabase/supabase-js';
import { REQUIRED, SECOND_ACCOUNT, readConfig } from './config';

// External suite (ADR-0008): real calls to the live Supabase project, run only via
// `npm run test:external`. The "[supabase-tables]" name tag is what the wrapper filters on.
// Covers the Garage table surface (#28): row-level security, the server-enforced Free cap
// (including concurrent adds, which only a real database can show) and idempotent retry.
// It needs supabase/migrations/20261010000000_garage_rigs.sql applied to the project, and it
// empties the two test accounts' Garages before and after, so it must only ever use throwaway
// test accounts. It never creates a user and never triggers an email.

const FREE_CAP = 5;

const isMissingTable = (error: { message: string } | null) => /garage_rigs|schema cache/i.test(error?.message ?? '');

describe('[supabase-tables] Supabase Garage table live contract', () => {
  let url: string;
  let anonKey: string;
  let alice: SupabaseClient;
  let bob: SupabaseClient;
  let aliceAgain: SupabaseClient;
  let signedOut: SupabaseClient;

  const freshClient = () =>
    createClient(url, anonKey, { auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false } });

  async function signedIn(email: string, password: string) {
    const client = freshClient();
    const { error } = await client.auth.signInWithPassword({ email, password });
    if (error) throw new Error('External test account could not sign in');
    return client;
  }

  const emptyGarage = async (client: SupabaseClient) => {
    const { error } = await client.from('garage_rigs').delete().not('id', 'is', null);
    expect(error, 'migration 20261010000000_garage_rigs.sql must be applied to the project').toBeNull();
  };

  const countRigs = async (client: SupabaseClient) => {
    const { data, error } = await client.from('garage_rigs').select('id');
    expect(error).toBeNull();
    return data!.length;
  };

  const add = (client: SupabaseClient, key: string, nickname: string) =>
    client.rpc('add_rig', { p_idempotency_key: key, p_nickname: nickname, p_truck: {}, p_trailer: {} });

  const runId = Date.now().toString(36);
  const key = (name: string) => `external-${runId}-${name}`;

  beforeAll(async () => {
    const cfg = readConfig(import.meta.env as Record<string, string | undefined>, [...REQUIRED, ...SECOND_ACCOUNT]);
    url = cfg.VITE_SUPABASE_URL;
    anonKey = cfg.VITE_SUPABASE_PUBLISHABLE_KEY;
    alice = await signedIn(cfg.WEB_EXTERNAL_TEST_EMAIL, cfg.WEB_EXTERNAL_TEST_PASSWORD);
    // a second session of the same account, standing in for a second device
    aliceAgain = await signedIn(cfg.WEB_EXTERNAL_TEST_EMAIL, cfg.WEB_EXTERNAL_TEST_PASSWORD);
    bob = await signedIn(cfg.WEB_EXTERNAL_TEST_NOCREDITS_EMAIL, cfg.WEB_EXTERNAL_TEST_NOCREDITS_PASSWORD);
    signedOut = freshClient();
    await emptyGarage(alice);
    await emptyGarage(bob);
  });

  afterAll(async () => {
    if (alice) await alice.from('garage_rigs').delete().not('id', 'is', null);
    if (bob) await bob.from('garage_rigs').delete().not('id', 'is', null);
  });

  it('has the Garage table and add_rig function the app calls', async () => {
    const table = await alice.from('garage_rigs').select('id, nickname, truck, trailer, last_used_at').limit(1);
    expect(isMissingTable(table.error), 'garage_rigs table is missing: apply the migration').toBe(false);
    expect(table.error).toBeNull();

    const added = await add(alice, key('shape'), 'Shape Check');
    expect(added.error).toBeNull();
    expect(added.data).toMatchObject({ nickname: 'Shape Check', truck: {}, trailer: {} });
    expect(added.data.id).toMatch(/^[0-9a-f-]{36}$/);
    expect(new Date(added.data.last_used_at).getTime()).not.toBeNaN();
    await emptyGarage(alice);
  });

  it('shows an account only its own rigs, and refuses another account any change to them', async () => {
    await emptyGarage(alice);
    await emptyGarage(bob);
    const mine = await add(alice, key('own'), 'Alice Rig');
    expect(mine.error).toBeNull();
    expect((await add(bob, key('own'), 'Bob Rig')).error).toBeNull();

    const bobSees = await bob.from('garage_rigs').select('nickname');
    expect(bobSees.data!.map((r) => r.nickname)).toEqual(['Bob Rig']);

    const hijack = await bob.from('garage_rigs').update({ nickname: 'Hijacked' }).eq('id', mine.data.id).select('id');
    expect(hijack.data ?? []).toHaveLength(0);
    const removal = await bob.from('garage_rigs').delete().eq('id', mine.data.id).select('id');
    expect(removal.data ?? []).toHaveLength(0);

    const aliceSees = await alice.from('garage_rigs').select('nickname');
    expect(aliceSees.data!.map((r) => r.nickname)).toEqual(['Alice Rig']);
    await emptyGarage(alice);
    await emptyGarage(bob);
  });

  it('gives a signed-out caller no access to the table or to add_rig', async () => {
    const read = await signedOut.from('garage_rigs').select('id');
    expect(read.error).not.toBeNull();
    expect((await add(signedOut, key('anon'), 'Anon Rig')).error).not.toBeNull();
  });

  it('refuses a direct insert, so the capacity check cannot be skipped', async () => {
    const direct = await alice.from('garage_rigs').insert({ nickname: 'Direct', idempotency_key: key('direct') });
    expect(direct.error).not.toBeNull();
    expect(await countRigs(alice)).toBe(0);
  });

  it('refuses to hand a rig to another account by changing its owner', async () => {
    await emptyGarage(alice);
    const mine = await add(alice, key('owner'), 'Alice Rig');
    const reassigned = await alice
      .from('garage_rigs')
      .update({ user_id: '00000000-0000-4000-8000-000000000000' })
      .eq('id', mine.data.id);
    expect(reassigned.error).not.toBeNull();
    await emptyGarage(alice);
  });

  it('stops at the Free cap with a garage_full error that carries the cap', async () => {
    await emptyGarage(alice);
    for (let i = 1; i <= FREE_CAP; i++) {
      expect((await add(alice, key(`cap-${i}`), `Rig ${i}`)).error).toBeNull();
    }

    const over = await add(alice, key('cap-over'), 'One Too Many');

    expect(over.error?.message).toBe('garage_full');
    expect(over.error?.details).toBe(String(FREE_CAP));
    expect(await countRigs(alice)).toBe(FREE_CAP);
    await emptyGarage(alice);
  });

  it('never exceeds the cap when many adds arrive at the same moment', async () => {
    await emptyGarage(alice);
    for (let i = 1; i <= FREE_CAP - 1; i++) {
      expect((await add(alice, key(`race-${i}`), `Rig ${i}`)).error).toBeNull();
    }

    // Two sessions of one account (two devices) racing, with room for exactly one more.
    const attempts = await Promise.all(
      Array.from({ length: 8 }, (_, i) => add(i % 2 === 0 ? alice : aliceAgain, key(`race-extra-${i}`), `Racer ${i}`)),
    );

    const accepted = attempts.filter((a) => a.error === null);
    const refused = attempts.filter((a) => a.error?.message === 'garage_full');
    expect(accepted).toHaveLength(1);
    expect(refused).toHaveLength(attempts.length - 1);
    expect(await countRigs(alice)).toBe(FREE_CAP);
    await emptyGarage(alice);
  });

  it('creates one rig when the same add is retried, even after the garage has filled', async () => {
    await emptyGarage(alice);
    for (let i = 1; i <= FREE_CAP - 1; i++) {
      expect((await add(alice, key(`retry-${i}`), `Rig ${i}`)).error).toBeNull();
    }
    const first = await add(alice, key('retry-last'), 'Last Slot');
    expect(first.error).toBeNull();

    const retried = await add(alice, key('retry-last'), 'Last Slot');

    expect(retried.error).toBeNull();
    expect(retried.data.id).toBe(first.data.id);
    expect(await countRigs(alice)).toBe(FREE_CAP);
    await emptyGarage(alice);
  });

  it('lets a rig in a full garage be updated, and its last-used time changed, without using capacity', async () => {
    await emptyGarage(alice);
    for (let i = 1; i <= FREE_CAP; i++) {
      expect((await add(alice, key(`touch-${i}`), `Rig ${i}`)).error).toBeNull();
    }
    const before = await alice.from('garage_rigs').select('id, last_used_at').eq('nickname', 'Rig 1').single();

    const touched = await alice
      .from('garage_rigs')
      .update({ last_used_at: new Date(Date.now() + 60_000).toISOString(), truck: { manufacturer: 'Ram' } })
      .eq('id', before.data!.id)
      .select('last_used_at, truck');
    expect(touched.error).toBeNull();
    expect(touched.data).toHaveLength(1);
    expect(new Date(touched.data![0].last_used_at).getTime()).toBeGreaterThan(new Date(before.data!.last_used_at).getTime());
    expect(touched.data![0].truck).toEqual({ manufacturer: 'Ram' });

    const refreshed = await add(alice, key('touch-again'), 'rig 2');
    expect(refreshed.error).toBeNull();
    expect(await countRigs(alice)).toBe(FREE_CAP);
    await emptyGarage(alice);
  });

  it('frees a slot when a rig is deleted', async () => {
    await emptyGarage(alice);
    for (let i = 1; i <= FREE_CAP; i++) {
      expect((await add(alice, key(`free-${i}`), `Rig ${i}`)).error).toBeNull();
    }

    expect((await alice.from('garage_rigs').delete().eq('nickname', 'Rig 1')).error).toBeNull();

    expect((await add(alice, key('free-new'), 'Replacement')).error).toBeNull();
    expect(await countRigs(alice)).toBe(FREE_CAP);
    await emptyGarage(alice);
  });
});
