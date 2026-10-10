import { describe, expect, it, vi } from 'vitest';
import type { SupabaseClient } from '@supabase/supabase-js';
import { GarageFullError } from './garage';
import { createSupabaseGarageBackend } from './supabaseGarage';

// The adapter's only logic is translating between the app's Garage shapes and the table/RPC
// contract. Supabase is faked at the client boundary; the contract itself is checked live by
// [supabase-tables] in the External suite.

function fakeClient(rpcResult: { error: { message: string; details?: string } | null }) {
  const rpc = vi.fn(async () => rpcResult);
  return { client: { rpc } as unknown as SupabaseClient, rpc };
}

describe('createSupabaseGarageBackend', () => {
  it('sends the idempotency key and the Rig to add_rig', async () => {
    const { client, rpc } = fakeClient({ error: null });

    await createSupabaseGarageBackend(client).addRig('key-1', {
      nickname: 'Big Blue',
      truck: { manufacturer: 'Ford' },
      trailer: {},
    });

    expect(rpc).toHaveBeenCalledWith('add_rig', {
      p_idempotency_key: 'key-1',
      p_nickname: 'Big Blue',
      p_truck: { manufacturer: 'Ford' },
      p_trailer: {},
    });
  });

  it('turns the server\u2019s garage_full error into a GarageFullError carrying the cap', async () => {
    const { client } = fakeClient({ error: { message: 'garage_full', details: '5' } });

    const attempt = createSupabaseGarageBackend(client).addRig('key-1', { nickname: 'Big Blue', truck: {}, trailer: {} });

    await expect(attempt).rejects.toBeInstanceOf(GarageFullError);
    await expect(attempt).rejects.toMatchObject({ cap: 5 });
  });

  it('reports an unreadable cap as unknown rather than guessing', async () => {
    const { client } = fakeClient({ error: { message: 'garage_full' } });

    await expect(
      createSupabaseGarageBackend(client).addRig('key-1', { nickname: 'Big Blue', truck: {}, trailer: {} }),
    ).rejects.toMatchObject({ cap: null });
  });

  it('lets any other server error through as a plain error', async () => {
    const { client } = fakeClient({ error: { message: 'connection reset' } });

    const attempt = createSupabaseGarageBackend(client).addRig('key-1', { nickname: 'Big Blue', truck: {}, trailer: {} });

    await expect(attempt).rejects.toThrow('connection reset');
    await expect(attempt).rejects.not.toBeInstanceOf(GarageFullError);
  });
});
