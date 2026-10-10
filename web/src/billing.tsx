import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useAuth } from './auth';
import { createRevenueCatBillingClient, readBillingConfig } from './revenueCatBilling';

export interface ProOffer {
  title: string;
  // already formatted for display, for example "$9.99"
  price: string;
}

export type PurchaseOutcome = 'purchased' | 'cancelled';

// The slice of RevenueCat this app uses - kept narrow so tests can fake it.
// A user cancelling checkout is a 'cancelled' outcome; any other failure rejects.
export interface BillingClient {
  // Makes the signed-in account the RevenueCat customer, so purchases and the
  // SCAN balance are the account's, shared with every other device.
  identify(accountId: string): Promise<void>;
  getProOffer(): Promise<ProOffer | null>;
  getStatus(): Promise<{ isPro: boolean; scanBalance: number }>;
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
  notice: string | null;
  buyPro(): Promise<void>;
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
  notice: null,
  buyPro: async () => {},
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
  const [notice, setNotice] = useState<string | null>(null);
  const checkoutOpenRef = useRef(false);

  // Each signed-in account gets its own plan, balance and offer; signing out clears them.
  useEffect(() => {
    setIsPro(false);
    setScanBalance(null);
    setProOffer(null);
    setError(null);
    setNotice(null);
    if (!client || !userId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        await client.identify(userId);
        const [offer, status] = await Promise.all([client.getProOffer(), client.getStatus()]);
        if (cancelled) return;
        setProOffer(offer);
        setIsPro(status.isPro);
        setScanBalance(status.scanBalance);
      } catch (err) {
        if (!cancelled) setError(message(err, 'Could not load your purchase details. Try again later.'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [client, userId]);

  const buyPro = useCallback(async () => {
    if (!client || checkoutOpenRef.current) return;
    checkoutOpenRef.current = true;
    setCheckoutOpen(true);
    setError(null);
    setNotice(null);

    let outcome: PurchaseOutcome;
    try {
      outcome = await client.purchasePro();
    } catch (err) {
      setError(message(err, 'The purchase could not be completed. You were not charged.'));
      return;
    } finally {
      checkoutOpenRef.current = false;
      setCheckoutOpen(false);
    }

    if (outcome === 'cancelled') {
      setNotice('Checkout closed. You were not charged.');
      return;
    }
    setIsPro(true);
    setNotice('Thank you! Pro is unlocked.');
    try {
      const status = await client.getStatus();
      setIsPro(status.isPro);
      setScanBalance(status.scanBalance);
    } catch {
      setError('Your purchase went through, but we could not refresh your scan balance. Reload to see it.');
    }
  }, [client]);

  // The RevenueCat modal has no close control of its own (purchases-js #973),
  // and cancels only on browser Back, so ours goes Back too.
  const closeCheckout = useCallback(() => window.history.back(), []);

  const value = useMemo<BillingState>(
    () =>
      client
        ? { available: true, loading, isPro, scanBalance, proOffer, checkoutOpen, error, notice, buyPro, closeCheckout }
        : UNAVAILABLE,
    [client, loading, isPro, scanBalance, proOffer, checkoutOpen, error, notice, buyPro, closeCheckout],
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
    <button
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 16,
        right: 16,
        zIndex: 2147483647,
        padding: '10px 18px',
        borderRadius: 'var(--radius-pill)',
        border: '1.5px solid var(--accent-secondary)',
        background: 'var(--bg-surface)',
        color: 'var(--accent-secondary-hover)',
        fontFamily: 'var(--font-display)',
        fontWeight: 700,
        fontSize: 14,
        cursor: 'pointer',
        boxShadow: 'var(--shadow-lg)',
      }}
    >
      Close checkout
    </button>
  );
}
