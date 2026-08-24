// Thin client for RevenueCat's Virtual Currency API (Developer API v2), used
// to hold the paid-scan credit ledger so this Worker never needs a database
// of its own. Docs: https://www.revenuecat.com/docs/offerings/virtual-currency
import type { Env } from "./types.ts";

const API_BASE = "https://api.revenuecat.com/v2";

// Tighter than claude.ts's ANTHROPIC_TIMEOUT_MS - this is a simple ledger
// write, not a vision model call, so a hang here should be caught sooner.
export const REVENUECAT_TIMEOUT_MS = 10_000;

export interface TransactionResult {
  ok: boolean;
  status: number;
  body: unknown;
}

async function postAdjustment(
  env: Env,
  customerId: string,
  amount: number,
  idempotencyKey: string,
): Promise<TransactionResult> {
  const url = `${API_BASE}/projects/${env.REVENUECAT_PROJECT_ID}/customers/${encodeURIComponent(
    customerId,
  )}/virtual_currencies/transactions`;

  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.REVENUECAT_SECRET_KEY}`,
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify({
      adjustments: { [env.REVENUECAT_CURRENCY_CODE]: amount },
    }),
    signal: AbortSignal.timeout(REVENUECAT_TIMEOUT_MS),
  });

  const body = await res.json().catch(() => null);
  return { ok: res.ok, status: res.status, body };
}

// Spends one credit. RevenueCat rejects this with 422 if the customer's
// balance is insufficient — that response IS the balance check, so callers
// don't need a separate read-then-decrement step (which would race).
export function spendCredit(
  env: Env,
  customerId: string,
  idempotencyKey: string,
): Promise<TransactionResult> {
  return postAdjustment(env, customerId, -1, idempotencyKey);
}

// Returns one credit — called when a scan was charged but Claude failed to
// extract anything, so the user isn't billed for a failed scan.
export function refundCredit(
  env: Env,
  customerId: string,
  idempotencyKey: string,
): Promise<TransactionResult> {
  return postAdjustment(env, customerId, 1, `${idempotencyKey}-refund`);
}
