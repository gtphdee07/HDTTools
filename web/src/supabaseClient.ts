import { createClient } from '@supabase/supabase-js';
import type { SupabaseClient } from '@supabase/supabase-js';

let cached: { url: string; key: string; client: SupabaseClient } | null = null;

// The one Supabase client for the app: auth and the Garage table must share it, because the client
// attaches the signed-in session's token to every table call. Null when the project isn't configured.
export function getSupabaseClient(): SupabaseClient | null {
  const url: string | undefined = import.meta.env.VITE_SUPABASE_URL;
  const key: string | undefined = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) return null;
  if (!cached || cached.url !== url || cached.key !== key) cached = { url, key, client: createClient(url, key) };
  return cached.client;
}
