import { useBilling } from './billing';
import type { BillingState } from './billing';

// The plan the account's saves report to the database, which picks the Garage and History cap from it
// (supabase/migrations/20261023000000_plan_caps.sql). null means the plan could not be read yet or at
// all; the database then uses the Pro caps so a Pro account is not refused or pruned over a failed read.
export type Plan = 'free' | 'pro';

function planOf(billing: Pick<BillingState, 'available' | 'isPro' | 'loading' | 'loadFailed' | 'scanBalance'>): Plan | null {
  // A build without purchases cannot hold Pro.
  if (!billing.available) return 'free';
  // Pro once seen stays Pro for the session: a purchase settles before RevenueCat's own read catches up.
  if (billing.isPro) return 'pro';
  // The balance is the last part of the plan load to arrive, so null means Free is not yet known.
  if (billing.loading || billing.loadFailed || billing.scanBalance === null) return null;
  return 'free';
}

export function usePlan(): Plan | null {
  return planOf(useBilling());
}

// How a full Garage is described: "is full (the Free plan holds 5 Rigs)". The cap is the one the database
// named, so it is never written here; whose it is depends on the plan the save reported.
export function garageFullText(cap: number | null, plan: Plan | null): string {
  if (cap === null) return 'is full';
  const rigs = `${cap} Rig${cap === 1 ? '' : 's'}`;
  if (plan === 'free') return `is full (the Free plan holds ${rigs})`;
  if (plan === 'pro') return `is full (Pro holds ${rigs})`;
  return `is full (${rigs})`;
}
