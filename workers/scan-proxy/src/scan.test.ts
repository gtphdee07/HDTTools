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

// postAdjustment/fetch rejecting (not just returning ok:false) isn't caught
// anywhere around the spendCredit call site either - documents that this
// currently propagates out of runScan as an unhandled rejection rather than
// a clean billing_error response. Same known-gap shape as the matching
// revenuecat.test.ts case, one layer up.
test("spendCredit itself rejecting propagates out of runScan rather than being caught", async () => {
  const deps = makeDeps({
    spendCredit: async () => {
      throw new Error("RevenueCat unreachable");
    },
  });

  await assert.rejects(() => runScan(env, request, deps), /RevenueCat unreachable/);
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
