import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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
    // The real call sends the browser to Google, so nothing comes back here; tests that need the
    // visitor to return build a new app (see the Google tests below).
    signInWithOAuth: vi.fn(
      async (_creds: { provider: 'google'; options?: { redirectTo?: string } }): Promise<{
        data: null;
        error: { message: string } | null;
      }> => ({ data: null, error: null }),
    ),
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

afterEach(() => {
  window.history.replaceState(null, '', '/');
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

  it('leaves the email and password fields empty after sign out, for the next person at a shared browser', async () => {
    const fake = makeFakeSupabase();
    const user = renderApp(fake);

    // Typed but not submitted, then a session arrives some other way (another tab): the typed
    // values are still in the form's state when Sign out is pressed.
    await user.click(headerSignIn());
    await fillCredentials(user, 'pat@example.com', 'hunter22');
    act(() => fake.emit('SIGNED_IN', fake.sessionFor('pat@example.com')));
    await user.click(await screen.findByRole('button', { name: 'Sign out' }));

    expect(await screen.findByRole('button', { name: 'Create an account' })).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toHaveValue('');
    expect(screen.getByLabelText('Password')).toHaveValue('');
  });

  it('leaves the fields empty after signing in, so a later sign out cannot reveal them', async () => {
    const fake = makeFakeSupabase();
    fake.accounts.set('pat@example.com', 'hunter22');
    const user = renderApp(fake);

    await user.click(headerSignIn());
    await fillCredentials(user, 'pat@example.com', 'hunter22');
    await user.click(submitSignIn());
    await user.click(await screen.findByRole('button', { name: 'Sign out' }));

    expect(await screen.findByLabelText('Email')).toHaveValue('');
    expect(screen.getByLabelText('Password')).toHaveValue('');
  });

  it('does not keep the new password in the form after a password reset', async () => {
    const fake = makeFakeSupabase();
    const user = renderApp(fake);
    await screen.findByRole('button', { name: 'Sign in' });
    act(() => fake.emit('PASSWORD_RECOVERY', fake.sessionFor('pat@example.com')));
    await user.type(await screen.findByLabelText('New password'), 'brand-new-pass');
    await user.click(screen.getByRole('button', { name: 'Update password' }));
    await user.click(await screen.findByRole('button', { name: 'Sign out' }));

    expect(await screen.findByLabelText('Password')).toHaveValue('');
  });

  it('shows the email and password as typed while still signed out', async () => {
    const user = renderApp(makeFakeSupabase());
    await user.click(headerSignIn());
    await fillCredentials(user, 'pat@example.com', 'hunter22');
    expect(screen.getByLabelText('Email')).toHaveValue('pat@example.com');
    expect(screen.getByLabelText('Password')).toHaveValue('hunter22');
  });

  it('explains a confirmation or recovery link opened in a browser that did not ask for it', async () => {
    // PKCE keeps a code verifier in the browser that asked; elsewhere the ?code= link signs nobody in.
    window.history.replaceState(null, '', '/?code=abc123');
    renderApp(makeFakeSupabase());

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/different browser or device/i);
    expect(alert).toHaveTextContent(/confirm/i);
    expect(alert).toHaveTextContent(/request a new/i);
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(window.location.search).toBe('');
  });

  it('tells the visitor an error redirect in the query string did not sign them in', async () => {
    window.history.replaceState(null, '', '/?error=access_denied&error_code=otp_expired&error_description=expired');
    renderApp(makeFakeSupabase());

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid, expired or already used/i);
    expect(window.location.search).toBe('');
  });

  it('tells the visitor an expired link in the URL fragment did not sign them in', async () => {
    window.history.replaceState(null, '', '/#error=access_denied&error_code=otp_expired&error_description=expired');
    renderApp(makeFakeSupabase());

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid, expired or already used/i);
    expect(screen.getByTestId('token')).toHaveTextContent('none');
    expect(window.location.hash).toBe('');
  });

  it('says nothing about links when the page was opened normally', async () => {
    renderApp(makeFakeSupabase());
    await screen.findByRole('button', { name: 'Sign in' });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
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

  it('offers Continue with Google on sign in and create account, and starts it for this site', async () => {
    const fake = makeFakeSupabase();
    const user = renderApp(fake);

    await user.click(headerSignIn());
    await user.click(screen.getByRole('button', { name: 'Create an account' }));
    expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Back to sign in' }));
    await user.click(screen.getByRole('button', { name: 'Continue with Google' }));

    expect(fake.client.signInWithOAuth).toHaveBeenCalledWith({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    });
  });

  it('does not offer Google on the password reset form, and offers no Apple button anywhere (#77)', async () => {
    const user = renderApp(makeFakeSupabase());
    await user.click(headerSignIn());
    expect(screen.queryByRole('button', { name: /apple/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Forgot password?' }));
    expect(screen.queryByRole('button', { name: 'Continue with Google' })).not.toBeInTheDocument();
  });

  it('shows the error in the usual style when Google sign-in cannot start', async () => {
    const fake = makeFakeSupabase();
    fake.client.signInWithOAuth.mockResolvedValueOnce({ data: null, error: { message: 'Unsupported provider: provider is not enabled' } });
    const user = renderApp(fake);

    await user.click(headerSignIn());
    await user.click(screen.getByRole('button', { name: 'Continue with Google' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Unsupported provider: provider is not enabled');
    expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeEnabled();
  });

  it('lands the visitor signed in when they return from Google', async () => {
    const fake = makeFakeSupabase();
    const user = renderApp(fake);
    await user.click(headerSignIn());
    await user.click(screen.getByRole('button', { name: 'Continue with Google' }));
    cleanup();

    // The page reloads at the site root; Supabase has already exchanged the ?code= for a session.
    const returned = makeFakeSupabase();
    returned.emit('SIGNED_IN', returned.sessionFor('pat@gmail.com'));
    renderApp(returned);

    await waitFor(() => expect(screen.getByTestId('token')).toHaveTextContent('token-for-pat@gmail.com'));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Account' }));
    expect(screen.getByText('Signed in as pat@gmail.com')).toBeInTheDocument();
  });

  it('tells the visitor Google did not sign them in when they cancel or it fails, not that an email link is dead', async () => {
    const user = renderApp(makeFakeSupabase());
    await user.click(headerSignIn());
    await user.click(screen.getByRole('button', { name: 'Continue with Google' }));
    cleanup();

    window.history.replaceState(null, '', '/?error=access_denied&error_code=server_error&error_description=denied');
    renderApp(makeFakeSupabase());

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/google sign-in did not finish/i);
    expect(alert).not.toHaveTextContent(/email link/i);
    expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeInTheDocument();
    expect(window.location.search).toBe('');
    expect(screen.getByTestId('token')).toHaveTextContent('none');
  });

  it('says the same when the code from Google could not be used in this browser', async () => {
    const user = renderApp(makeFakeSupabase());
    await user.click(headerSignIn());
    await user.click(screen.getByRole('button', { name: 'Continue with Google' }));
    cleanup();

    window.history.replaceState(null, '', '/?code=abc123');
    renderApp(makeFakeSupabase());

    expect(await screen.findByRole('alert')).toHaveTextContent(/google sign-in did not finish/i);
    expect(window.location.search).toBe('');
  });

  it('does not blame Google for a later email link once the Google return has been handled', async () => {
    const user = renderApp(makeFakeSupabase());
    await user.click(headerSignIn());
    await user.click(screen.getByRole('button', { name: 'Continue with Google' }));
    cleanup();

    // The visitor backed out of Google: the page reloaded with nothing in the URL.
    renderApp(makeFakeSupabase());
    await screen.findByRole('button', { name: 'Sign in' });
    cleanup();

    window.history.replaceState(null, '', '/?code=abc123');
    renderApp(makeFakeSupabase());
    expect(await screen.findByRole('alert')).toHaveTextContent(/different browser or device/i);
  });

  it('does not blame Google for a later email link when Google could not even be started', async () => {
    const fake = makeFakeSupabase();
    fake.client.signInWithOAuth.mockResolvedValueOnce({ data: null, error: { message: 'Unsupported provider: provider is not enabled' } });
    const user = renderApp(fake);
    await user.click(headerSignIn());
    await user.click(screen.getByRole('button', { name: 'Continue with Google' }));
    await screen.findByRole('alert');
    cleanup();

    // Nobody went to Google, so this unused code is from an email link.
    window.history.replaceState(null, '', '/?code=abc123');
    renderApp(makeFakeSupabase());
    expect(await screen.findByRole('alert')).toHaveTextContent(/different browser or device/i);
  });

  it('explains that accounts are unavailable when Supabase is not configured', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(headerSignIn());
    expect(screen.getByText('Accounts unavailable')).toBeInTheDocument();
  });
});
