import assert from "node:assert/strict";
import test from "node:test";
import { refundCredit, spendCredit } from "./revenuecat.ts";
import type { Env } from "./types.ts";

const env: Env = {
  ANTHROPIC_API_KEY: "unused-here",
  REVENUECAT_SECRET_KEY: "sk_test_123",
  REVENUECAT_PROJECT_ID: "proj_abc",
  REVENUECAT_CURRENCY_CODE: "SCAN",
};

test("spendCredit posts a -1 adjustment to the right URL with the right headers", async (t) => {
  let capturedUrl: string | undefined;
  let capturedInit: RequestInit | undefined;

  t.mock.method(globalThis, "fetch", async (url: string | URL, init?: RequestInit) => {
    capturedUrl = String(url);
    capturedInit = init;
    return new Response(JSON.stringify({ items: [{ balance: 4 }] }), { status: 200 });
  });

  const result = await spendCredit(env, "user-123", "idem-1");

  assert.equal(
    capturedUrl,
    "https://api.revenuecat.com/v2/projects/proj_abc/customers/user-123/virtual_currencies/transactions",
  );
  assert.equal(capturedInit?.method, "POST");
  const headers = capturedInit?.headers as Record<string, string>;
  assert.equal(headers.Authorization, "Bearer sk_test_123");
  assert.equal(headers["Idempotency-Key"], "idem-1");
  assert.deepEqual(JSON.parse(capturedInit?.body as string), { adjustments: { SCAN: -1 } });
  assert.equal(result.ok, true);
  assert.equal(result.status, 200);
});

test("refundCredit posts a +1 adjustment with a distinct idempotency key", async (t) => {
  let capturedInit: RequestInit | undefined;
  t.mock.method(globalThis, "fetch", async (_url: string | URL, init?: RequestInit) => {
    capturedInit = init;
    return new Response(JSON.stringify({}), { status: 200 });
  });

  await refundCredit(env, "user-123", "idem-1");

  const headers = capturedInit?.headers as Record<string, string>;
  assert.equal(headers["Idempotency-Key"], "idem-1-refund");
  assert.deepEqual(JSON.parse(capturedInit?.body as string), { adjustments: { SCAN: 1 } });
});

test("URL-encodes the customer id", async (t) => {
  let capturedUrl: string | undefined;
  t.mock.method(globalThis, "fetch", async (url: string | URL) => {
    capturedUrl = String(url);
    return new Response(JSON.stringify({}), { status: 200 });
  });

  await spendCredit(env, "user with spaces/slashes", "idem-1");
  assert.ok(capturedUrl?.includes(encodeURIComponent("user with spaces/slashes")));
});

test("a 422 (insufficient balance) is surfaced as ok:false, not thrown", async (t) => {
  t.mock.method(
    globalThis,
    "fetch",
    async () =>
      new Response(JSON.stringify({ message: "insufficient balance" }), { status: 422 }),
  );

  const result = await spendCredit(env, "user-123", "idem-2");
  assert.equal(result.ok, false);
  assert.equal(result.status, 422);
});

test("a non-JSON error body doesn't throw", async (t) => {
  t.mock.method(globalThis, "fetch", async () => new Response("<html>502</html>", { status: 502 }));

  const result = await spendCredit(env, "user-123", "idem-3");
  assert.equal(result.ok, false);
  assert.equal(result.status, 502);
  assert.equal(result.body, null);
});
