import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useAuth } from './auth';
import { Button } from './design-system/Button';
import { createRevenueCatBillingClient, readBillingConfig } from './revenueCatBilling';

export interface ProOffer {
  // already formatted for display, for example "$9.99"
  price: string;
}

export interface BillingStatus {
  isPro: boolean;
  scanBalance: number;
}

export type PurchaseOutcome = 'purchased' | 'cancelled';

// The slice of RevenueCat this app uses - kept narrow so tests can fake it.
// A user cancelling checkout is a 'cancelled' outcome; any other failure rejects.
export interface BillingClient {
  // Makes the signed-in account the RevenueCat customer, so purchases and the
  // SCAN balance are the account's, shared with every other device.
  identify(accountId: string): Promise<void>;
  getProOffer(): Promise<ProOffer | null>;
  getStatus(): Promise<BillingStatus>;
  // Opens the modal checkout and settles when it closes.
  purchasePro(): Promise<PurchaseOutcome>;
}

export interface BillingState {
  // False when this build has no purchases set up (the free calculator still works).
  available: boolean;
  loading: boolean;
  isPro: boolean;
  // Scan Credit balance; null until first loaded.
  scanBalance: number | null;
  proOffer: ProOffer | null;
  checkoutOpen: boolean;
  error: string | null;
  // True when loading the plan, balance and offer failed (not when a purchase failed).
  loadFailed: boolean;
  notice: string | null;
  buyPro(): Promise<void>;
  // Loads the plan, balance and offer again. Never starts a checkout.
  reload(): void;
  // Dismisses an open checkout; the same path as the browser Back button.
  closeCheckout(): void;
}

const UNAVAILABLE: BillingState = {
  available: false,
  loading: false,
  isPro: false,
  scanBalance: null,
  proOffer: null,
  checkoutOpen: false,
  error: null,
  loadFailed: false,
  notice: null,
  buyPro: async () => {},
  reload: () => {},
  closeCheckout: () => {},
};

const BillingContext = createContext<BillingState>(UNAVAILABLE);

export function useBilling(): BillingState {
  return useContext(BillingContext);
}

export function createRevenueCatClientFromEnv(): BillingClient | null {
  const config = readBillingConfig(import.meta.env);
  return config ? createRevenueCatBillingClient(config) : null;
}

const message = (err: unknown, fallback: string) => (err instanceof Error && err.message ? err.message : fallback);

export function BillingProvider({ client, children }: { client: BillingClient | null; children: ReactNode }) {
  const { user } = useAuth();
  const userId = user?.id ?? null;

  const [loading, setLoading] = useState(false);
  const [isPro, setIsPro] = useState(false);
  const [scanBalance, setScanBalance] = useState<number | null>(null);
  const [proOffer, setProOffer] = useState<ProOffer | null>(null);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const checkoutOpenRef = useRef(false);
  // Counts plan loads; only the newest may write its result, so a slow load that was
  // retried over, or belongs to an account that has since left, is dropped.
  const loadRunRef = useRef(0);
  // The account signed in right now, readable from a checkout that settles later.
  const accountRef = useRef<string | null>(null);
  // Where the history stood when the open checkout began, to tell whether the
  // modal has pushed its own entry yet.
  const checkoutHistoryRef = useRef<{ length: number; state: unknown } | null>(null);

  const loadPlan = useCallback(
    async (accountId: string) => {
      if (!client) return;
      const run = ++loadRunRef.current;
      const current = () => loadRunRef.current === run;
      setLoading(true);
      setError(null);
      setLoadFailed(false);
      try {
        await client.identify(accountId);
        const [offer, status] = await Promise.all([client.getProOffer(), client.getStatus()]);
        if (!current()) return;
        setProOffer(offer);
        setIsPro(status.isPro);
        setScanBalance(status.scanBalance);
      } catch (err) {
        if (!current()) return;
        setError(message(err, 'Could not load your purchase details. Try again later.'));
        setLoadFailed(true);
      } finally {
        if (current()) setLoading(false);
      }
    },
    [client],
  );

  const dropPendingLoads = useCallback(() => {
    loadRunRef.current++;
  }, []);

  // Each signed-in account gets its own plan, balance and offer; signing out clears them.
  useEffect(() => {
    accountRef.current = userId;
    setIsPro(false);
    setScanBalance(null);
    setProOffer(null);
    setError(null);
    setLoadFailed(false);
    setNotice(null);
    if (!client || !userId) {
      setLoading(false);
      return;
    }
    void loadPlan(userId);
    return dropPendingLoads;
  }, [client, userId, loadPlan, dropPendingLoads]);

  const reload = useCallback(() => {
    const accountId = accountRef.current;
    if (!accountId || checkoutOpenRef.current) return;
    void loadPlan(accountId);
  }, [loadPlan]);

  const buyPro = useCallback(async () => {
    if (!client || checkoutOpenRef.current) return;
    checkoutOpenRef.current = true;
    checkoutHistoryRef.current = { length: window.history.length, state: window.history.state };
    setCheckoutOpen(true);
    setError(null);
    setNotice(null);

    // The outcome belongs to the account that started the checkout; if someone
    // else is signed in (or nobody) by the time it settles, it must not touch them.
    const buyer = accountRef.current;
    const stillBuyer = () => accountRef.current === buyer;

    let outcome: PurchaseOutcome;
    try {
      outcome = await client.purchasePro();
    } catch (err) {
      if (stillBuyer()) setError(message(err, 'The purchase could not be completed. You were not charged.'));
      return;
    } finally {
      checkoutOpenRef.current = false;
      checkoutHistoryRef.current = null;
      setCheckoutOpen(false);
    }

    if (!stillBuyer()) return;
    if (outcome === 'cancelled') {
      setNotice('Checkout closed. You were not charged.');
      return;
    }
    // The completed purchase is what makes the user Pro; RevenueCat's entitlement
    // can lag behind it, so the refresh below must not flip them back to Free.
    setIsPro(true);
    setNotice('Thank you! Pro is unlocked.');
    try {
      const status = await client.getStatus();
      if (stillBuyer()) setScanBalance(status.scanBalance);
    } catch {
      if (stillBuyer()) setError('Your purchase went through, but we could not refresh your scan balance. Reload to see it.');
    }
  }, [client]);

  // The RevenueCat modal has no close control of its own (purchases-js #973),
  // and cancels only on browser Back, so ours goes Back too - but only once the
  // modal has pushed its history entry; before that, Back would leave the page.
  const closeCheckout = useCallback(() => {
    const start = checkoutHistoryRef.current;
    if (!start) return;
    if (window.history.length > start.length || window.history.state !== start.state) window.history.back();
  }, []);

  const value = useMemo<BillingState>(
    () =>
      client
        ? { available: true, loading, isPro, scanBalance, proOffer, checkoutOpen, error, loadFailed, notice, buyPro, reload, closeCheckout }
        : UNAVAILABLE,
    [client, loading, isPro, scanBalance, proOffer, checkoutOpen, error, loadFailed, notice, buyPro, reload, closeCheckout],
  );

  return (
    <BillingContext.Provider value={value}>
      {children}
      {checkoutOpen && <CloseCheckoutButton onClose={closeCheckout} />}
    </BillingContext.Provider>
  );
}

// Sits above the RevenueCat modal overlay so the buyer always has a visible way out.
function CloseCheckoutButton({ onClose }: { onClose: () => void }) {
  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={onClose}
      style={{ position: 'fixed', top: 16, right: 16, zIndex: 2147483647, boxShadow: 'var(--shadow-lg)' }}
    >
      Close checkout
    </Button>
  );
}
