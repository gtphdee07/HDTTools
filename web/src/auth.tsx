import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { getSupabaseClient } from './supabaseClient';

interface AuthUser {
  id: string;
  email?: string;
}

export interface AuthSession {
  access_token: string;
  user: AuthUser;
}

type AuthEvent = 'INITIAL_SESSION' | 'SIGNED_IN' | 'SIGNED_OUT' | 'PASSWORD_RECOVERY' | 'TOKEN_REFRESHED' | 'USER_UPDATED';

interface AuthResult<T = unknown> {
  data: T;
  error: { message: string } | null;
}

// The slice of Supabase's auth client this app uses - kept narrow so tests can fake it.
export interface AuthClient {
  getSession(): Promise<AuthResult<{ session: AuthSession | null }>>;
  onAuthStateChange(cb: (event: AuthEvent, session: AuthSession | null) => void): {
    data: { subscription: { unsubscribe(): void } };
  };
  signUp(creds: { email: string; password: string }): Promise<AuthResult<{ session: AuthSession | null }>>;
  signInWithPassword(creds: { email: string; password: string }): Promise<AuthResult<unknown>>;
  signOut(): Promise<{ error: { message: string } | null }>;
  resetPasswordForEmail(email: string, options?: { redirectTo?: string }): Promise<AuthResult<unknown>>;
  updateUser(attrs: { password: string }): Promise<AuthResult<unknown>>;
}

export interface ActionResult {
  error?: string;
  // sign-up succeeded but the account must be confirmed by email before signing in
  needsConfirmation?: boolean;
}

export interface AuthState {
  configured: boolean;
  loading: boolean;
  user: AuthUser | null;
  // The signed-in session's JWT, for authenticating calls to later services; null when signed out.
  accessToken: string | null;
  // True after the user opens a password-reset email link, until they set a new password.
  recovering: boolean;
  // Set when the page was opened from an email link that could not sign anyone in here (see takeUnusedLinkProblem).
  linkProblem: string | null;
  signUp(email: string, password: string): Promise<ActionResult>;
  signIn(email: string, password: string): Promise<ActionResult>;
  signOut(): Promise<ActionResult>;
  requestPasswordReset(email: string): Promise<ActionResult>;
  updatePassword(password: string): Promise<ActionResult>;
}

const unavailable = async (): Promise<ActionResult> => ({ error: 'Accounts are not available right now.' });

const SIGNED_OUT: AuthState = {
  configured: false,
  loading: false,
  user: null,
  accessToken: null,
  recovering: false,
  linkProblem: null,
  signUp: unavailable,
  signIn: unavailable,
  signOut: unavailable,
  requestPasswordReset: unavailable,
  updatePassword: unavailable,
};

const AuthContext = createContext<AuthState>(SIGNED_OUT);

export function useAuth(): AuthState {
  return useContext(AuthContext);
}

export function createSupabaseAuthClient(): AuthClient | null {
  const client = getSupabaseClient();
  return client ? (client.auth as unknown as AuthClient) : null;
}

const fail = (error: { message: string } | null): ActionResult => (error ? { error: error.message } : {});

const UNUSED_CODE_LINK =
  'That email link could not sign you in here. It was opened in a different browser or device than the one you requested it from, or it has expired or already been used. ' +
  'If it was a confirmation link, your email may already be confirmed: try signing in with your password. ' +
  'If it was a password reset link, request a new one from this browser.';
const DEAD_LINK = 'That email link is invalid, expired or already used, so it did not sign you in. Request a new one.';
const CALLBACK_PARAMS = ['access_token', 'error', 'error_description'];

// Email links come back as ?code=... (PKCE). Supabase's client exchanges the code for a session and
// removes it from the URL, but only in the browser that holds the code verifier (and while the code
// is still good); otherwise the code is left in place and nothing happens. Called once the client has
// finished starting up: any callback still in the URL was not used. Returns what to tell the visitor,
// and tidies the URL.
function takeUnusedLinkProblem(): string | null {
  const url = new URL(window.location.href);
  const fragment = new URLSearchParams(url.hash.slice(1));
  const unusedCode = url.searchParams.has('code');
  const deadInFragment = CALLBACK_PARAMS.some((p) => fragment.has(p));
  const deadInQuery = CALLBACK_PARAMS.some((p) => url.searchParams.has(p));
  if (!unusedCode && !deadInFragment && !deadInQuery) return null;
  for (const p of ['code', 'error_code', ...CALLBACK_PARAMS]) url.searchParams.delete(p);
  if (deadInFragment) url.hash = '';
  window.history.replaceState(window.history.state, '', url.toString());
  return deadInFragment || deadInQuery ? DEAD_LINK : UNUSED_CODE_LINK;
}

export function AuthProvider({ client, children }: { client: AuthClient | null; children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(client !== null);
  const [recovering, setRecovering] = useState(false);
  const [linkProblem, setLinkProblem] = useState<string | null>(null);

  useEffect(() => {
    if (!client) return;
    let cancelled = false;
    const { data } = client.onAuthStateChange((event, next) => {
      setSession(next);
      if (next) setLinkProblem(null);
      if (event === 'PASSWORD_RECOVERY') setRecovering(true);
      if (event === 'SIGNED_OUT') setRecovering(false);
    });
    client.getSession().then(({ data: { session: current } }) => {
      if (cancelled) return;
      const problem = takeUnusedLinkProblem();
      if (!current) setLinkProblem(problem);
      setSession((prev) => prev ?? current);
      setLoading(false);
    });
    return () => {
      cancelled = true;
      data.subscription.unsubscribe();
    };
  }, [client]);

  const signUp = useCallback(
    async (email: string, password: string): Promise<ActionResult> => {
      const { data, error } = await client!.signUp({ email, password });
      if (error) return fail(error);
      return data.session ? {} : { needsConfirmation: true };
    },
    [client],
  );
  const signIn = useCallback(
    async (email: string, password: string) => fail((await client!.signInWithPassword({ email, password })).error),
    [client],
  );
  const signOut = useCallback(async () => fail((await client!.signOut()).error), [client]);
  const requestPasswordReset = useCallback(
    async (email: string) => fail((await client!.resetPasswordForEmail(email, { redirectTo: window.location.origin })).error),
    [client],
  );
  const updatePassword = useCallback(
    async (password: string): Promise<ActionResult> => {
      const { error } = await client!.updateUser({ password });
      if (!error) setRecovering(false);
      return fail(error);
    },
    [client],
  );

  const value = useMemo<AuthState>(
    () =>
      client
        ? {
            configured: true,
            loading,
            user: session?.user ?? null,
            accessToken: session?.access_token ?? null,
            recovering,
            linkProblem,
            signUp,
            signIn,
            signOut,
            requestPasswordReset,
            updatePassword,
          }
        : SIGNED_OUT,
    [client, loading, session, recovering, linkProblem, signUp, signIn, signOut, requestPasswordReset, updatePassword],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
