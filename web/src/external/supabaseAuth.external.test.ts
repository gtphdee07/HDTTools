import { beforeAll, describe, expect, it } from 'vitest';
import { createClient } from '@supabase/supabase-js';
import type { SupabaseClient } from '@supabase/supabase-js';

// External suite (ADR-0008): real calls to the live Supabase project, run only via
// `npm run test:external`. The "[supabase-auth]" name tag is what the wrapper filters on.
// Never creates a user and never triggers an email: sign-up and password reset are
// exercised only with a malformed address, which the server rejects before sending anything.

const REQUIRED = ['VITE_SUPABASE_URL', 'VITE_SUPABASE_PUBLISHABLE_KEY', 'WEB_EXTERNAL_TEST_EMAIL', 'WEB_EXTERNAL_TEST_PASSWORD'] as const;

type Config = Record<(typeof REQUIRED)[number], string>;

function readConfig(): Config {
  const env = import.meta.env as Record<string, string | undefined>;
  const missing = REQUIRED.filter((name) => !env[name]);
  if (missing.length > 0) {
    throw new Error(`External test credentials missing (set them in web/.env.local): ${missing.join(', ')}`);
  }
  return Object.fromEntries(REQUIRED.map((name) => [name, env[name]])) as Config;
}

const isJwt = (token: string) => /^[\w-]+\.[\w-]+\.[\w-]+$/.test(token);

describe('[supabase-auth] Supabase Auth live contract', () => {
  let cfg: Config;
  let supabase: SupabaseClient;

  beforeAll(() => {
    cfg = readConfig();
  });

  const freshClient = () =>
    createClient(cfg.VITE_SUPABASE_URL, cfg.VITE_SUPABASE_PUBLISHABLE_KEY, {
      auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
    });

  beforeAll(() => {
    supabase = freshClient();
  });

  it('accepts the project URL and publishable key', async () => {
    const accepted = await fetch(`${cfg.VITE_SUPABASE_URL}/auth/v1/settings`, {
      headers: { apikey: cfg.VITE_SUPABASE_PUBLISHABLE_KEY },
    });
    expect(accepted.status).toBe(200);
    const settings = (await accepted.json()) as { external?: { email?: boolean } };
    expect(settings.external?.email).toBe(true);

    const rejected = await fetch(`${cfg.VITE_SUPABASE_URL}/auth/v1/settings`, {
      headers: { apikey: 'not-a-real-key' },
    });
    expect(rejected.status).toBeGreaterThanOrEqual(401);
    expect(rejected.status).toBeLessThan(500);
  });

  it('returns a session with a three-part JWT, user id and confirmed email on sign-in', async () => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email: cfg.WEB_EXTERNAL_TEST_EMAIL,
      password: cfg.WEB_EXTERNAL_TEST_PASSWORD,
    });

    expect(error).toBeNull();
    expect(data.session).not.toBeNull();
    expect(isJwt(data.session!.access_token)).toBe(true);
    expect(data.session!.refresh_token).toBeTruthy();
    expect(data.user!.id).toMatch(/^[0-9a-f-]{36}$/);
    expect(data.user!.email).toBe(cfg.WEB_EXTERNAL_TEST_EMAIL.toLowerCase());
    expect(data.user!.email_confirmed_at).toBeTruthy();
    expect(data.session!.user.id).toBe(data.user!.id);
  });

  it('rejects a bad password with the invalid-credentials error and no session', async () => {
    const { data, error } = await freshClient().auth.signInWithPassword({
      email: cfg.WEB_EXTERNAL_TEST_EMAIL,
      password: `${cfg.WEB_EXTERNAL_TEST_PASSWORD}-definitely-wrong`,
    });

    expect(data.session).toBeNull();
    expect(error?.message).toBe('Invalid login credentials');
    expect(error?.status).toBe(400);
  });

  it('rejects an unknown email with the same invalid-credentials error and no session', async () => {
    const { data, error } = await freshClient().auth.signInWithPassword({
      email: `external-suite-unknown-${Date.now()}@example.com`,
      password: cfg.WEB_EXTERNAL_TEST_PASSWORD,
    });

    expect(data.session).toBeNull();
    expect(error?.message).toBe('Invalid login credentials');
    expect(error?.status).toBe(400);
  });

  it('journey: signs in, exposes the token, signs out, and the session is gone', async () => {
    const client = freshClient();
    const { data, error } = await client.auth.signInWithPassword({
      email: cfg.WEB_EXTERNAL_TEST_EMAIL,
      password: cfg.WEB_EXTERNAL_TEST_PASSWORD,
    });
    expect(error).toBeNull();

    const current = (await client.auth.getSession()).data.session;
    expect(current?.access_token).toBe(data.session!.access_token);

    const token = current!.access_token;
    expect((await client.auth.getUser(token)).error).toBeNull();

    expect((await client.auth.signOut()).error).toBeNull();

    expect((await client.auth.getSession()).data.session).toBeNull();
    expect((await client.auth.getUser(token)).error).not.toBeNull();
  });

  it('rejects sign-up with a malformed email before creating a user or sending mail', async () => {
    const { data, error } = await freshClient().auth.signUp({
      email: 'not-an-email',
      password: cfg.WEB_EXTERNAL_TEST_PASSWORD,
    });

    expect(data.user).toBeNull();
    expect(data.session).toBeNull();
    expect(error?.status).toBe(400);
    expect(error?.code).toBe('validation_failed');
  });

  it('rejects a password-reset request for a malformed email before sending mail', async () => {
    const { error } = await freshClient().auth.resetPasswordForEmail('not-an-email');

    expect(error?.status).toBe(400);
    expect(error?.code).toBe('validation_failed');
  });
});
