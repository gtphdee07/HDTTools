// External suite (ADR-0008): real calls from revenuecat.ts to RevenueCat REST v2
// virtual-currency endpoints, using the dedicated test customers (never
// smoke-test-user). Run only via test-external.ps1 / `npm run test:external`.
// The "[revenuecat-rest]" name tag is what the wrapper filters on.
//
// A missing REVENUECAT_SECRET_KEY fails the run; skipping is only ever the wrapper's
// explicit -Skip, which records `skipped` and leaves the surface stale. Calls are free
// (ledger adjustments), and every journey ends back at its starting balance.
import assert from "node:assert/strict";
import test from "node:test";
import { refundCredit, spendCredit } from "../revenuecat.ts";
import type { TransactionResult } from "../revenuecat.ts";
import type { Env } from "../types.ts";

const SECRET_KEY = process.env.REVENUECAT_SECRET_KEY;
if (!SECRET_KEY) {
  throw new Error(
    "External test credentials missing: REVENUECAT_SECRET_KEY is not set in the environment " +
      "(a v2 key with Customer information read and write).",
  );
}

const FUNDED = "weekly-test-user";
const EMPTY = "weekly-test-user-no-credits";
const UNKNOWN = "external-suite-no-such-customer";

const env: Env = {
  ANTHROPIC_API_KEY: "",
  REVENUECAT_SECRET_KEY: SECRET_KEY,
  // Both non-secret, same as wrangler.toml's [vars].
  REVENUECAT_PROJECT_ID: "proj07f52826",
  REVENUECAT_CURRENCY_CODE: "SCAN",
  SUPABASE_URL: "", // unused here: this surface talks to RevenueCat only
};

const freshKey = () => `external-test-${crypto.randomUUID()}`;

// 401/403 means the test environment is broken (key revoked, or missing a permission),
// not that the contract changed; name the call so the right permission gets fixed.
function assertAuthorized(label: string, result: { status: number; body: unknown }): void {
  if (result.status === 401 || result.status === 403) {
    assert.fail(
      `${label}: REVENUECAT_SECRET_KEY rejected (${result.status}) - check the key's permissions ` +
        `(needs Customer information read and write): ${JSON.stringify(result.body)}`,
    );
  }
}

interface BalanceItem {
  object: string;
  currency_code: string;
  balance: number;
}

function assertBalanceList(body: unknown): BalanceItem[] {
  const list = body as { object?: string; items?: BalanceItem[] };
  assert.equal(list.object, "list");
  assert.ok(Array.isArray(list.items));
  for (const item of list.items) {
    assert.equal(item.object, "virtual_currency_balance");
    assert.equal(typeof item.currency_code, "string");
    assert.equal(typeof item.balance, "number");
  }
  return list.items;
}

const scanBalance = (items: BalanceItem[]) =>
  items.find((i) => i.currency_code === env.REVENUECAT_CURRENCY_CODE)?.balance ?? 0;

// revenuecat.ts has no balance read (Spend's 422 is the Worker's balance check), so the
// suite reads it directly to prove each adjustment's effect.
async function readBalance(customerId: string, key: string = env.REVENUECAT_SECRET_KEY): Promise<TransactionResult> {
  const res = await fetch(
    `https://api.revenuecat.com/v2/projects/${env.REVENUECAT_PROJECT_ID}/customers/${encodeURIComponent(customerId)}/virtual_currencies`,
    { headers: { Authorization: `Bearer ${key}` }, signal: AbortSignal.timeout(10_000) },
  );
  return { ok: res.ok, status: res.status, body: await res.json().catch(() => null) };
}

async function balanceOf(customerId: string): Promise<number> {
  const read = await readBalance(customerId);
  assertAuthorized("balance read", read);
  assert.equal(read.status, 200, JSON.stringify(read.body));
  return scanBalance(assertBalanceList(read.body));
}

