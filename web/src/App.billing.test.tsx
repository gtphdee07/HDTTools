import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { AuthProvider } from './auth';
import type { AuthClient, AuthSession } from './auth';
import { BillingProvider, useBilling } from './billing';
import type { BillingState } from './billing';
import type { BillingClient, PurchaseOutcome, ScanRecheck } from './billing';

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
// With `lateGrant`, RevenueCat has the purchase but has not yet granted the starter
// scans: the balance stays 0 until the test calls `grantScans()`.
function makeFakeBilling({ lazyModal = false, lateGrant = false }: { lazyModal?: boolean; lateGrant?: boolean } = {}) {
  // RevenueCat keeps status per customer; the purchase lands on whoever started it.
  const proAccounts = new Set<string>();
  const grantedAccounts = new Set<string>();
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
      const granted = currentAccount !== null && grantedAccounts.has(currentAccount);
      return { isPro, scanBalance: isPro && granted ? STARTER_SCANS : 0 };
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
      if (purchaser) {
        proAccounts.add(purchaser);
        if (!lateGrant) grantedAccounts.add(purchaser);
      }
      finishWith('purchased');
    },
    // RevenueCat grants the starter bundle to whoever bought
    grantScans: () => {
      if (purchaser) grantedAccounts.add(purchaser);
    },
    // the payment provider reports a failure
    failPayment: (message: string) => {
      detachBack?.();
      fail?.(new Error(message));
    },
  };
}

