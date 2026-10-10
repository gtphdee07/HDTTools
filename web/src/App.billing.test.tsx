import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { AuthProvider } from './auth';
import type { AuthClient, AuthSession } from './auth';
import { BillingProvider } from './billing';
import type { BillingClient, PurchaseOutcome } from './billing';

// Interaction tests for buying Pro: the real screens against a fake auth
// client and a fake billing client. The fake billing client behaves like the
// RevenueCat modal checkout: opening it pushes a history entry, and browser
// Back (popstate) cancels it - the SDK's only cancel path (purchases-js #973).

const SESSION: AuthSession = { access_token: 'token-pat', user: { id: 'acct-pat', email: 'pat@example.com' } };

function makeSignedInAuth(session: AuthSession | null = SESSION) {
  return {
    getSession: vi.fn(async () => ({ data: { session }, error: null })),
    onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: () => {} } } })),
    signUp: vi.fn(),
    signInWithPassword: vi.fn(),
    signOut: vi.fn(),
    resetPasswordForEmail: vi.fn(),
    updateUser: vi.fn(),
  } as unknown as AuthClient;
}

const STARTER_SCANS = 5;

function makeFakeBilling() {
  let isPro = false;
  let scanBalance = 0;
  let finish: ((outcome: PurchaseOutcome) => void) | null = null;
  let fail: ((error: Error) => void) | null = null;
  let detachBack: (() => void) | null = null;

  const client = {
    identify: vi.fn(async () => {}),
    getProOffer: vi.fn(async () => ({ price: '$9.99' })),
    getStatus: vi.fn(async () => ({ isPro, scanBalance })),
    purchasePro: vi.fn(
      () =>
        new Promise<PurchaseOutcome>((resolve, reject) => {
          window.history.pushState({ checkoutOpen: true }, '');
          const onBack = () => finishWith('cancelled');
          window.addEventListener('popstate', onBack);
          detachBack = () => window.removeEventListener('popstate', onBack);
          finish = resolve;
          fail = reject;
        }),
    ),
  };
  const finishWith = (outcome: PurchaseOutcome) => {
    detachBack?.();
    finish?.(outcome);
  };
  return {
    client: client as unknown as BillingClient & typeof client,
    // the buyer completes payment in the checkout
    completePayment: () => {
      isPro = true;
      scanBalance = STARTER_SCANS;
      finishWith('purchased');
    },
    // the payment provider reports a failure
    failPayment: (message: string) => {
      detachBack?.();
      fail?.(new Error(message));
    },
  };
}

function renderApp(billing: ReturnType<typeof makeFakeBilling> | null, auth: AuthClient | null = makeSignedInAuth()) {
  render(
    <AuthProvider client={auth}>
      <BillingProvider client={billing?.client ?? null}>
        <App />
      </BillingProvider>
    </AuthProvider>,
  );
  return userEvent.setup();
}