test("[revenuecat-rest] reachable and authenticated: the key reads a balance, a bad key is a 401 authentication_error", async () => {
  const read = await readBalance(FUNDED);
  assertAuthorized("balance read", read);
  assert.equal(read.status, 200);

  const bad = await readBalance(FUNDED, "sk_not-a-real-key");
  assert.equal(bad.status, 401);
  assert.equal((bad.body as { type?: string }).type, "authentication_error");

  const badSpend = await spendCredit({ ...env, REVENUECAT_SECRET_KEY: "sk_not-a-real-key" }, FUNDED, freshKey());
  assert.equal(badSpend.ok, false);
  assert.equal(badSpend.status, 401);
});

test("[revenuecat-rest] balance response shape: a funded customer lists a numeric SCAN balance, an empty one lists none", async () => {
  const funded = await readBalance(FUNDED);
  assertAuthorized("balance read", funded);
  const items = assertBalanceList(funded.body);
  assert.ok(items.some((i) => i.currency_code === "SCAN"), "funded customer has a SCAN balance");
  assert.ok(
    scanBalance(items) > 0,
    `${FUNDED} must hold credits for the journey; top it up in the RevenueCat dashboard`,
  );

  const empty = await readBalance(EMPTY);
  assertAuthorized("balance read", empty);
  assert.equal(scanBalance(assertBalanceList(empty.body)), 0);
});

test("[revenuecat-rest] adjustment response shape: Spend and Refund return the updated balance list", async () => {
  const before = await balanceOf(FUNDED);
  const key = freshKey();
  let spent = false;
  try {
    const spend = await spendCredit(env, FUNDED, key);
    assertAuthorized("spendCredit", spend);
    assert.equal(spend.status, 200, JSON.stringify(spend.body));
    spent = true;
    assert.equal(spend.ok, true);
    assert.equal(scanBalance(assertBalanceList(spend.body)), before - 1);
  } finally {
    // Only undo a Spend that happened; refunding a failed one would inflate the balance.
    if (spent) {
      const refund = await refundCredit(env, FUNDED, key);
      assertAuthorized("refundCredit", refund);
      assert.equal(refund.status, 200, JSON.stringify(refund.body));
      assert.equal(scanBalance(assertBalanceList(refund.body)), before);
    }
  }
});

test("[revenuecat-rest] error contract: Spend on an empty balance is the 422 scan.ts treats as insufficient credits", async () => {
  const result = await spendCredit(env, EMPTY, freshKey());
  assertAuthorized("spendCredit", result);
  assert.equal(result.status, 422, JSON.stringify(result.body));
  assert.equal(result.ok, false);
  assert.equal((result.body as { type?: string }).type, "unprocessable_entity_error");
  assert.equal(await balanceOf(EMPTY), 0, "a rejected Spend must not change the balance");
});

test("[revenuecat-rest] error contract: an unknown customer is a 404 resource_missing, which scan.ts reports as a billing error", async () => {
  const result = await spendCredit(env, UNKNOWN, freshKey());
  assertAuthorized("spendCredit", result);
  assert.equal(result.status, 404, JSON.stringify(result.body));
  assert.equal(result.ok, false);
  assert.equal((result.body as { type?: string }).type, "resource_missing");
});

test("[revenuecat-rest] journey: Spend then Refund restores the balance, and retrying either with the same key changes nothing", async () => {
  const before = await balanceOf(FUNDED);
  const key = freshKey();
  let spent = false;
  try {
    assert.equal((await spendCredit(env, FUNDED, key)).status, 200);
    spent = true;
    assert.equal(await balanceOf(FUNDED), before - 1);

    const retriedSpend = await spendCredit(env, FUNDED, key);
    assert.equal(retriedSpend.status, 200);
    assert.equal(await balanceOf(FUNDED), before - 1, "an idempotent Spend retry must not charge twice");
  } finally {
    if (spent) assert.equal((await refundCredit(env, FUNDED, key)).status, 200);
  }
  assert.equal(await balanceOf(FUNDED), before, "Refund restores the balance");

  assert.equal((await refundCredit(env, FUNDED, key)).status, 200);
  assert.equal(await balanceOf(FUNDED), before, "an idempotent Refund retry must not credit twice");
});
