import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { AuthProvider, useAuth } from './auth';
import type { AuthClient, AuthSession } from './auth';

// Interaction tests for account flows: the real screens against an in-memory
// fake of the Supabase auth client (the same seam the app uses in production).

function makeFakeSupabase() {
  const accounts = new Map<string, string>();
  let session: AuthSession | null = null;
  const listeners = new Set<(event: never, s: AuthSession | null) => void>();
  const emit = (event: string, s: AuthSession | null) => {
    session = s;
    listeners.forEach((l) => l(event as never, s));
  };
  const sessionFor = (email: string): AuthSession => ({
    access_token: `token-for-${email}`,
    user: { id: `id-${email}`, email },
  });

  const client = {
    getSession: vi.fn(async () => ({ data: { session }, error: null })),
    onAuthStateChange: vi.fn((cb: (event: never, s: AuthSession | null) => void) => {
      listeners.add(cb);
      return { data: { subscription: { unsubscribe: () => listeners.delete(cb) } } };
    }),
    signUp: vi.fn(async ({ email, password }: { email: string; password: string }) => {
      if (accounts.has(email)) return { data: { session: null }, error: { message: 'User already registered' } };
      accounts.set(email, password);
      return { data: { session: null }, error: null };
    }),
    signInWithPassword: vi.fn(async ({ email, password }: { email: string; password: string }) => {
      if (accounts.get(email) !== password) return { data: null, error: { message: 'Invalid login credentials' } };
      emit('SIGNED_IN', sessionFor(email));
      return { data: null, error: null };
    }),
    signOut: vi.fn(async () => {
      emit('SIGNED_OUT', null);
      return { error: null };
    }),
    resetPasswordForEmail: vi.fn(async () => ({ data: null, error: null })),
    updateUser: vi.fn(async () => ({ data: null, error: null })),
  };
  return {
    client: client as unknown as AuthClient & typeof client,
    accounts,
    emit,
    sessionFor,
  };
}

function TokenProbe() {
  const { accessToken } = useAuth();
  return <div data-testid="token">{accessToken ?? 'none'}</div>;
}

function renderApp(fake: ReturnType<typeof makeFakeSupabase>) {
  render(
    <AuthProvider client={fake.client}>
      <App />
      <TokenProbe />
    </AuthProvider>,
  );
  return userEvent.setup();
}

const headerSignIn = () => screen.getAllByRole('button', { name: 'Sign in' })[0];
const submitSignIn = () => screen.getAllByRole('button', { name: 'Sign in' }).at(-1)!;

async function fillCredentials(user: ReturnType<typeof userEvent.setup>, email: string, password: string) {
  await user.type(screen.getByLabelText('Email'), email);
  await user.type(screen.getByLabelText('Password'), password);
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe('Web accounts', () => {
  it('lets a visitor reach the free manual-entry flow without an account', async () => {
    const user = renderApp(makeFakeSupabase());
    await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
    expect(screen.getByRole('button', { name: 'Start New Rig' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Create account' })).not.toBeInTheDocument();
  });

  it('signs up, confirms by email, signs in, exposes the token, and signs out', async () => {
    const fake = makeFakeSupabase();
    const user = renderApp(fake);

    await user.click(headerSignIn());
    await user.click(screen.getByRole('button', { name: 'Create an account' }));
    await fillCredentials(user, 'pat@example.com', 'hunter22');
    await user.click(screen.getByRole('button', { name: 'Create account' }));
    expect(await screen.findByRole('status')).toHaveTextContent(/check your email/i);
    expect(fake.client.signUp).toHaveBeenCalledWith({ email: 'pat@example.com', password: 'hunter22' });

    await user.click(screen.getByRole('button', { name: 'Back to sign in' }));
    await user.clear(screen.getByLabelText('Email'));
    await user.clear(screen.getByLabelText('Password'));
    await fillCredentials(user, 'pat@example.com', 'hunter22');
    await user.click(submitSignIn());

    expect(await screen.findByText('Signed in as pat@example.com')).toBeInTheDocument();
    expect(screen.getByTestId('token')).toHaveTextContent('token-for-pat@example.com');

    await user.click(screen.getByRole('button', { name: 'Sign out' }));
    expect(await screen.findByRole('button', { name: 'Create an account' })).toBeInTheDocument();
    expect(screen.getByTestId('token')).toHaveTextContent('none');
  });

  it('shows the error when credentials are wrong', async () => {
    const user = renderApp(makeFakeSupabase());
    await user.click(headerSignIn());
    await fillCredentials(user, 'nobody@example.com', 'wrong-pass');
    await user.click(submitSignIn());
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid login credentials');
  });

  it('restores an existing session on load', async () => {
    const fake = makeFakeSupabase();
    fake.emit('SIGNED_IN', fake.sessionFor('back@example.com'));
    const user = renderApp(fake);
    await waitFor(() => expect(screen.getByTestId('token')).toHaveTextContent('token-for-back@example.com'));
    await user.click(screen.getByRole('button', { name: 'Account' }));
    expect(screen.getByText('Signed in as back@example.com')).toBeInTheDocument();
  });

  it('sends a password reset email', async () => {
    const fake = makeFakeSupabase();
    const user = renderApp(fake);
    await user.click(headerSignIn());
    await user.click(screen.getByRole('button', { name: 'Forgot password?' }));
    await user.type(screen.getByLabelText('Email'), 'pat@example.com');
    await user.click(screen.getByRole('button', { name: 'Send reset link' }));
    expect(await screen.findByRole('status')).toHaveTextContent(/password reset link/i);
    expect(fake.client.resetPasswordForEmail).toHaveBeenCalledWith('pat@example.com', {
      redirectTo: window.location.origin,
    });
  });

  it('opening the reset link lands on a new-password form that updates the password', async () => {
    const fake = makeFakeSupabase();
    const user = renderApp(fake);
    await screen.findByRole('button', { name: 'Sign in' });
    act(() => fake.emit('PASSWORD_RECOVERY', fake.sessionFor('pat@example.com')));

    await user.type(await screen.findByLabelText('New password'), 'brand-new-pass');
    await user.click(screen.getByRole('button', { name: 'Update password' }));
    await waitFor(() => expect(fake.client.updateUser).toHaveBeenCalledWith({ password: 'brand-new-pass' }));
    expect(await screen.findByText('Signed in as pat@example.com')).toBeInTheDocument();
  });

  it('explains that accounts are unavailable when Supabase is not configured', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(headerSignIn());
    expect(screen.getByText('Accounts unavailable')).toBeInTheDocument();
  });
});
