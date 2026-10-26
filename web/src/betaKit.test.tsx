import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { AuthProvider } from './auth';
import type { AuthClient } from './auth';
import { BillingProvider } from './billing';
import type { BillingClient } from './billing';

// The Web side of the tester kit (#181): the feedback link, the "Beta: test payments" label and the
// tester guide (betaGuide.test.ts), through the real screens with a fake auth client and a fake billing client.

const SESSION = { access_token: 'token-pat', user: { id: 'acct-pat', email: 'pat@example.com' } };

function makeAuth(signedIn: boolean) {
  return {
    getSession: vi.fn(async () => ({ data: { session: signedIn ? SESSION : null }, error: null })),
    onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: () => {} } } })),
    signUp: vi.fn(),
    signInWithPassword: vi.fn(),
    signOut: vi.fn(),
    resetPasswordForEmail: vi.fn(),
    updateUser: vi.fn(),
  } as unknown as AuthClient;
}

function makeBilling(isPro: boolean) {
  return {
    identify: vi.fn(async () => {}),
    getProOffer: vi.fn(async () => ({ price: '$9.99' })),
    getStatus: vi.fn(async () => ({ isPro, scanBalance: isPro ? 5 : 0 })),
    getScanPacks: vi.fn(async () => [{ id: 'pack_10', title: '10 scans', price: '$2.99' }]),
    purchasePro: vi.fn(),
    purchaseScanPack: vi.fn(),
  } as unknown as BillingClient;
}

function renderApp({ signedIn = true, isPro = false } = {}) {
  render(
    <AuthProvider client={makeAuth(signedIn)}>
      <BillingProvider client={makeBilling(isPro)}>
        <App />
      </BillingProvider>
    </AuthProvider>,
  );
  return userEvent.setup();
}

const BETA_LABEL = /Beta: test payments/;

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('Send feedback link', () => {
  it('is in the footer for a visitor and mails the feedback address', async () => {
    renderApp({ signedIn: false });
    const links = await screen.findAllByRole('link', { name: 'Send feedback' });
    expect(links).toHaveLength(1);
    expect(links[0].getAttribute('href')).toMatch(/^mailto:WTIAppDev@gmail\.com(\?|$)/);
  });

  it('is also on the Account screen of a signed-in user, with the same address', async () => {
    const user = renderApp();
    await user.click(await screen.findByRole('button', { name: 'Account' }));
    // The footer has one link; the Account card adds a second.
    await screen.findByText(/Signed in as pat@example.com/);
    const links = screen.getAllByRole('link', { name: 'Send feedback' });
    expect(links).toHaveLength(2);
    for (const link of links) expect(link.getAttribute('href')).toMatch(/^mailto:WTIAppDev@gmail\.com(\?|$)/);
  });
});

describe('Beta: test payments label', () => {
  it('shows on the Pro paywall when the beta flag is on', async () => {
    vi.stubEnv('VITE_BETA', 'true');
    const user = renderApp();
    await user.click(await screen.findByRole('button', { name: 'Account' }));
    await screen.findByRole('button', { name: 'Buy Pro' });
    expect(screen.getByText(BETA_LABEL)).toHaveTextContent(/test card/);
  });

  it('is missing from the Pro paywall when the flag is off', async () => {
    vi.stubEnv('VITE_BETA', '');
    const user = renderApp();
    await user.click(await screen.findByRole('button', { name: 'Account' }));
    await screen.findByRole('button', { name: 'Buy Pro' });
    expect(screen.queryByText(BETA_LABEL)).not.toBeInTheDocument();
  });

  it('shows on the scan-pack offers when the beta flag is on', async () => {
    vi.stubEnv('VITE_BETA', 'true');
    const user = renderApp({ isPro: true });
    await user.click(await screen.findByRole('button', { name: 'Account' }));
    await screen.findByRole('button', { name: 'Buy 10 scans' });
    expect(screen.getByText(BETA_LABEL)).toBeInTheDocument();
  });

  it('is missing from the scan-pack offers when the flag is off', async () => {
    vi.stubEnv('VITE_BETA', '');
    const user = renderApp({ isPro: true });
    await user.click(await screen.findByRole('button', { name: 'Account' }));
    await screen.findByRole('button', { name: 'Buy 10 scans' });
    expect(screen.queryByText(BETA_LABEL)).not.toBeInTheDocument();
  });
});
