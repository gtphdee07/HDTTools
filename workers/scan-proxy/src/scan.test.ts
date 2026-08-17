// Unit tests for the money-critical control flow in scan.ts, using fake
// deps — no real Anthropic SDK or network call involved, so these run with
// nothing installed beyond Node itself.
import assert from "node:assert/strict";
import test from "node:test";
import type { ScanRequest } from "./request.ts";
import { runScan, type ScanDeps } from "./scan.ts";
import type { Env } from "./types.ts";

const env: Env = {
  ANTHROPIC_API_KEY: "sk-ant-test",
  REVENUECAT_SECRET_KEY: "sk_test",
  REVENUECAT_PROJECT_ID: "proj",
  REVENUECAT_CURRENCY_CODE: "SCAN",
};

const request: ScanRequest = {
  app_user_id: "user-1",
  doc_type: "truck_tag",
  image_base64: "aGVsbG8=",
  media_type: "image/jpeg",
};

function makeDeps(overrides: Partial<ScanDeps>): ScanDeps {
  return {
    spendCredit: async () => ({ ok: true, status: 200, body: {} }),
    refundCredit: async () => ({ ok: true, status: 200, body: {} }),
    extractFields: async () => ({ manufacturer: "Ford" }),
    ...overrides,
  };
}

test("successful scan charges exactly once and returns the extracted fields", async () => {
  let spendCalls = 0;
  const deps = makeDeps({
    spendCredit: async () => {
      spendCalls++;
      return { ok: true, status: 200, body: {} };
    },
  });

  const res = await runScan(env, request, deps);
  assert.equal(res.status, 200);
  assert.equal(spendCalls, 1);
  assert.deepEqual(await res.json(), {
    ok: true,
    doc_type: "truck_tag",
    fields: { manufacturer: "Ford" },
  });
});

test("insufficient credits (422) returns 402 and never calls Claude", async () => {
  let extractCalls = 0;
  const deps = makeDeps({
    spendCredit: async () => ({ ok: false, status: 422, body: {} }),
    extractFields: async () => {
      extractCalls++;
      return {};
    },
  });

  const res = await runScan(env, request, deps);
  assert.equal(res.status, 402);
  assert.equal(((await res.json()) as { code: string }).code, "insufficient_credits");
  assert.equal(extractCalls, 0, "a zero-credit user must never trigger a paid Claude call");
});

test("a non-422 billing failure returns 502 and never calls Claude", async () => {
  let extractCalls = 0;
  const deps = makeDeps({
    spendCredit: async () => ({ ok: false, status: 500, body: {} }),
    extractFields: async () => {
      extractCalls++;
      return {};
    },
  });

  const res = await runScan(env, request, deps);
  assert.equal(res.status, 502);
  assert.equal(((await res.json()) as { code: string }).code, "billing_error");
  assert.equal(extractCalls, 0);
});

test("extraction failure refunds the credit for the same user and reports extraction_failed", async () => {
  let refundCalls = 0;
  let refundedUser: string | undefined;
  const deps = makeDeps({
    extractFields: async () => {
      throw new Error("Claude API error");
    },
    refundCredit: async (_env, customerId) => {
      refundCalls++;
      refundedUser = customerId;
      return { ok: true, status: 200, body: {} };
    },
  });

  const res = await runScan(env, request, deps);
  assert.equal(res.status, 502);
  assert.equal(((await res.json()) as { code: string }).code, "extraction_failed");
  assert.equal(refundCalls, 1);
  assert.equal(refundedUser, "user-1");
});

test("a failed refund attempt doesn't crash the request", async () => {
  const deps = makeDeps({
    extractFields: async () => {
      throw new Error("Claude API error");
    },
    refundCredit: async () => {
      throw new Error("RevenueCat unreachable");
    },
  });

  const res = await runScan(env, request, deps);
  assert.equal(res.status, 502);
  assert.equal(((await res.json()) as { code: string }).code, "extraction_failed");
});

test("a successful scan never issues a refund", async () => {
  let refundCalls = 0;
  const deps = makeDeps({
    refundCredit: async () => {
      refundCalls++;
      return { ok: true, status: 200, body: {} };
    },
  });

  await runScan(env, request, deps);
  assert.equal(refundCalls, 0);
});
