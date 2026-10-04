import { afterEach, describe, expect, it, vi } from 'vitest';

// createSupabaseAuthClient wires auth.tsx's narrow AuthClient interface to
// the real Supabase SDK - the one line in this file that App.auth.test.tsx's
// fake client never exercises, since that suite injects its own fake
// directly. createClient is mocked so this never touches a real project;
// env vars are stubbed explicitly (not left to whatever web/.env.local
// happens to hold on this machine) so a missing or misnamed
// VITE_SUPABASE_* variable is provably caught offline.

const authSlice = { getSession: vi.fn() };
const mockCreateClient = vi.fn((_url: string, _key: string) => ({ auth: authSlice }));

vi.mock('@supabase/supabase-js', () => ({
  createClient: (url: string, key: string) => mockCreateClient(url, key),
}));

const { createSupabaseAuthClient } = await import('./auth');

afterEach(() => {
  vi.unstubAllEnvs();
  vi.clearAllMocks();
});

describe('createSupabaseAuthClient', () => {
  it('returns null and never calls createClient when neither env var is set', () => {
    vi.stubEnv('VITE_SUPABASE_URL', '');
    vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', '');
    expect(createSupabaseAuthClient()).toBeNull();
    expect(mockCreateClient).not.toHaveBeenCalled();
  });

  it('returns null when only the URL is set', () => {
    vi.stubEnv('VITE_SUPABASE_URL', 'https://example.supabase.co');
    vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', '');
    expect(createSupabaseAuthClient()).toBeNull();
    expect(mockCreateClient).not.toHaveBeenCalled();
  });

  it('returns null when only the publishable key is set', () => {
    vi.stubEnv('VITE_SUPABASE_URL', '');
    vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_test');
    expect(createSupabaseAuthClient()).toBeNull();
    expect(mockCreateClient).not.toHaveBeenCalled();
  });

  it('creates a client from both env vars and returns its auth slice', () => {
    vi.stubEnv('VITE_SUPABASE_URL', 'https://example.supabase.co');
    vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_test');

    const client = createSupabaseAuthClient();

    expect(mockCreateClient).toHaveBeenCalledWith('https://example.supabase.co', 'sb_publishable_test');
    expect(client).toBe(authSlice);
  });
});
