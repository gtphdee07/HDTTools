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

// A consumable pack that adds Scan Credits. It adds scans only, never Garage or History caps.
export interface ScanPack {
  id: string;
  title: string;
  // already formatted for display, for example "$2.99"
  price: string;
}

export type PurchaseOutcome = 'purchased' | 'cancelled';

// How long, and how often, the Scan Credit balance is rechecked after a purchase while
// RevenueCat's server-side grant of the starter bundle has not shown up yet.
export interface ScanRecheck {
  intervalMs: number;
  // The first check is immediate; rechecks continue until this much time has passed.
  windowMs: number;
  // A check that has not answered by then counts as failed, so a hung call cannot hold the window open.
  checkTimeoutMs: number;
}

// A tuning value: the real grant delay is best observed in the sandbox purchase (#11).
const DEFAULT_SCAN_RECHECK: ScanRecheck = { intervalMs: 2000, windowMs: 30000, checkTimeoutMs: 8000 };

// The slice of RevenueCat this app uses - kept narrow so tests can fake it.
// A user cancelling checkout is a 'cancelled' outcome; any other failure rejects.
export interface BillingClient {
  // Makes the signed-in account the RevenueCat customer, so purchases and the
  // SCAN balance are the account's, shared with every other device.
  identify(accountId: string): Promise<void>;
  getProOffer(): Promise<ProOffer | null>;
  getStatus(): Promise<BillingStatus>;
  // The scan packs on sale to this customer; empty when none can be bought on the web.
  getScanPacks(): Promise<ScanPack[]>;
  // Opens the modal checkout and settles when it closes.
  purchasePro(): Promise<PurchaseOutcome>;
  // Same, for one of the packs getScanPacks listed.
  purchaseScanPack(packId: string): Promise<PurchaseOutcome>;
}

export interface BillingState {
  // False when this build has no purchases set up (the free calculator still works).
  available: boolean;
  loading: boolean;
  isPro: boolean;
  // Scan Credit balance; null until first loaded.
  scanBalance: number | null;
  // True while the balance is being rechecked after a purchase, waiting for the starter scans.
  scansUpdating: boolean;
  proOffer: ProOffer | null;
  scanPacks: ScanPack[];
  checkoutOpen: boolean;
  error: string | null;
  // True when loading the plan, balance and offer failed (not when a purchase failed).
  loadFailed: boolean;
  notice: string | null;
  buyPro(): Promise<void>;
  buyScanPack(packId: string): Promise<void>;
  // Loads the plan, balance and offer again. Never starts a checkout.
  reload(): void;
  // Reads the Scan Credit balance again, for after a scan spent or refunded one. A failed read leaves the
  // balance as it was.
  refreshScanBalance(): Promise<void>;
  // Dismisses an open checkout; the same path as the browser Back button.
  closeCheckout(): void;
}

const UNAVAILABLE: BillingState = {
  available: false,
  loading: false,
  isPro: false,
  scanBalance: null,
  scansUpdating: false,
  proOffer: null,
  scanPacks: [],
  checkoutOpen: false,
  error: null,
  loadFailed: false,
  notice: null,
  buyPro: async () => {},
  buyScanPack: async () => {},
  reload: () => {},
  refreshScanBalance: async () => {},
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

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Timed out.')), ms);
    promise.then(resolve, reject).finally(() => clearTimeout(timer));
  });
}

