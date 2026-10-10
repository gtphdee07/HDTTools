import type { SupabaseClient } from '@supabase/supabase-js';
import { GarageFullError } from './garage';
import type { GarageBackend } from './garage';
import type { RecentRig } from './types';

// The account's Garage over the `garage_rigs` table and `add_rig` function from
// supabase/migrations/20261010000000_garage_rigs.sql. Row-level security scopes every call to the
// signed-in account; the cap and idempotency live in add_rig, not here.

interface GarageRow {
  id: string;
  nickname: string;
  truck: RecentRig['truck'];
  trailer: RecentRig['trailer'];
  last_used_at: string;
}

const toRig = (row: GarageRow): RecentRig => ({
  id: row.id,
  nickname: row.nickname,
  truck: row.truck,
  trailer: row.trailer,
  lastUsedAt: row.last_used_at,
});

export function createSupabaseGarageBackend(client: SupabaseClient): GarageBackend {
  return {
    async list() {
      const { data, error } = await client
        .from('garage_rigs')
        .select('id, nickname, truck, trailer, last_used_at')
        .order('last_used_at', { ascending: false });
      if (error) throw new Error(error.message);
      return (data as GarageRow[]).map(toRig);
    },

    async addRig(idempotencyKey, rig) {
      const { error } = await client.rpc('add_rig', {
        p_idempotency_key: idempotencyKey,
        p_nickname: rig.nickname,
        p_truck: rig.truck,
        p_trailer: rig.trailer,
      });
      if (!error) return;
      if (error.message === 'garage_full') {
        const cap = Number.parseInt(error.details ?? '', 10);
        throw new GarageFullError(Number.isNaN(cap) ? null : cap);
      }
      throw new Error(error.message);
    },

    async updateRig(rig) {
      const { data, error } = await client
        .from('garage_rigs')
        .update({ truck: rig.truck, trailer: rig.trailer, last_used_at: rig.lastUsedAt })
        .eq('id', rig.id)
        .select('id');
      if (error) throw new Error(error.message);
      if (data.length === 0) throw new Error('rig_not_found');
    },
  };
}
