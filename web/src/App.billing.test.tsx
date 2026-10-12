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

const SAM: AuthSession = { access_token: 'token-sam', user: { id: 'acct-sam', email: 'sam@example.com' } };

// An auth client the test can drive from outside: it starts signed in as Pat and
// `emit` signs the app in as someone else, or out (null).
function makeDrivableAuth() {
  let listener: ((event: string, session: AuthSession | null) => void) | null = null;
  const client = {
    getSession: vi.fn(async () => ({ data: { session: SESSION }, error: null })),
    onAuthStateChange: vi.fn((cb: (event: string, session: AuthSession | null) => void) => {
      listener = cb;
      return { data: { subscription: { unsubscribe: () => {} } } };
    }),
    signUp: vi.fn(),
    signInWithPassword: vi.fn(),
    signOut: vi.fn(),
    resetPasswordForEmail: vi.fn(),
    updateUser: vi.fn(),
  } as unknown as AuthClient;
  return {
    client,
    emit: (session: AuthSession | null) => act(() => listener?.(session ? 'SIGNED_IN' : 'SIGNED_OUT', session)),
  };
}

const STARTER_SCANS = 5;

// With `lazyModal`, purchasePro returns before the SDK has opened the modal (it
// loads in the background), so no history entry exists until `openModal()`.
function makeFakeBilling({ lazyModal = false }: { lazyModal?: boolean } = {}) {
  // RevenueCat keeps status per customer; the purchase lands on whoever started it.
  const proAccounts = new Set<string>();
  let currentAccount: string | null = null;
  let purchaser: string | null = null;
  let finish: ((outcome: PurchaseOutcome) => void) | null = null;
  let fail: ((error: Error) => void) | null = null;
  let detachBack: (() => void) | null = null;

  const openModal = () => {
    window.history.pushState({ checkoutOpen: true }, '');
    const onBack = () => finishWith('cancelled');
    window.addEventListener('popstate', onBack);
    detachBack = () => window.removeEventListener('popstate', onBack);
  };

  const client = {
    identify: vi.fn(async (accountId: string) => {
      currentAccount = accountId;
    }),
    getProOffer: vi.fn(async () => ({ price: '$9.99' })),
    getStatus: vi.fn(async () => {
      const isPro = currentAccount !== null && proAccounts.has(currentAccount);
      return { isPro, scanBalance: isPro ? STARTER_SCANS : 0 };
    }),
    purchasePro: vi.fn(
      () =>
        new Promise<PurchaseOutcome>((resolve, reject) => {
          purchaser = currentAccount;
          if (!lazyModal) openModal();
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
    openModal,
    // the buyer completes payment in the checkout
    completePayment: () => {
      if (purchaser) proAccounts.add(purchaser);
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
    expect(screen.getByText(/Scan Credit balance: 0/)).toBeInTheDocument();
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
    expect(screen.getByText(new RegExp(`Scan Credit balance: ${STARTER_SCANS}`))).toBeInTheDocument();
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

  it('does not hand the Pro of a checkout that settles late to the account that signed in afterwards', async () => {
    const billing = makeFakeBilling();
    const auth = makeDrivableAuth();
    const user = renderApp(billing, auth.client);
    await openAccount(user);

    await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
    auth.emit(SAM);
    expect(await screen.findByText('Signed in as sam@example.com')).toBeInTheDocument();
    expect(await screen.findByText('Free plan')).toBeInTheDocument();

    await act(async () => billing.completePayment());

    expect(screen.getByText('Free plan')).toBeInTheDocument();
    expect(screen.getByText(/Scan Credit balance: 0/)).toBeInTheDocument();
    expect(screen.queryByText(/pro is unlocked/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Buy Pro' })).toBeInTheDocument();
  });

  it('does not let a checkout that settles after sign-out change the next account that signs in', async () => {
    const billing = makeFakeBilling();
    const auth = makeDrivableAuth();
    const user = renderApp(billing, auth.client);
    await openAccount(user);

    await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
    auth.emit(null);
    await act(async () => billing.completePayment());
    auth.emit(SAM);

    expect(await screen.findByText('Signed in as sam@example.com')).toBeInTheDocument();
    expect(await screen.findByText('Free plan')).toBeInTheDocument();
    expect(screen.getByText(/Scan Credit balance: 0/)).toBeInTheDocument();
    expect(screen.queryByText(/pro is unlocked/i)).not.toBeInTheDocument();
  });

  it('does not show another account the error or the cancel notice of an earlier checkout', async () => {
    const billing = makeFakeBilling();
    const auth = makeDrivableAuth();
    const user = renderApp(billing, auth.client);
    await openAccount(user);

    await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
    auth.emit(SAM);
    expect(await screen.findByText('Free plan')).toBeInTheDocument();
    await act(async () => billing.failPayment('Your card was declined.'));

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('does not navigate away when Close checkout is pressed before the SDK has opened the modal, and closes it once it has', async () => {
    const billing = makeFakeBilling({ lazyModal: true });
    const user = renderApp(billing);
    await openAccount(user);
    const lengthBefore = window.history.length;
    const back = vi.spyOn(window.history, 'back');

    await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
    await user.click(screen.getByRole('button', { name: 'Close checkout' }));
    expect(back).not.toHaveBeenCalled();
    expect(window.history.length).toBe(lengthBefore);
    expect(screen.getByRole('button', { name: 'Close checkout' })).toBeInTheDocument();

    act(() => billing.openModal());
    await user.click(screen.getByRole('button', { name: 'Close checkout' }));
    expect(back).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole('status')).toHaveTextContent(/not charged/i);
    expect(screen.queryByRole('button', { name: 'Close checkout' })).not.toBeInTheDocument();
    back.mockRestore();
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

  describe('when the plan fails to load', () => {
    it('shows the error with a Try again action and no paywall', async () => {
      const billing = makeFakeBilling();
      billing.client.getStatus.mockRejectedValueOnce(new Error('RevenueCat is unreachable.'));
      const user = renderApp(billing);
      await openAccount(user);

      expect(await screen.findByRole('alert')).toHaveTextContent('RevenueCat is unreachable.');
      expect(screen.getByRole('button', { name: 'Try again' })).toBeEnabled();
      expect(screen.queryByRole('button', { name: 'Buy Pro' })).not.toBeInTheDocument();
      expect(screen.queryByText('Free plan')).not.toBeInTheDocument();
    });

    it('reloads the plan, balance and offer on Try again and shows the Free plan with the paywall', async () => {
      const billing = makeFakeBilling();
      billing.client.getStatus.mockRejectedValueOnce(new Error('RevenueCat is unreachable.'));
      const user = renderApp(billing);
      await openAccount(user);

      await user.click(await screen.findByRole('button', { name: 'Try again' }));

      expect(await screen.findByText('Free plan')).toBeInTheDocument();
      expect(screen.getByText(/Scan Credit balance: 0/)).toBeInTheDocument();
      expect(screen.getByText(/\$9\.99/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Buy Pro' })).toBeEnabled();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
      expect(billing.client.getStatus).toHaveBeenCalledTimes(2);
      expect(billing.client.getProOffer).toHaveBeenCalledTimes(2);
      expect(billing.client.identify).toHaveBeenCalledTimes(2);
    });

    it('shows the Pro plan without a paywall when the retry finds a Pro customer', async () => {
      const billing = makeFakeBilling();
      billing.client.getStatus.mockRejectedValueOnce(new Error('RevenueCat is unreachable.'));
      billing.client.getStatus.mockResolvedValueOnce({ isPro: true, scanBalance: 12 });
      const user = renderApp(billing);
      await openAccount(user);

      await user.click(await screen.findByRole('button', { name: 'Try again' }));

      expect(await screen.findByText('Pro plan')).toBeInTheDocument();
      expect(screen.getByText(/Scan Credit balance: 12/)).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Buy Pro' })).not.toBeInTheDocument();
    });

    it('shows the error again, with Try again still offered, when the retry fails too', async () => {
      const billing = makeFakeBilling();
      billing.client.getStatus.mockRejectedValueOnce(new Error('First failure.'));
      billing.client.getStatus.mockRejectedValueOnce(new Error('Second failure.'));
      const user = renderApp(billing);
      await openAccount(user);

      await user.click(await screen.findByRole('button', { name: 'Try again' }));

      expect(await screen.findByRole('alert')).toHaveTextContent('Second failure.');
      expect(screen.getByRole('button', { name: 'Try again' })).toBeEnabled();
      expect(screen.queryByRole('button', { name: 'Buy Pro' })).not.toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: 'Try again' }));
      expect(await screen.findByText('Free plan')).toBeInTheDocument();
    });

    it('recovers from a failed offer or identify call the same way', async () => {
      const billing = makeFakeBilling();
      billing.client.identify.mockRejectedValueOnce(new Error('Could not identify.'));
      const user = renderApp(billing);
      await openAccount(user);

      expect(await screen.findByRole('alert')).toHaveTextContent('Could not identify.');
      await user.click(screen.getByRole('button', { name: 'Try again' }));
      expect(await screen.findByText('Free plan')).toBeInTheDocument();
      expect(billing.client.identify).toHaveBeenLastCalledWith('acct-pat');
    });

    it('never starts a checkout when Try again is used', async () => {
      const billing = makeFakeBilling();
      billing.client.getStatus.mockRejectedValueOnce(new Error('First failure.'));
      billing.client.getStatus.mockRejectedValueOnce(new Error('Second failure.'));
      const user = renderApp(billing);
      await openAccount(user);

      await user.click(await screen.findByRole('button', { name: 'Try again' }));
      await screen.findByText('Second failure.');
      await user.click(screen.getByRole('button', { name: 'Try again' }));
      await screen.findByText('Free plan');

      expect(billing.client.purchasePro).not.toHaveBeenCalled();
      expect(screen.queryByRole('button', { name: 'Close checkout' })).not.toBeInTheDocument();
    });

    it('does not apply a retry that settles after another account signed in', async () => {
      const billing = makeFakeBilling();
      const auth = makeDrivableAuth();
      // Pat's first load fails; Pat's retry then hangs until the test settles it with a Pro answer.
      let settlePat: (status: { isPro: boolean; scanBalance: number }) => void = () => {};
      billing.client.getStatus.mockRejectedValueOnce(new Error('First failure.'));
      billing.client.getStatus.mockReturnValueOnce(new Promise((resolve) => (settlePat = resolve)));
      const user = renderApp(billing, auth.client);
      await openAccount(user);
      await user.click(await screen.findByRole('button', { name: 'Try again' }));
      expect(await screen.findByText('Loading your plan...')).toBeInTheDocument();

      auth.emit(SAM);
      expect(await screen.findByText('Signed in as sam@example.com')).toBeInTheDocument();
      expect(await screen.findByText('Free plan')).toBeInTheDocument();
      await act(async () => settlePat({ isPro: true, scanBalance: 99 }));

      expect(screen.getByText('Free plan')).toBeInTheDocument();
      expect(screen.queryByText('Pro plan')).not.toBeInTheDocument();
      expect(screen.queryByText(/Scan Credit balance: 99/)).not.toBeInTheDocument();
    });

    it('does not offer Try again for a failed purchase, only for a failed load', async () => {
      const billing = makeFakeBilling();
      const user = renderApp(billing);
      await openAccount(user);

      await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
      act(() => billing.failPayment('Your card was declined.'));

      expect(await screen.findByRole('alert')).toHaveTextContent('Your card was declined.');
      expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
    });
  });

  it('shows Pro straight away for a customer who already bought it', async () => {
    const billing = makeFakeBilling();
    billing.client.getStatus.mockResolvedValue({ isPro: true, scanBalance: 12 });
    const user = renderApp(billing);
    await openAccount(user);

    expect(await screen.findByText('Pro plan')).toBeInTheDocument();
    expect(screen.getByText(/Scan Credit balance: 12/)).toBeInTheDocument();
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
