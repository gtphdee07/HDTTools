// THROWAWAY PROTOTYPE — not part of the production app.
//
// Answers wayfinder ticket #5 (github.com/gtphdee07/HDTTools/issues/5):
// how does a real RevenueCat Web Billing checkout actually behave and feel,
// and are upstream purchases-js bugs #1095 (inline checkout can't be
// cancelled, orphans the Embedded Checkout instance) and #973 (modal
// checkout drops onClose, no visible cancel affordance) still live?
//
// Run: npm run dev:prototype-checkout (see web/package.json), then
// manually click through the cancel/dismiss checklist below.
//
// Findings belong on ticket #5, not in this file. When this ticket
// resolves, this whole src/prototype/ folder is captured on a
// prototype/revenuecat-web-checkout branch, then deleted from main.

import { useEffect, useRef, useState } from 'react';
import {
  ErrorCode,
  LogLevel,
  Purchases,
  PurchasesError,
} from '@revenuecat/purchases-js';
import type { Offering, Package as RCPackage, PurchaseResult } from '@revenuecat/purchases-js';

const APP_USER_ID_KEY = 'rigcheck:prototype:appUserId';

type Placement = 'inline' | 'modal';
type PurchaseState = 'idle' | 'in-progress' | 'success' | 'cancelled' | 'error';

interface LogEntry {
  time: string;
  label: string;
  detail?: string;
}

