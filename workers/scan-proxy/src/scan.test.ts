// Unit tests for the money-critical control flow in scan.ts, using fake
// deps — no real Anthropic SDK or network call involved. Still needs the proxy's
// `npm install` (requireInstall.ts stops with the fix when it is missing).
import "./requireInstall.ts";
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
  SUPABASE_URL: "https://test-project.supabase.co",
};

// What index.ts passes in after verifying the account token.
const USER_ID = "user-1";

const request: ScanRequest = {
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

  const res = await runScan(env, USER_ID, request, deps);
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

  const res = await runScan(env, USER_ID, request, deps);
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

  const res = await runScan(env, USER_ID, request, deps);
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

  const res = await runScan(env, USER_ID, request, deps);
  assert.equal(res.status, 502);
  assert.equal(((await res.json()) as { code: string }).code, "extraction_failed");
  assert.equal(refundCalls, 1);
  assert.equal(refundedUser, USER_ID);
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

  const res = await runScan(env, USER_ID, request, deps);
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

  const res = await runScan(env, USER_ID, request, deps);
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

  await runScan(env, USER_ID, request, deps);
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

  await runScan(env, USER_ID, request, deps);
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

  const res = await runScan(env, USER_ID, request, deps);
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

  const res = await runScan(env, USER_ID, request, deps);
  assert.equal(res.status, 502);
  assert.equal(((await res.json()) as { code: string }).code, "extraction_failed");
  assert.equal(refundCalls, 1);
});

test("a request with client_request_id gets a stable RevenueCat idempotency key derived from it, never the raw id", async () => {
  const spendKeys: string[] = [];
  const deps = makeDeps({
    spendCredit: async (_env, _customerId, idempotencyKey) => {
      spendKeys.push(idempotencyKey);
      return { ok: true, status: 200, body: {} };
    },
  });

  await runScan(env, USER_ID, { ...request, client_request_id: "stable-attempt-1" }, deps);
  await runScan(env, USER_ID, { ...request, client_request_id: "stable-attempt-1" }, deps);
  await runScan(env, USER_ID, { ...request, client_request_id: "stable-attempt-3" }, deps);
  assert.equal(spendKeys[0], spendKeys[1]);
  assert.notEqual(spendKeys[0], spendKeys[2]);
  assert.notEqual(spendKeys[0], "stable-attempt-1");
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
  await runScan(env, USER_ID, retryRequest, deps);
  await runScan(env, USER_ID, retryRequest, deps);

  assert.equal(spendKeys.length, 2);
  assert.equal(spendKeys[0], spendKeys[1]);
});

test("a request without client_request_id falls back to a fresh random key each call, unchanged from today", async () => {
  const spendKeys: string[] = [];
  const deps = makeDeps({
    spendCredit: async (_env, _customerId, idempotencyKey) => {
      spendKeys.push(idempotencyKey);
      return { ok: true, status: 200, body: {} };
    },
  });

  await runScan(env, USER_ID, request, deps);
  await runScan(env, USER_ID, request, deps);

  assert.notEqual(spendKeys[0], spendKeys[1]);
});

test("trailer_tag and scale_ticket scans use their own doc type's config and echo it back", async () => {
  for (const docType of ["trailer_tag", "scale_ticket"] as const) {
    const deps = makeDeps({
      extractFields: async (_apiKey, _image, _mediaType, config) => ({ toolNameUsed: config.toolName }),
    });

    const res = await runScan(env, USER_ID, { ...request, doc_type: docType }, deps);
    assert.equal(res.status, 200);
    const body = (await res.json()) as { doc_type: string; fields: { toolNameUsed: string } };
    assert.equal(body.doc_type, docType);
    assert.equal(body.fields.toolNameUsed, `record_${docType}`);
  }
});

