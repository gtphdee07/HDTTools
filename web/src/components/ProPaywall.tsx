import { useBilling } from '../billing';
import { Button } from '../design-system/Button';
import { Card } from '../design-system/Card';

// What a signed-in Free user sees on their account: what Pro is, its price, the
// not-certified statement (the Disclaimer gate before results is separate and unchanged), and Buy.
export function ProPaywall() {
  const billing = useBilling();
  const { proOffer, loading, checkoutOpen } = billing;

  return (
    <Card
      title="RigCheck Pro"
      subtitle="A one-time purchase, yours for good: larger Garage and History, plus a starter bundle of scans."
    >
      {proOffer ? (
        <div style={{ fontSize: 14, marginTop: 10 }}>
          <strong>{proOffer.price}</strong> &middot; one time, no subscription
        </div>
      ) : (
        !loading && <div style={{ fontSize: 13, marginTop: 10 }}>Pro is not available to buy right now.</div>
      )}
      <div style={{ fontSize: 13, color: 'var(--fg-2)', marginTop: 10 }}>
        RigCheck is an educational tool. Its results are estimates, not certified DOT weights.
      </div>
      {proOffer && (
        <Button disabled={loading || checkoutOpen} onClick={() => void billing.buyPro()} style={{ marginTop: 14 }}>
          Buy Pro
        </Button>
      )}
    </Card>
  );
}
