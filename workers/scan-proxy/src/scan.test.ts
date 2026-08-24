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

test("[sanity] successful scan charges exactly once and returns the extracted fields", async () => {
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

test("a failed refund attempt doesn't crash the request, and doesn't falsely claim a refund happened", async () => {
  const deps = makeDeps({
    extractFields: async () => {
      throw new Error("Claude API error");
    },
    refundCredit: async () => {
      throw new Error("RevenueCat unreachable");
    },
  });

  const res = await runScan(env, request, deps);
  const body = (await res.json()) as { code: string; message: string };
  assert.equal(res.status, 502);
  assert.equal(body.code, "extraction_failed_no_refund");
  assert.doesNotMatch(body.message, /credit refunded/i);
});

test("a refund call that resolves with ok:false (not a throw) is also treated as a failed refund", async () => {
  const deps = makeDeps({
    extractFields: async () => {
      throw new Error("Claude API error");
    },
    refundCredit: async () => ({ ok: false, status: 500, body: {} }),
  });

  const res = await runScan(env, request, deps);
  const body = (await res.json()) as { code: string };
  assert.equal(res.status, 502);
  assert.equal(body.code, "extraction_failed_no_refund");
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

// revenuecat.ts derives the refund's distinct "-refund" idempotency key from
// whatever it's given, so scan.ts's own responsibility is to generate one
// key per runScan call and pass that same raw value to both spendCredit and
// refundCredit. A regression minting a fresh key per call would silently
// break the charge/refund pairing's idempotency and nothing else would
// catch it, since revenuecat.test.ts only tests its own suffixing logic in
// isolation.
test("spendCredit and refundCredit are called with the same idempotency key", async () => {
  let spendKey: string | undefined;
  let refundKey: string | undefined;
  const deps = makeDeps({
    extractFields: async () => {
      throw new Error("Claude API error");
    },
    spendCredit: async (_env, _customerId, idempotencyKey) => {
      spendKey = idempotencyKey;
      return { ok: true, status: 200, body: {} };
    },
    refundCredit: async (_env, _customerId, idempotencyKey) => {
      refundKey = idempotencyKey;
      return { ok: true, status: 200, body: {} };
    },
  });

  await runScan(env, request, deps);
  assert.ok(spendKey, "spendCredit should have been called with a key");
  assert.equal(spendKey, refundKey);
});

// spendCredit rejecting (RevenueCat unreachable, or its own
// AbortSignal.timeout firing on a hung request) is mapped to the same
// billing_error response as a non-ok status, not left to propagate as an
// unhandled rejection - this is what makes revenuecat.ts's timeout an
// actual clean bounded error instead of just a faster crash. The fake dep
// throwing immediately stands in for what a real 10s timeout eventually
// does, without the test having to wait for one.
test("a spendCredit rejection (e.g. a timeout) is mapped to a clean billing_error response, not a hang", async () => {
  let extractCalls = 0;
  const deps = makeDeps({
    spendCredit: async () => {
      throw new Error("RevenueCat unreachable");
    },
    extractFields: async () => {
      extractCalls++;
      return {};
    },
  });

  const res = await runScan(env, request, deps);
  assert.equal(res.status, 502);
  assert.equal(((await res.json()) as { code: string }).code, "billing_error");
  assert.equal(extractCalls, 0, "a failed charge must never trigger a paid Claude call");
});

// extractFields rejecting with a timeout-shaped error already falls through
// the existing generic catch same as any other extraction failure (refund
// + extraction_failed) - this pins that down explicitly for the timeout
// case specifically, since claude.ts's ANTHROPIC_TIMEOUT_MS is what's
// meant to eventually produce this exact shape of rejection.
test("an extractFields timeout is refunded and mapped to extraction_failed like any other extraction failure", async () => {
  let refundCalls = 0;
  const deps = makeDeps({
    extractFields: async () => {
      throw new Error("Request timed out.");
    },
    refundCredit: async () => {
      refundCalls++;
      return { ok: true, status: 200, body: {} };
    },
  });

  const res = await runScan(env, request, deps);
  assert.equal(res.status, 502);
  assert.equal(((await res.json()) as { code: string }).code, "extraction_failed");
  assert.equal(refundCalls, 1);
});

test("a request with client_request_id uses it as the RevenueCat idempotency key instead of a random one", async () => {
  let spendKey: string | undefined;
  const deps = makeDeps({
    spendCredit: async (_env, _customerId, idempotencyKey) => {
      spendKey = idempotencyKey;
      return { ok: true, status: 200, body: {} };
    },
  });

  await runScan(env, { ...request, client_request_id: "stable-attempt-1" }, deps);
  assert.equal(spendKey, "stable-attempt-1");
});

// This is the whole point of Gap B: two calls that represent retries of the
// same logical attempt (same client_request_id) must spend exactly once.
// RevenueCat is the one that actually enforces the "at most once" guarantee
// given a repeated Idempotency-Key header - this test only proves scan.ts
// hands it the *same* key both times, which is scan.ts's own responsibility.
test("two runScan calls with the same client_request_id use the same idempotency key both times", async () => {
  const spendKeys: string[] = [];
  const deps = makeDeps({
    spendCredit: async (_env, _customerId, idempotencyKey) => {
      spendKeys.push(idempotencyKey);
      return { ok: true, status: 200, body: {} };
    },
  });

  const retryRequest = { ...request, client_request_id: "stable-attempt-2" };
  await runScan(env, retryRequest, deps);
  await runScan(env, retryRequest, deps);

  assert.deepEqual(spendKeys, ["stable-attempt-2", "stable-attempt-2"]);
});

test("a request without client_request_id falls back to a fresh random key each call, unchanged from today", async () => {
  const spendKeys: string[] = [];
  const deps = makeDeps({
    spendCredit: async (_env, _customerId, idempotencyKey) => {
      spendKeys.push(idempotencyKey);
      return { ok: true, status: 200, body: {} };
    },
  });

  await runScan(env, request, deps);
  await runScan(env, request, deps);

  assert.notEqual(spendKeys[0], spendKeys[1]);
});

test("trailer_tag and scale_ticket scans use their own doc type's config and echo it back", async () => {
  for (const docType of ["trailer_tag", "scale_ticket"] as const) {
    const deps = makeDeps({
      extractFields: async (_apiKey, _image, _mediaType, config) => ({ toolNameUsed: config.toolName }),
    });

    const res = await runScan(env, { ...request, doc_type: docType }, deps);
    assert.equal(res.status, 200);
    const body = (await res.json()) as { doc_type: string; fields: { toolNameUsed: string } };
    assert.equal(body.doc_type, docType);
    assert.equal(body.fields.toolNameUsed, `record_${docType}`);
  }
});