export function BillingProvider({
  client,
  scanRecheck = DEFAULT_SCAN_RECHECK,
  children,
}: {
  client: BillingClient | null;
  scanRecheck?: ScanRecheck;
  children: ReactNode;
}) {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  // At least 1ms apart, so the number of rechecks in the window is always finite.
  const intervalMs = Math.max(1, scanRecheck.intervalMs);
  const { windowMs, checkTimeoutMs } = scanRecheck;

  const [loading, setLoading] = useState(false);
  const [isPro, setIsPro] = useState(false);
  const [scanBalance, setScanBalanceState] = useState<number | null>(null);
  const [scansUpdating, setScansUpdating] = useState(false);
  // The balance on screen, readable from a purchase that settles later.
  const scanBalanceRef = useRef<number | null>(null);
  const setScanBalance = useCallback((balance: number | null) => {
    scanBalanceRef.current = balance;
    setScanBalanceState(balance);
  }, []);
  // Counts post-purchase rechecks; bumping it cancels the one running.
  const recheckRunRef = useRef(0);
  const [proOffer, setProOffer] = useState<ProOffer | null>(null);
  const [scanPacks, setScanPacks] = useState<ScanPack[]>([]);
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
        const [offer, packs, status] = await Promise.all([client.getProOffer(), client.getScanPacks(), client.getStatus()]);
        if (!current()) return;
        setProOffer(offer);
        setScanPacks(packs);
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
    [client, setScanBalance],
  );

  const dropPendingLoads = useCallback(() => {
    loadRunRef.current++;
    recheckRunRef.current++;
  }, []);

  // Each signed-in account gets its own plan, balance and offer; signing out clears them.
  useEffect(() => {
    accountRef.current = userId;
    setIsPro(false);
    setScanBalance(null);
    setScansUpdating(false);
    setProOffer(null);
    setScanPacks([]);
    setError(null);
    setLoadFailed(false);
    setNotice(null);
    if (!client || !userId) {
      setLoading(false);
      return;
    }
    void loadPlan(userId);
    return dropPendingLoads;
  }, [client, userId, loadPlan, dropPendingLoads, setScanBalance]);

  const reload = useCallback(() => {
    const accountId = accountRef.current;
    // While the starter scans are awaited, a plan load could report RevenueCat's lagging Free status.
    if (!accountId || checkoutOpenRef.current || scansUpdating) return;
    void loadPlan(accountId);
  }, [loadPlan, scansUpdating]);

  const refreshScanBalance = useCallback(async () => {
    const accountId = accountRef.current;
    if (!client || !accountId) return;
    try {
      const status = await client.getStatus();
      if (accountRef.current === accountId) setScanBalance(status.scanBalance);
    } catch {
      // The balance on screen stays; the next scan is checked by the Scan service either way.
    }
  }, [client, setScanBalance]);

  // One checkout at a time, for Pro or a scan pack. The purchase only ever changes what the
  // purchase is for: Pro flips the plan, a pack only moves the Scan Credit balance.
  const checkout = useCallback(async (purchase: () => Promise<PurchaseOutcome>, item: 'pro' | 'pack') => {
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
      outcome = await purchase();
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
    if (item === 'pro') {
      setIsPro(true);
      setNotice('Thank you! Pro is unlocked.');
    } else {
      setNotice('Thank you! Your scans are on the way.');
    }
    // A plan load still in flight from before the purchase would report the old, Free state.
    dropPendingLoads();
    setLoading(false);

    // RevenueCat grants the starter scans server-side, so the balance can lag the
    // purchase: recheck it for a bounded window until it differs from before.
    const before = scanBalanceRef.current ?? 0;
    const run = ++recheckRunRef.current;
    const current = () => recheckRunRef.current === run && stillBuyer();
    const rechecks = Math.floor(windowMs / intervalMs);
    // Only a window in which no check got an answer is an error; a stray failure among
    // answers that all said "not yet" is still just a late grant.
    let anyCheckSucceeded = false;
    setScansUpdating(true);
    try {
      for (let attempt = 0; ; attempt++) {
        if (attempt > 0) {
          await sleep(intervalMs);
          if (!current()) return;
        }
        try {
          const status = await withTimeout(client.getStatus(), checkTimeoutMs);
          if (!current()) return;
          anyCheckSucceeded = true;
          setScanBalance(status.scanBalance);
          if (status.scanBalance !== before) return;
        } catch {
          if (!current()) return;
        }
        if (attempt >= rechecks) break;
      }
      if (!anyCheckSucceeded) setError('Your purchase went through, but we could not refresh your scan balance. Reload to see it.');
      else setNotice(`${item === 'pro' ? 'Pro is unlocked.' : 'Your purchase went through.'} Your scans may take a minute to appear.`);
    } finally {
      if (current()) setScansUpdating(false);
    }
  }, [client, intervalMs, windowMs, checkTimeoutMs, setScanBalance, dropPendingLoads]);

  const buyPro = useCallback(async () => {
    if (client) await checkout(() => client.purchasePro(), 'pro');
  }, [client, checkout]);

  const buyScanPack = useCallback(
    async (packId: string) => {
      if (client) await checkout(() => client.purchaseScanPack(packId), 'pack');
    },
    [client, checkout],
  );

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
        ? {
            available: true,
            loading,
            isPro,
            scanBalance,
            scansUpdating,
            proOffer,
            scanPacks,
            checkoutOpen,
            error,
            loadFailed,
            notice,
            buyPro,
            buyScanPack,
            reload,
            refreshScanBalance,
            closeCheckout,
          }
        : UNAVAILABLE,
    [client, loading, isPro, scanBalance, scansUpdating, proOffer, scanPacks, checkoutOpen, error, loadFailed, notice, buyPro, buyScanPack, reload, refreshScanBalance, closeCheckout],
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
