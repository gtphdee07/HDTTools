import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// The real supabase-js client (not mocked) against a stubbed network: proves what the PKCE flow
// does with a callback URL. A link whose author controls the session (#access_token=...) must not
// sign the visitor in, and a ?code= link opened without this browser's code verifier must leave no
// session and leave the code in the URL - Account's "different browser" message relies on that.

const jsonResponse = (body: unknown) =>
  new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });

const attacker = { id: 'attacker-id', aud: 'authenticated', email: 'attacker@example.com', app_metadata: {}, user_metadata: {}, created_at: '2026-01-01T00:00:00Z' };

let n = 0;
async function freshClient() {
  vi.resetModules();
  // A distinct project per test, so supabase-js's storage key never carries over between tests.
  vi.stubEnv('VITE_SUPABASE_URL', `https://project-${(n += 1)}.supabase.co`);
  vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_test');
  const { getSupabaseClient } = await import('./supabaseClient');
  return getSupabaseClient()!;
}

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(attacker)));
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  window.history.replaceState(null, '', '/');
});

describe('the Web Supabase client callback handling', () => {
  it('does not accept a session handed over in the URL fragment', async () => {
    const hash = '#access_token=attacker.jwt.token&refresh_token=r&expires_in=3600&token_type=bearer';
    window.history.replaceState(null, '', `/${hash}`);

    const client = await freshClient();
    const { data } = await client.auth.getSession();

    expect(data.session).toBeNull();
    expect(JSON.stringify(localStorage)).not.toContain('attacker.jwt.token');
  });

  it('leaves no session, and the code in the URL, for a ?code= link without this browser\'s code verifier', async () => {
    window.history.replaceState(null, '', '/?code=abc123');

    const client = await freshClient();
    const { data } = await client.auth.getSession();

    expect(data.session).toBeNull();
    expect(new URLSearchParams(window.location.search).get('code')).toBe('abc123');
  });
});
