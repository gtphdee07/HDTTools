import { useBilling } from '../billing';
import { Button } from '../design-system/Button';
import { Card } from '../design-system/Card';
import { NOT_CERTIFIED_STATEMENT } from '../notCertified';

// Where a Pro user tops up their Scan Credit balance (a Free user buys Pro first, so this renders nothing
// for them). A pack adds scans only: it never changes the plan, so the Garage and History limits stay as they were.
export function ScanPacks() {
  const billing = useBilling();
  const { scanPacks, loading, checkoutOpen, scansUpdating, isPro } = billing;
  if (!isPro || scanPacks.length === 0) return null;

  const busy = loading || checkoutOpen || scansUpdating;
  return (
    <Card title="Buy more scans" subtitle="Scan packs add scans only. They do not change your plan or your Garage and History limits.">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
        {scanPacks.map((pack) => (
          <div key={pack.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <div style={{ fontSize: 14 }}>
              <strong>{pack.title}</strong> &middot; {pack.price}
            </div>
            <Button variant="secondary" size="sm" disabled={busy} aria-label={`Buy ${pack.title}`} onClick={() => void billing.buyScanPack(pack.id)}>
              Buy
            </Button>
          </div>
        ))}
      </div>
      {/* A Pro user never sees the Pro paywall, where this statement otherwise lives. */}
      <div style={{ fontSize: 13, color: 'var(--fg-2)', marginTop: 10 }}>{NOT_CERTIFIED_STATEMENT}</div>
    </Card>
  );
}