// A fake RevenueCat ledger that behaves like the real one for the property
// these tests need: a Spend or Refund whose Idempotency-Key was already seen
// is replayed (answered ok, balance untouched), and a Spend with no credit
// left is a 422. Everything else about RevenueCat is out of scope here.
function makeLedger(credits: number) {
  const seen = new Set<string>();
  const spendKeys: string[] = [];
  const refundKeys: string[] = [];
  const ledger = {
    credits,
    spendKeys,
    refundKeys,
    extractions: 0,
    spendCredit: (async (_env, _customerId, key) => {
      spendKeys.push(key);
      if (seen.has(key)) return { ok: true, status: 200, body: {} };
      if (ledger.credits < 1) return { ok: false, status: 422, body: {} };
      seen.add(key);
      ledger.credits--;
      return { ok: true, status: 200, body: {} };
    }) as ScanDeps["spendCredit"],
    // revenuecat.ts derives the refund's own key by suffixing "-refund".
    refundCredit: (async (_env, _customerId, key) => {
      const refundKey = `${key}-refund`;
      refundKeys.push(refundKey);
      if (!seen.has(refundKey)) {
        seen.add(refundKey);
        ledger.credits++;
      }
      return { ok: true, status: 200, body: {} };
    }) as ScanDeps["refundCredit"],
  };
  return ledger;
}

function countingDeps(ledger: ReturnType<typeof makeLedger>, failOn?: (image: string) => boolean): ScanDeps {
  return {
    spendCredit: ledger.spendCredit,
    refundCredit: ledger.refundCredit,
    extractFields: async (_apiKey, image) => {
      ledger.extractions++;
      if (failOn?.(image)) throw new Error("undecodable image");
      return { manufacturer: "Ford" };
    },
  };
}

test("one client_request_id with many different images cannot extract more than the credits paid for", async () => {
  const ledger = makeLedger(1);
  const deps = countingDeps(ledger);

  const statuses: number[] = [];
  for (let i = 0; i < 5; i++) {
    const res = await runScan(
      env,
      USER_ID,
      { ...request, image_base64: `aW1hZ2Ux${i}`, client_request_id: "one-id" },
      deps,
    );
    statuses.push(res.status);
  }

  assert.deepEqual(statuses, [200, 402, 402, 402, 402]);
  assert.equal(ledger.extractions, 1, "five images under one id must not buy five extractions for one credit");
});

test("the same client_request_id is charged separately per account, document type and image", async () => {
  const ledger = makeLedger(10);
  const deps = countingDeps(ledger);
  const base = { ...request, client_request_id: "shared-id" };

  await runScan(env, "user-1", base, deps);
  await runScan(env, "user-2", base, deps);
  await runScan(env, "user-1", { ...base, doc_type: "scale_ticket" }, deps);
  await runScan(env, "user-1", { ...base, image_base64: "b3RoZXI=" }, deps);

  assert.equal(new Set(ledger.spendKeys).size, 4, "each variation is its own RevenueCat charge");
  assert.equal(ledger.credits, 6);
});

test("an honest retry of the same request (account, type, image and id) charges once", async () => {
  const ledger = makeLedger(3);
  const deps = countingDeps(ledger);
  const retry = { ...request, client_request_id: "lost-response-1" };

  await runScan(env, USER_ID, retry, deps);
  await runScan(env, USER_ID, retry, deps);

  assert.equal(ledger.spendKeys[0], ledger.spendKeys[1]);
  assert.equal(ledger.credits, 2, "the retry replays the Spend, so only one credit is gone");
});

test("a spend key is a fixed-width hash, so no other request's refund key can equal it", async () => {
  const ledger = makeLedger(5);
  const deps = countingDeps(ledger, () => true);

  await runScan(env, USER_ID, { ...request, client_request_id: "X" }, deps);
  await runScan(env, USER_ID, { ...request, client_request_id: "X-refund" }, deps);

  for (const key of ledger.spendKeys) assert.match(key, /^[0-9a-f]{64}$/);
  for (const spendKey of ledger.spendKeys) {
    assert.ok(!ledger.refundKeys.includes(spendKey), "a spend key must never be another request's refund key");
  }
  assert.equal(new Set([...ledger.spendKeys, ...ledger.refundKeys]).size, 4);
});

test("replaying a delivered scan's id with an undecodable image is charged on its own, not a free extraction", async () => {
  const ledger = makeLedger(2);
  const deps = countingDeps(ledger, (image) => image === "YmFk");

  const good = await runScan(env, USER_ID, { ...request, client_request_id: "K" }, deps);
  const replay = await runScan(env, USER_ID, { ...request, image_base64: "YmFk", client_request_id: "K" }, deps);

  assert.equal(good.status, 200);
  assert.equal(replay.status, 502);
  assert.equal(ledger.spendKeys.length, 2);
  assert.notEqual(ledger.spendKeys[0], ledger.spendKeys[1], "the failed replay is its own charge");
  assert.equal(ledger.credits, 1, "one delivered scan costs one credit; the failed one is charged then refunded");
});
