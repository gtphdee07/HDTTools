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

export function AuthProvider({ client, children }: { client: AuthClient | null; children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(client !== null);
  const [recovering, setRecovering] = useState(false);

  useEffect(() => {
    if (!client) return;
    let cancelled = false;
    const { data } = client.onAuthStateChange((event, next) => {
      setSession(next);
      if (event === 'PASSWORD_RECOVERY') setRecovering(true);
      if (event === 'SIGNED_OUT') setRecovering(false);
    });
    client.getSession().then(({ data: { session: current } }) => {
      if (cancelled) return;
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
            signUp,
            signIn,
            signOut,
            requestPasswordReset,
            updatePassword,
          }
        : SIGNED_OUT,
    [client, loading, session, recovering, signUp, signIn, signOut, requestPasswordReset, updatePassword],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