function timestamp(): string {
  return new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function PrototypeCheckout() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [configError, setConfigError] = useState<string | null>(null);
  const [purchases, setPurchases] = useState<Purchases | null>(null);
  const [appUserId, setAppUserId] = useState<string>('');
  const [offering, setOffering] = useState<Offering | null>(null);
  const [webPackages, setWebPackages] = useState<RCPackage[]>([]);
  const [excludedCount, setExcludedCount] = useState(0);
  const [balance, setBalance] = useState<number | null>(null);
  const [placement, setPlacement] = useState<Placement>('inline');
  const [purchaseState, setPurchaseState] = useState<PurchaseState>('idle');
  const [lastResult, setLastResult] = useState<string | null>(null);
  const inlineMountRef = useRef<HTMLDivElement | null>(null);

  const log = (label: string, detail?: string) => {
    setLogs((prev) => [...prev, { time: timestamp(), label, detail }]);
  };

  useEffect(() => {
    const apiKey = import.meta.env.VITE_REVENUECAT_WEB_PUBLIC_API_KEY as string | undefined;
    const offeringId = import.meta.env.VITE_REVENUECAT_WEB_OFFERING_ID as string | undefined;

    if (!apiKey || !offeringId) {
      setConfigError(
        'Missing VITE_REVENUECAT_WEB_PUBLIC_API_KEY or VITE_REVENUECAT_WEB_OFFERING_ID in web/.env.local — ' +
          're-run the wizard (scripts/revenuecat-web-billing-setup.sh) before using this prototype.',
      );
      return;
    }

    let storedId = sessionStorage.getItem(APP_USER_ID_KEY);
    if (!storedId) {
      storedId = Purchases.generateRevenueCatAnonymousAppUserId();
      sessionStorage.setItem(APP_USER_ID_KEY, storedId);
    }
    setAppUserId(storedId);

    Purchases.setLogLevel(LogLevel.Debug);
    let instance: Purchases;
    try {
      instance = Purchases.configure({ apiKey, appUserId: storedId });
    } catch (err) {
      setConfigError(err instanceof Error ? err.message : 'Purchases.configure() failed.');
      return;
    }
    setPurchases(instance);
    log('configured', `appUserId=${storedId}`);

    void instance
      .getOfferings()
      .then((offerings) => {
        const picked = offerings.all[offeringId] ?? offerings.current;
        if (!picked) {
          log('offerings fetched', `no offering found for id "${offeringId}" and no current offering either`);
          return;
        }
        const purchasable = picked.availablePackages.filter((pkg) => Boolean(pkg.webBillingProduct));
        setOffering(picked);
        setWebPackages(purchasable);
        setExcludedCount(picked.availablePackages.length - purchasable.length);
        log(
          'offerings fetched',
          `offering="${picked.identifier}", ${purchasable.length} web-purchasable package(s), ` +
            `${picked.availablePackages.length - purchasable.length} excluded (not backed by Web Billing)`,
        );
      })
      .catch((err) => {
        log('offerings fetch failed', err instanceof Error ? err.message : String(err));
      });

    void instance
      .getVirtualCurrencies()
      .then((vcs) => {
        const scan = vcs.all['SCAN'];
        setBalance(scan?.balance ?? 0);
        log('virtual currencies fetched', `SCAN balance=${scan?.balance ?? 0}`);
      })
      .catch((err) => {
        log('virtual currencies fetch failed', err instanceof Error ? err.message : String(err));
      });
    // Runs once on mount: configuring more than one Purchases instance is
    // explicitly unsupported by the SDK.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refreshBalance = async (instance: Purchases) => {
    try {
      instance.invalidateVirtualCurrenciesCache();
      const vcs = await instance.getVirtualCurrencies();
      const scan = vcs.all['SCAN'];
      setBalance(scan?.balance ?? 0);
      log('balance refreshed', `SCAN balance=${scan?.balance ?? 0}`);
    } catch (err) {
      log('balance refresh failed', err instanceof Error ? err.message : String(err));
    }
  };

  const startPurchase = async (pkg: RCPackage) => {
    if (!purchases) return;
    setPurchaseState('in-progress');
    setLastResult(null);
    log('purchase started', `package="${pkg.identifier}" placement=${placement}`);

    try {
      const result: PurchaseResult = await purchases.purchase({
        rcPackage: pkg,
        htmlTarget: placement === 'inline' ? (inlineMountRef.current ?? undefined) : undefined,
      });
      setPurchaseState('success');
      setLastResult(`operationSessionId=${result.operationSessionId}`);
      log('purchase succeeded', `operationSessionId=${result.operationSessionId}`);
      await refreshBalance(purchases);
    } catch (err) {
      if (err instanceof PurchasesError && err.errorCode === ErrorCode.UserCancelledError) {
        setPurchaseState('cancelled');
        setLastResult('ErrorCode.UserCancelledError');
        log('purchase cancelled', 'SDK reported ErrorCode.UserCancelledError (the documented path)');
      } else if (err instanceof PurchasesError) {
        setPurchaseState('error');
        setLastResult(`${err.errorCode}: ${err.message}`);
        log('purchase errored', `errorCode=${err.errorCode} message=${err.message}`);
      } else {
        setPurchaseState('error');
        setLastResult(err instanceof Error ? err.message : String(err));
        log('purchase errored (non-PurchasesError)', err instanceof Error ? err.message : String(err));
      }
    }
  };

  const resetIdentity = () => {
    sessionStorage.removeItem(APP_USER_ID_KEY);
    window.location.reload();
  };

  if (configError) {
    return (
      <div style={{ fontFamily: 'monospace', padding: 24, maxWidth: 720 }}>
        <h1>⚠ Prototype not configured</h1>
        <p>{configError}</p>
      </div>
    );
  }

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: 24, maxWidth: 820, margin: '0 auto' }}>
      <div style={{ background: '#fff3cd', border: '1px solid #ffc107', padding: '8px 12px', marginBottom: 20, fontSize: 13 }}>
        PROTOTYPE — throwaway code for wayfinder ticket{' '}
        <a href="https://github.com/gtphdee07/HDTTools/issues/5" target="_blank" rel="noreferrer">#5</a>. Not part of the production app.
      </div>

      <h1 style={{ fontSize: 20 }}>RevenueCat Web Billing checkout prototype</h1>
      <p style={{ color: '#555', fontSize: 14 }}>
        appUserId: <code>{appUserId || '…generating…'}</code> ·{' '}
        <button onClick={resetIdentity} style={{ fontSize: 12 }}>reset as new test customer</button>
      </p>
      <p style={{ fontSize: 14 }}>SCAN balance: <strong>{balance ?? '…loading…'}</strong></p>

      <h2 style={{ fontSize: 16, marginTop: 28 }}>1. Checkout placement</h2>
      <p style={{ fontSize: 13, color: '#555' }}>
        Switch this, then purchase, to compare inline vs. modal — this is the fork the two known bugs sit on.
      </p>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button
          onClick={() => setPlacement('inline')}
          style={{ fontWeight: placement === 'inline' ? 700 : 400, padding: '6px 12px' }}
        >
          Inline (htmlTarget) — watch for #1095
        </button>
        <button
          onClick={() => setPlacement('modal')}
          style={{ fontWeight: placement === 'modal' ? 700 : 400, padding: '6px 12px' }}
        >
          Modal (no htmlTarget) — watch for #973
        </button>
      </div>

      {placement === 'inline' && (
        <div
          ref={inlineMountRef}
          id="prototype-inline-mount"
          style={{ position: 'relative', border: '2px dashed #999', minHeight: 900, overflow: 'visible', padding: 12, marginBottom: 16, background: '#fafafa' }}
        >
          <span style={{ color: '#999', fontSize: 13 }}>Checkout mounts here. After a cancel, check whether this area looks stuck/broken on the next purchase attempt (that's #1095).</span>
        </div>
      )}

      <h2 style={{ fontSize: 16, marginTop: 28 }}>2. Packages</h2>
      {excludedCount > 0 && (
        <p style={{ fontSize: 13, color: '#a15c00' }}>
          {excludedCount} package(s) in the "{offering?.identifier}" offering hidden — not backed by Web Billing (Android's Test Store packages).
        </p>
      )}
      {webPackages.length === 0 && <p style={{ fontSize: 13 }}>Loading offering, or no web-purchasable package found…</p>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {webPackages.map((pkg) => (
          <div key={pkg.identifier} style={{ border: '1px solid #ddd', borderRadius: 6, padding: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 600 }}>{pkg.webBillingProduct.title}</div>
              <div style={{ fontSize: 12, color: '#666' }}>
                {pkg.identifier} · {pkg.webBillingProduct.currentPrice.formattedPrice}
              </div>
            </div>
            <button
              onClick={() => void startPurchase(pkg)}
              disabled={purchaseState === 'in-progress'}
              style={{ padding: '8px 16px', fontWeight: 600 }}
            >
              {purchaseState === 'in-progress' ? 'In progress…' : 'Purchase'}
            </button>
          </div>
        ))}
      </div>

      <h2 style={{ fontSize: 16, marginTop: 28 }}>3. Cancel/dismiss checklist</h2>
      <p style={{ fontSize: 13, color: '#555' }}>
        Click Purchase above, then try each of these without completing payment, and watch the state below and the browser console (log level is Debug):
      </p>
      <ul style={{ fontSize: 13, color: '#555' }}>
        <li>Click the checkout's own close/X button, if one is visible.</li>
        <li>Click outside the checkout (modal backdrop, or elsewhere on the page for inline).</li>
        <li>Press Escape.</li>
        <li>After any of the above, click Purchase again <em>without reloading the page</em> — this is the actual #1095 repro (does the second attempt work, or is the instance orphaned?).</li>
      </ul>

      <h2 style={{ fontSize: 16, marginTop: 28 }}>4. State</h2>
      <p style={{ fontSize: 14 }}>
        purchaseState: <strong style={{
          color: purchaseState === 'success' ? '#1a7a1a' : purchaseState === 'error' ? '#b00020' : purchaseState === 'cancelled' ? '#a15c00' : '#333',
        }}>{purchaseState}</strong>
        {lastResult && <> — {lastResult}</>}
      </p>

      <h2 style={{ fontSize: 16, marginTop: 28 }}>Event log</h2>
      <div style={{ fontFamily: 'monospace', fontSize: 12, background: '#111', color: '#0f0', padding: 12, borderRadius: 6, maxHeight: 280, overflowY: 'auto' }}>
        {logs.length === 0 && <div>…</div>}
        {logs.map((entry, i) => (
          <div key={i}>
            [{entry.time}] {entry.label}
            {entry.detail && <> — {entry.detail}</>}
          </div>
        ))}
      </div>
    </div>
  );
}
