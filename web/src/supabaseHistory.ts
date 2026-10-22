import type { SupabaseClient } from '@supabase/supabase-js';
import { formatDate } from './breakdown';
import type { HistoryBackend } from './history';
import type { Verdict } from './types';

// The account's History over the `history_entries` table and `add_history_entry` function from
// supabase/migrations/20261022000000_history_entries.sql. Row-level security scopes every call to the
// signed-in account; the cap and idempotency live in add_history_entry, not here.

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

    async addEntry(idempotencyKey, entry) {
      const { error } = await client.rpc('add_history_entry', {
        p_idempotency_key: idempotencyKey,
        p_rig_nickname: entry.rigNickname.trim(),
        p_verdict: entry.verdict,
      });
      if (error) throw new Error(error.message);
    },
  };
}
