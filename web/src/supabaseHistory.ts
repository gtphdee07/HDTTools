import type { SupabaseClient } from '@supabase/supabase-js';
import { formatDate } from './breakdown';
import type { HistoryBackend } from './history';
import type { Plan } from './plan';
import type { Verdict } from './types';

// The account's History over the `history_entries` table and `add_history_entry` function from
// supabase/migrations/20261022000000_history_entries.sql. Row-level security scopes every call to the
// signed-in account; the cap and idempotency live in add_history_entry, not here. The plan only tells
// add_history_entry which cap to use (supabase/migrations/20261023000000_plan_caps.sql).

interface HistoryRow {
  id: string;
  rig_nickname: string;
  verdict: Verdict;
  checked_at: string;
}

export function createSupabaseHistoryBackend(client: SupabaseClient): HistoryBackend {
  return {
    async list() {
      const { data, error } = await client
        .from('history_entries')
        .select('id, rig_nickname, verdict, checked_at')
        // Insertion order, not the timestamp: the timestamp is only what the entry's date shows.
        .order('seq', { ascending: false });
      if (error) throw new Error(error.message);
      return (data as HistoryRow[]).map((row) => ({
        id: row.id,
        date: formatDate(new Date(row.checked_at)),
        rigNickname: row.rig_nickname.trim(),
        verdict: row.verdict,
      }));
    },

    async caps() {
      const { data, error } = await client.from('plan_caps').select('plan, history_cap');
      if (error) throw new Error(error.message);
      const rows = data as Array<{ plan: Plan; history_cap: number }>;
      const of = (plan: Plan) => rows.find((r) => r.plan === plan)?.history_cap;
      const free = of('free');
      const pro = of('pro');
      if (free === undefined || pro === undefined) throw new Error('plan_caps_missing');
      return { free, pro };
    },

    async addEntry(idempotencyKey, entry, plan) {
      const { error } = await client.rpc('add_history_entry', {
        p_idempotency_key: idempotencyKey,
        p_rig_nickname: entry.rigNickname.trim(),
        p_verdict: entry.verdict,
        p_pro: plan === null ? null : plan === 'pro',
      });
      if (error) throw new Error(error.message);
    },
  };
}
