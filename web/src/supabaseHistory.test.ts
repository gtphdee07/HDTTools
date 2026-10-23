import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { SupabaseClient } from '@supabase/supabase-js';
import { createSupabaseHistoryBackend } from './supabaseHistory';

// The adapter's only logic is translating between the app's History shapes and the table/RPC
// contract. Supabase is faked at the client boundary; the contract itself is checked live by
// [supabase-tables] in the External suite.

function fakeRpcClient(error: { message: string } | null = null) {
  const rpc = vi.fn(async (_name: string, _args: Record<string, unknown>) => ({ error }));
  return { client: { rpc } as unknown as SupabaseClient, rpc };
}

function fakeListClient(result: { data: unknown; error: { message: string } | null }) {
  const order = vi.fn(async () => result);
  const select = vi.fn(() => ({ order }));
  const from = vi.fn(() => ({ select }));
  return { client: { from } as unknown as SupabaseClient, from, select, order };
}

describe('createSupabaseHistoryBackend', () => {
  // Entry dates are the viewer's local day, so every test pins the zone instead of using the machine's.
  const savedZone = process.env.TZ;
  beforeEach(() => {
    process.env.TZ = 'UTC';
  });
  afterEach(() => {
    if (savedZone === undefined) delete process.env.TZ;
    else process.env.TZ = savedZone;
  });

  it('sends the idempotency key, the Rig and the verdict to add_history_entry', async () => {
    const { client, rpc } = fakeRpcClient();

    await createSupabaseHistoryBackend(client).addEntry('key-1', { rigNickname: 'Big Blue', verdict: 'fail' }, 'free');

    expect(rpc).toHaveBeenCalledWith('add_history_entry', {
      p_idempotency_key: 'key-1',
      p_rig_nickname: 'Big Blue',
      p_verdict: 'fail',
      p_pro: false,
    });
  });

  it('tells add_history_entry which cap applies: Pro, Free, or unknown when the plan could not be read', async () => {
    const { client, rpc } = fakeRpcClient();
    const entry = { rigNickname: 'Big Blue', verdict: 'pass' as const };

    await createSupabaseHistoryBackend(client).addEntry('key-1', entry, 'pro');
    await createSupabaseHistoryBackend(client).addEntry('key-2', entry, 'free');
    await createSupabaseHistoryBackend(client).addEntry('key-3', entry, null);

    expect(rpc.mock.calls.map(([, args]) => args.p_pro)).toEqual([true, false, null]);
  });

  it('reads how many checks each plan keeps from plan_caps', async () => {
    const select = vi.fn(async () => ({
      data: [
        { plan: 'pro', history_cap: 50 },
        { plan: 'free', history_cap: 10 },
      ],
      error: null,
    }));
    const from = vi.fn(() => ({ select }));

    const caps = await createSupabaseHistoryBackend({ from } as unknown as SupabaseClient).caps();

    expect(from).toHaveBeenCalledWith('plan_caps');
    expect(caps).toEqual({ free: 10, pro: 50 });
  });

  it('rejects caps that are incomplete or refused, so the screen says nothing rather than guessing', async () => {
    const half = vi.fn(async () => ({ data: [{ plan: 'free', history_cap: 10 }], error: null }));
    const refused = vi.fn(async () => ({ data: null, error: { message: 'connection reset' } }));

    await expect(
      createSupabaseHistoryBackend({ from: () => ({ select: half }) } as unknown as SupabaseClient).caps(),
    ).rejects.toThrow('plan_caps_missing');
    await expect(
      createSupabaseHistoryBackend({ from: () => ({ select: refused }) } as unknown as SupabaseClient).caps(),
    ).rejects.toThrow('connection reset');
  });

  it('sends the nickname without its surrounding spaces', async () => {
    const { client, rpc } = fakeRpcClient();

    await createSupabaseHistoryBackend(client).addEntry('key-1', { rigNickname: ' truck a ', verdict: 'pass' }, 'free');

    expect(rpc).toHaveBeenCalledWith('add_history_entry', expect.objectContaining({ p_rig_nickname: 'truck a' }));
  });

  it('lets a server error through, so the caller can retry', async () => {
    const { client } = fakeRpcClient({ message: 'connection reset' });

    await expect(createSupabaseHistoryBackend(client).addEntry('key-1', { rigNickname: 'Big Blue', verdict: 'pass' }, 'free')).rejects.toThrow(
      'connection reset',
    );
  });

  it('lists the newest checks first, each with the date the app shows for a fresh check', async () => {
    const { client, from, order } = fakeListClient({
      data: [
        { id: 'h2', rig_nickname: ' Truck A ', verdict: 'fail', checked_at: '2026-10-22T03:15:00Z' },
        { id: 'h1', rig_nickname: 'Truck B', verdict: 'pass', checked_at: '2026-10-05T23:59:59Z' },
      ],
      error: null,
    });

    const entries = await createSupabaseHistoryBackend(client).list();

    expect(from).toHaveBeenCalledWith('history_entries');
    expect(order).toHaveBeenCalledWith('seq', { ascending: false });
    expect(entries).toEqual([
      { id: 'h2', date: 'Oct 22, 2026', rigNickname: 'Truck A', verdict: 'fail' },
      { id: 'h1', date: 'Oct 05, 2026', rigNickname: 'Truck B', verdict: 'pass' },
    ]);
  });

  it("shows each entry's date as the viewer's local day, not the UTC day the server stored", async () => {
    const rows = {
      data: [
        { id: 'h2', rig_nickname: 'Truck A', verdict: 'fail', checked_at: '2026-10-22T03:15:00Z' },
        { id: 'h1', rig_nickname: 'Truck B', verdict: 'pass', checked_at: '2026-10-05T23:30:00Z' },
      ],
      error: null,
    };
    const datesShownIn = async (zone: string) => {
      process.env.TZ = zone;
      return (await createSupabaseHistoryBackend(fakeListClient(rows).client).list()).map((e) => e.date);
    };

    // Chicago is UTC-5 in October: 03:15Z is still the evening before. Auckland is UTC+13: 23:30Z is already the next day.
    expect(await datesShownIn('America/Chicago')).toEqual(['Oct 21, 2026', 'Oct 05, 2026']);
    expect(await datesShownIn('Pacific/Auckland')).toEqual(['Oct 22, 2026', 'Oct 06, 2026']);
  });

  it('rejects a list the server refused, so the caller keeps what it shows', async () => {
    const { client } = fakeListClient({ data: null, error: { message: 'connection reset' } });

    await expect(createSupabaseHistoryBackend(client).list()).rejects.toThrow('connection reset');
  });
});
