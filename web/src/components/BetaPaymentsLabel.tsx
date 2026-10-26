import { isBeta } from '../betaKit';

// Shown on the cards where a tester can buy, only in a build made with VITE_BETA=true.
export function BetaPaymentsLabel() {
  if (!isBeta()) return null;
  return (
    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-purple-deep)', marginTop: 10 }}>
      Beta: test payments. Every purchase uses a test card; no real money moves.
    </div>
  );
}
