import { useAuth } from './auth';
import { useBilling } from './billing';

// Whether the visitor can scan right now, and if not, the one thing standing in the way.
export type ScanAccess =
  // Pro with at least one Scan Credit.
  | { kind: 'ready'; balance: number }
  // This build has no accounts or purchases set up.
  | { kind: 'unavailable' }
  // Not signed in.
  | { kind: 'sign-in' }
  // The account, plan or balance is still being read (or the starter scans are on their way).
  | { kind: 'checking' }
  | { kind: 'load-failed' }
  // Signed in on the Free plan: scans are part of Pro (ADR-0006).
  | { kind: 'upgrade' }
  // Pro with no Scan Credit left.
  | { kind: 'no-scans' };

export function useScanAccess(): ScanAccess {
  const auth = useAuth();
  const billing = useBilling();

  if (!auth.configured || !billing.available) return { kind: 'unavailable' };
  if (auth.loading) return { kind: 'checking' };
  if (!auth.user) return { kind: 'sign-in' };
  if (billing.loadFailed) return { kind: 'load-failed' };
  if (billing.loading || billing.scanBalance === null) return { kind: 'checking' };
  if (!billing.isPro) return { kind: 'upgrade' };
  if (billing.scanBalance < 1) return billing.scansUpdating ? { kind: 'checking' } : { kind: 'no-scans' };
  return { kind: 'ready', balance: billing.scanBalance };
}