// A short recheck window keeps the late-grant tests quick: 10 rechecks, 10ms apart.
const RECHECK: ScanRecheck = { intervalMs: 10, windowMs: 100, checkTimeoutMs: 50 };
const RECHECKS_IN_WINDOW = RECHECK.windowMs / RECHECK.intervalMs;
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function renderApp(
  billing: ReturnType<typeof makeFakeBilling> | null,
  auth: AuthClient | null = makeSignedInAuth(),
  scanRecheck: ScanRecheck = RECHECK,
) {
  const view = render(
    <AuthProvider client={auth}>
      <BillingProvider client={billing?.client ?? null} scanRecheck={scanRecheck}>
        <App />
      </BillingProvider>
    </AuthProvider>,
  );
  return Object.assign(userEvent.setup(), { unmount: view.unmount });
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
    expect(await screen.findByText(new RegExp(`Scan Credit balance: ${STARTER_SCANS}`))).toBeInTheDocument();
    expect(screen.queryByText(/updating your scans/i)).not.toBeInTheDocument();
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

  describe('when the starter scans arrive after the purchase', () => {
    // Buys Pro with the grant held back, and waits until the Account shows the waiting state.
    async function buyWithLateGrant(billing: ReturnType<typeof makeFakeBilling>, auth?: AuthClient) {
      const user = renderApp(billing, auth);
      await openAccount(user);
      await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
      act(() => billing.completePayment());
      await screen.findByText(/updating your scans/i);
      return user;
    }

    it('shows an updating state while it waits, with the user on Pro, then the balance once the grant lands', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      await buyWithLateGrant(billing);

      expect(screen.getByText('Pro plan')).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Buy Pro' })).not.toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();

      await act(async () => {
        await wait(RECHECK.intervalMs * 3);
        billing.grantScans();
      });

      expect(await screen.findByText(new RegExp(`Scan Credit balance: ${STARTER_SCANS}`))).toBeInTheDocument();
      expect(screen.queryByText(/updating your scans/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/may take a minute/i)).not.toBeInTheDocument();
      expect(screen.getByText('Pro plan')).toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('stops rechecking once the balance has changed', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      await buyWithLateGrant(billing);
      act(() => billing.grantScans());
      await screen.findByText(new RegExp(`Scan Credit balance: ${STARTER_SCANS}`));
      const calls = billing.client.getStatus.mock.calls.length;

      await act(async () => wait(RECHECK.windowMs * 2));

      expect(billing.client.getStatus).toHaveBeenCalledTimes(calls);
    });

    it('tells the user scans may take a minute, with no error and still on Pro, when the grant never arrives in the window', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      await buyWithLateGrant(billing);

      expect(await screen.findByText(/may take a minute to appear/i, undefined, { timeout: 2000 })).toBeInTheDocument();

      expect(screen.queryByText(/updating your scans/i)).not.toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.getByText('Pro plan')).toBeInTheDocument();
      expect(screen.getByText(/Scan Credit balance: 0/)).toBeInTheDocument();
    });

    it('never rechecks after the window ends', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      await buyWithLateGrant(billing);
      await screen.findByText(/may take a minute to appear/i, undefined, { timeout: 2000 });
      // one load when the Account opened, then the first check and each recheck in the window
      expect(billing.client.getStatus).toHaveBeenCalledTimes(1 + 1 + RECHECKS_IN_WINDOW);

      await act(async () => wait(RECHECK.windowMs * 2));

      expect(billing.client.getStatus).toHaveBeenCalledTimes(1 + 1 + RECHECKS_IN_WINDOW);
    });

    it('keeps rechecking through a failed check and shows no error when a later one finds the grant', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      const user = renderApp(billing);
      await openAccount(user);
      await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
      billing.client.getStatus.mockRejectedValueOnce(new Error('RevenueCat is unreachable.'));
      act(() => billing.completePayment());
      await screen.findByText(/updating your scans/i);
      act(() => billing.grantScans());

      expect(await screen.findByText(new RegExp(`Scan Credit balance: ${STARTER_SCANS}`))).toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('asks the user to reload when every check in the window failed', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      const user = renderApp(billing);
      await openAccount(user);
      await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
      billing.client.getStatus.mockRejectedValue(new Error('RevenueCat is unreachable.'));
      act(() => billing.completePayment());

      expect(await screen.findByRole('alert', undefined, { timeout: 2000 })).toHaveTextContent(/could not refresh your scan balance/i);
      expect(screen.queryByText(/updating your scans/i)).not.toBeInTheDocument();
      expect(screen.getByText('Pro plan')).toBeInTheDocument();
    });

    it('shows the plain message, not an error, when the last check fails after earlier ones saw no change', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      const user = renderApp(billing);
      await openAccount(user);
      await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
      // the first check answers "no change", every later one fails, including the last
      billing.client.getStatus.mockResolvedValueOnce({ isPro: true, scanBalance: 0 });
      billing.client.getStatus.mockRejectedValue(new Error('RevenueCat is unreachable.'));
      act(() => billing.completePayment());

      expect(await screen.findByText(/may take a minute to appear/i, undefined, { timeout: 2000 })).toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('keeps the user on Pro while RevenueCat still reports the entitlement as missing', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      const user = renderApp(billing);
      await openAccount(user);
      await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
      billing.client.getStatus.mockResolvedValue({ isPro: false, scanBalance: 0 });
      act(() => billing.completePayment());
      await screen.findByText(/updating your scans/i);
      await act(async () => wait(RECHECK.intervalMs * 3));

      expect(screen.getByText('Pro plan')).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Buy Pro' })).not.toBeInTheDocument();

      billing.client.getStatus.mockResolvedValue({ isPro: true, scanBalance: STARTER_SCANS });
      expect(await screen.findByText(new RegExp(`Scan Credit balance: ${STARTER_SCANS}`))).toBeInTheDocument();
      expect(screen.getByText('Pro plan')).toBeInTheDocument();
    });

    it('compares against the balance the user already had, not against zero', async () => {
      const billing = makeFakeBilling();
      billing.client.getStatus.mockResolvedValue({ isPro: false, scanBalance: 3 });
      const user = renderApp(billing);
      await openAccount(user);
      expect(await screen.findByText(/Scan Credit balance: 3/)).toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: 'Buy Pro' }));
      act(() => billing.completePayment());

      // an unchanged 3 is not a grant, so it keeps waiting
      await screen.findByText(/updating your scans/i);
      await act(async () => wait(RECHECK.intervalMs * 3));
      expect(screen.getByText(/updating your scans/i)).toBeInTheDocument();

      billing.client.getStatus.mockResolvedValue({ isPro: true, scanBalance: 3 + STARTER_SCANS });
      expect(await screen.findByText(new RegExp(`Scan Credit balance: ${3 + STARTER_SCANS}`))).toBeInTheDocument();
    });

    it('does not stay on "updating" when a check hangs: the next one still finds the grant', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      const user = renderApp(billing);
      await openAccount(user);
      await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
      billing.client.getStatus.mockReturnValueOnce(new Promise(() => {}));
      act(() => billing.completePayment());
      await screen.findByText(/updating your scans/i);
      act(() => billing.grantScans());

      expect(await screen.findByText(new RegExp(`Scan Credit balance: ${STARTER_SCANS}`), undefined, { timeout: 2000 })).toBeInTheDocument();
      expect(screen.queryByText(/updating your scans/i)).not.toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('ends the waiting state even when every check hangs', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      const user = renderApp(billing);
      await openAccount(user);
      await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
      billing.client.getStatus.mockImplementation(() => new Promise(() => {}));
      act(() => billing.completePayment());
      await screen.findByText(/updating your scans/i);

      expect(await screen.findByRole('alert', undefined, { timeout: 4000 })).toHaveTextContent(/could not refresh your scan balance/i);
      expect(screen.queryByText(/updating your scans/i)).not.toBeInTheDocument();
      expect(screen.getByText('Pro plan')).toBeInTheDocument();
    });

    it('still ends the window when the interval is zero', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      const user = renderApp(billing, makeSignedInAuth(), { intervalMs: 0, windowMs: 50, checkTimeoutMs: 50 });
      await openAccount(user);
      await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
      act(() => billing.completePayment());

      expect(await screen.findByText(/may take a minute to appear/i, undefined, { timeout: 2000 })).toBeInTheDocument();
      // one load, then the first check and at most one recheck per millisecond of the window
      expect(billing.client.getStatus.mock.calls.length).toBeLessThanOrEqual(1 + 1 + 50);
    });

    it('stops rechecking when the user signs out', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      const auth = makeDrivableAuth();
      await buyWithLateGrant(billing, auth.client);

      auth.emit(null);
      await act(async () => wait(RECHECK.intervalMs));
      const calls = billing.client.getStatus.mock.calls.length;
      await act(async () => wait(RECHECK.windowMs * 2));

      expect(billing.client.getStatus).toHaveBeenCalledTimes(calls);
      expect(screen.queryByText(/updating your scans/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/may take a minute/i)).not.toBeInTheDocument();
    });

    it('stops rechecking for the buyer when another account signs in, and does not touch that account', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      const auth = makeDrivableAuth();
      await buyWithLateGrant(billing, auth.client);

      auth.emit(SAM);
      expect(await screen.findByText('Signed in as sam@example.com')).toBeInTheDocument();
      expect(await screen.findByText('Free plan')).toBeInTheDocument();
      const calls = billing.client.getStatus.mock.calls.length;
      await act(async () => wait(RECHECK.windowMs * 2));

      expect(billing.client.getStatus).toHaveBeenCalledTimes(calls);
      expect(screen.getByText('Free plan')).toBeInTheDocument();
      expect(screen.getByText(/Scan Credit balance: 0/)).toBeInTheDocument();
      expect(screen.queryByText(/updating your scans/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/may take a minute/i)).not.toBeInTheDocument();
    });

    it('stops rechecking when the app goes away', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      const user = await buyWithLateGrant(billing);

      user.unmount();
      await wait(RECHECK.intervalMs);
      const calls = billing.client.getStatus.mock.calls.length;
      await wait(RECHECK.windowMs * 2);

      expect(billing.client.getStatus).toHaveBeenCalledTimes(calls);
    });
  });

  describe('a plan load racing the purchase', () => {
    // Renders only the billing state, so a test can reach calls the Account screen never offers
    // at that moment (the Buy Pro button is disabled while a plan loads).
    function renderProbe(billing: ReturnType<typeof makeFakeBilling>) {
      const probe: { current: BillingState | null } = { current: null };
      function Probe() {
        probe.current = useBilling();
        return (
          <div>
            {probe.current.isPro ? 'probe: pro' : 'probe: free'} / {probe.current.loading ? 'probe: loading' : 'probe: idle'}
          </div>
        );
      }
      render(
        <AuthProvider client={makeSignedInAuth()}>
          <BillingProvider client={billing.client} scanRecheck={RECHECK}>
            <Probe />
          </BillingProvider>
        </AuthProvider>,
      );
      return probe;
    }

    it('does not let a plan load that began before the purchase turn the buyer back to Free', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      let settleStale: (status: { isPro: boolean; scanBalance: number }) => void = () => {};
      billing.client.getStatus.mockReturnValueOnce(new Promise((resolve) => (settleStale = resolve)));
      const probe = renderProbe(billing);
      await screen.findByText(/probe: loading/);

      act(() => void probe.current?.buyPro());
      act(() => billing.completePayment());
      expect(await screen.findByText(/probe: pro/)).toBeInTheDocument();
      await act(async () => settleStale({ isPro: false, scanBalance: 0 }));

      expect(screen.getByText(/probe: pro/)).toBeInTheDocument();
      expect(screen.queryByText(/probe: loading/)).not.toBeInTheDocument();
    });

    it('ignores a reload while the starter scans are awaited', async () => {
      const billing = makeFakeBilling({ lateGrant: true });
      const probe = renderProbe(billing);
      await screen.findByText(/probe: idle/);
      act(() => void probe.current?.buyPro());
      act(() => billing.completePayment());
      await waitFor(() => expect(probe.current?.scansUpdating).toBe(true));
      const identifies = billing.client.identify.mock.calls.length;

      act(() => probe.current?.reload());

      expect(billing.client.identify).toHaveBeenCalledTimes(identifies);
    });
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

    it('recovers from a failed identify call the same way', async () => {
      const billing = makeFakeBilling();
      billing.client.identify.mockRejectedValueOnce(new Error('Could not identify.'));
      const user = renderApp(billing);
      await openAccount(user);

      expect(await screen.findByRole('alert')).toHaveTextContent('Could not identify.');
      await user.click(screen.getByRole('button', { name: 'Try again' }));
      expect(await screen.findByText('Free plan')).toBeInTheDocument();
      expect(billing.client.identify).toHaveBeenLastCalledWith('acct-pat');
    });

    it('recovers from a failed offer call the same way', async () => {
      const billing = makeFakeBilling();
      billing.client.getProOffer.mockRejectedValueOnce(new Error('Could not load the offer.'));
      const user = renderApp(billing);
      await openAccount(user);

      expect(await screen.findByRole('alert')).toHaveTextContent('Could not load the offer.');
      await user.click(screen.getByRole('button', { name: 'Try again' }));
      expect(await screen.findByText('Free plan')).toBeInTheDocument();
      expect(screen.getByText(/\$9\.99/)).toBeInTheDocument();
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