async function openAccount(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: 'Account' }));
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe('Buy Pro on Web', () => {
  it('shows a signed-in Free user their plan, scan balance and the Pro paywall with the not-certified statement', async () => {
    const billing = makeFakeBilling();
    const user = renderApp(billing);
    await openAccount(user);

    expect(await screen.findByText('Free plan')).toBeInTheDocument();
    expect(screen.getByText(/scan credits: 0/i)).toBeInTheDocument();
    expect(screen.getByText(/\$9\.99/)).toBeInTheDocument();
    expect(screen.getByText(/not certified DOT weights/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Buy Pro' })).toBeEnabled();
    expect(billing.client.identify).toHaveBeenCalledWith('acct-pat');
  });

  it('opens checkout, then shows Pro status and the starter scans after purchase', async () => {
    const billing = makeFakeBilling();
    const user = renderApp(billing);
    await openAccount(user);

    await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
    expect(billing.client.purchasePro).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'Close checkout' })).toBeInTheDocument();

    act(() => billing.completePayment());

    expect(await screen.findByText('Pro plan')).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`scan credits: ${STARTER_SCANS}`, 'i'))).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Buy Pro' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Close checkout' })).not.toBeInTheDocument();
  });

  it('stays Pro after purchase even if RevenueCat has not yet reported the entitlement', async () => {
    const billing = makeFakeBilling();
    const user = renderApp(billing);
    await openAccount(user);

    await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
    billing.client.getStatus.mockResolvedValue({ isPro: false, scanBalance: 0 });
    act(() => billing.completePayment());

    expect(await screen.findByText('Pro plan')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Buy Pro' })).not.toBeInTheDocument();
  });

  it('closes cleanly from the visible close control and allows a fresh retry', async () => {
    const billing = makeFakeBilling();
    const user = renderApp(billing);
    await openAccount(user);

    await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
    await user.click(screen.getByRole('button', { name: 'Close checkout' }));

    expect(await screen.findByRole('status')).toHaveTextContent(/not charged/i);
    expect(screen.queryByRole('button', { name: 'Close checkout' })).not.toBeInTheDocument();
    expect(screen.getByText('Free plan')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Buy Pro' }));
    expect(billing.client.purchasePro).toHaveBeenCalledTimes(2);
    act(() => billing.completePayment());
    expect(await screen.findByText('Pro plan')).toBeInTheDocument();
  });

  it('closes cleanly from the browser Back button and allows a fresh retry', async () => {
    const billing = makeFakeBilling();
    const user = renderApp(billing);
    await openAccount(user);

    await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
    act(() => window.history.back());

    expect(await screen.findByRole('status')).toHaveTextContent(/not charged/i);
    expect(screen.queryByRole('button', { name: 'Close checkout' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Buy Pro' }));
    expect(billing.client.purchasePro).toHaveBeenCalledTimes(2);
    act(() => billing.completePayment());
    expect(await screen.findByText('Pro plan')).toBeInTheDocument();
  });

  it('does not start a second checkout while one is open', async () => {
    const billing = makeFakeBilling();
    const user = renderApp(billing);
    await openAccount(user);

    await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
    expect(screen.getByRole('button', { name: 'Buy Pro' })).toBeDisabled();
    expect(billing.client.purchasePro).toHaveBeenCalledTimes(1);
  });

  it('shows an error when the purchase fails and lets the buyer try again', async () => {
    const billing = makeFakeBilling();
    const user = renderApp(billing);
    await openAccount(user);

    await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
    act(() => billing.failPayment('Your card was declined.'));

    expect(await screen.findByRole('alert')).toHaveTextContent('Your card was declined.');
    expect(screen.getByText('Free plan')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Buy Pro' })).toBeEnabled();
  });

  it('shows Pro straight away for a customer who already bought it', async () => {
    const billing = makeFakeBilling();
    billing.client.getStatus.mockResolvedValue({ isPro: true, scanBalance: 12 });
    const user = renderApp(billing);
    await openAccount(user);

    expect(await screen.findByText('Pro plan')).toBeInTheDocument();
    expect(screen.getByText(/scan credits: 12/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Buy Pro' })).not.toBeInTheDocument();
  });

  it('explains when Pro is not on sale right now', async () => {
    const billing = makeFakeBilling();
    billing.client.getProOffer.mockResolvedValue(null as never);
    const user = renderApp(billing);
    await openAccount(user);

    expect(await screen.findByText(/not available to buy right now/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Buy Pro' })).not.toBeInTheDocument();
  });

  it('offers no purchase to a visitor who is not signed in', async () => {
    const billing = makeFakeBilling();
    const user = renderApp(billing, makeSignedInAuth(null));
    await user.click(await screen.findByRole('button', { name: 'Sign in' }));

    expect(screen.queryByRole('button', { name: 'Buy Pro' })).not.toBeInTheDocument();
    expect(billing.client.identify).not.toHaveBeenCalled();
  });

  it('shows no plan or paywall when purchases are not set up on this site', async () => {
    const user = renderApp(null);
    await openAccount(user);

    expect(await screen.findByText('Signed in as pat@example.com')).toBeInTheDocument();
    expect(screen.queryByText(/plan$/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Buy Pro' })).not.toBeInTheDocument();
  });
});
