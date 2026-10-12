import { createClient } from '@supabase/supabase-js';
import type { SupabaseClient } from '@supabase/supabase-js';

let cached: { url: string; key: string; client: SupabaseClient } | null = null;

// The one Supabase client for the app: auth and the Garage table must share it, because the client
// attaches the signed-in session's token to every table call. Null when the project isn't configured.
// PKCE, not the default implicit flow: the implicit flow signs in whatever session sits in the URL
// fragment, so a crafted link could sign a visitor into an account the link's author controls. The
// cost is that an email link only signs in the browser that asked for it (see Account's link notice).
export function getSupabaseClient(): SupabaseClient | null {
  const url: string | undefined = import.meta.env.VITE_SUPABASE_URL;
  const key: string | undefined = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) return null;
  if (!cached || cached.url !== url || cached.key !== key) {
    cached = { url, key, client: createClient(url, key, { auth: { flowType: 'pkce' } }) };
  }
  return cached.client;
}
