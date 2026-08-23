// Release tier — real API calls at this Worker's actual service-provider
// boundaries (RevenueCat, Anthropic), called directly, not mocked and not
// routed through the deployed Worker as an intermediary (that's what the
// Weekly tier's scan.weekly.test.ts already does). Gated on deciding to
// push a major Play Store update, not a calendar - see the root
// TESTING.md's "Reconciling..." section and this Worker's own
// TESTING.md for the full design decision (2026-08-21).
//
// Needs ANTHROPIC_API_KEY and REVENUECAT_SECRET_KEY in the environment
// this test runs in - the same two values already set as this Worker's
// deployed secrets via `wrangler secret put`, exported here instead
// (never typed into chat, same discipline as that original setup).
//
// Default behavior is strict, not a graceful skip (2026-08-22 revision,
// per explicit direction): without SKIP_KEYS=1 in the environment (set
// by test-release.ps1's -SkipKeys switch, or directly), a missing key
// stops this whole file before any test runs - a silent skip here would
// be indistinguishable from "the boundary was never actually checked
// this release," which defeats the tier's entire purpose. Only with
// SKIP_KEYS=1 does a missing key fall back to a per-boundary skip
// instead. Separately: a key that IS present but wrong (revoked,
// mistyped, expired) is never allowed to just fail as a generic
// assertion mismatch - assertNotAuthFailure/rejectingAuthFailureAsBadKey
// below turn a real 401/403 from either service into an explicit
// "<ENV_VAR_NAME> appears invalid" failure, naming which key.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { extractFields } from "../claude.ts";
import { DOC_TYPE_CONFIG } from "../docTypes.ts";
import { refundCredit, spendCredit } from "../revenuecat.ts";
import type { Env } from "../types.ts";

const REVENUECAT_SECRET_KEY = process.env.REVENUECAT_SECRET_KEY;
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const SKIP_KEYS = process.env.SKIP_KEYS === "1" || process.env.SKIP_KEYS === "true";

if (!SKIP_KEYS) {
  const missing = [
    !REVENUECAT_SECRET_KEY && "REVENUECAT_SECRET_KEY",
    !ANTHROPIC_API_KEY && "ANTHROPIC_API_KEY",
  ].filter((name): name is string => Boolean(name));

  if (missing.length > 0) {
    throw new Error(
      `Release tier stopped before running: ${missing.join(" and ")} not set in the ` +
        "environment. Export the missing key(s) (the same values set via `wrangler secret " +
        "put`) before running, or explicitly allow skipping with `.\\test-release.ps1 " +
        "-SkipKeys` (or `SKIP_KEYS=1 npm run test:release` directly).",
    );
  }
}

// Missing-key skip reasons only ever apply once SKIP_KEYS=1 has already
// let execution reach this point - see the hard stop above.
const skipRevenueCat = REVENUECAT_SECRET_KEY
  ? false
  : "REVENUECAT_SECRET_KEY not set (SKIP_KEYS=1 was passed, so skipping instead of stopping).";
const skipAnthropic = ANTHROPIC_API_KEY
  ? false
  : "ANTHROPIC_API_KEY not set (SKIP_KEYS=1 was passed, so skipping instead of stopping).";

const env: Env = {
  ANTHROPIC_API_KEY: ANTHROPIC_API_KEY ?? "",
  REVENUECAT_SECRET_KEY: REVENUECAT_SECRET_KEY ?? "",
  // Both non-secret, same as wrangler.toml's [vars].
  REVENUECAT_PROJECT_ID: "proj07f52826",
  REVENUECAT_CURRENCY_CODE: "SCAN",
};

// A wrong RevenueCat secret key still gets a real HTTP response (401/403),
// never a thrown error - postAdjustment() in revenuecat.ts only throws on
// a genuine network failure. Without this check, a bad key would just
// read as "expected 200/422, got 401" - a real result, but not the one
// worth reporting: it's a broken test *environment*, not a broken
// contract with RevenueCat.
function assertNotAuthFailure(result: { status: number; body: unknown }, envVarName: string): void {
  if (result.status === 401 || result.status === 403) {
    assert.fail(
      `${envVarName} appears invalid - RevenueCat returned ${result.status}: ${JSON.stringify(result.body)}`,
    );
  }
}

// The Anthropic SDK throws a typed error (with a .status) on a real 401,
// rather than returning a status-bearing result the way revenuecat.ts
// does - same reasoning as assertNotAuthFailure above, different shape.
async function rejectingAuthFailureAsBadKey<T>(promise: Promise<T>, envVarName: string): Promise<T> {
  try {
    return await promise;
  } catch (err) {
    const status = (err as { status?: unknown }).status;
    if (status === 401 || status === 403) {
      const message = err instanceof Error ? err.message : String(err);
      assert.fail(`${envVarName} appears invalid - Anthropic returned ${status}: ${message}`);
    }
    throw err;
  }
}

test(
  "spendCredit against a real funded customer succeeds, and refundCredit reverses it (net zero balance change)",
  { skip: skipRevenueCat },
  async () => {
    const idempotencyKey = `release-test-${crypto.randomUUID()}`;

    const spend = await spendCredit(env, "weekly-test-user", idempotencyKey);
    assertNotAuthFailure(spend, "REVENUECAT_SECRET_KEY");
    assert.equal(spend.status, 200, `Expected 200, got ${spend.status}: ${JSON.stringify(spend.body)}`);
    assert.equal(spend.ok, true);

    const refund = await refundCredit(env, "weekly-test-user", idempotencyKey);
    assertNotAuthFailure(refund, "REVENUECAT_SECRET_KEY");
    assert.equal(refund.status, 200, `Expected 200, got ${refund.status}: ${JSON.stringify(refund.body)}`);
    assert.equal(refund.ok, true);
  },
);

test(
  "spendCredit against a real customer with zero balance gets the real 422 scan.ts depends on",
  { skip: skipRevenueCat },
  async () => {
    const result = await spendCredit(
      env,
      "weekly-test-user-no-credits",
      `release-test-${crypto.randomUUID()}`,
    );

    assertNotAuthFailure(result, "REVENUECAT_SECRET_KEY");
    assert.equal(result.status, 422, `Expected 422, got ${result.status}: ${JSON.stringify(result.body)}`);
    assert.equal(result.ok, false);
  },
);

test(
  "extractFields against the real Anthropic API extracts real fields from a real truck tag photo",
  { skip: skipAnthropic },
  async () => {
    const imagePath = path.resolve(
      path.dirname(fileURLToPath(import.meta.url)),
      "../../../../ExampleDocs/AddieTag.jpg",
    );
    const imageBase64 = readFileSync(imagePath, "base64");

    const fields = await rejectingAuthFailureAsBadKey(
      extractFields(env.ANTHROPIC_API_KEY, imageBase64, "image/jpeg", DOC_TYPE_CONFIG.truck_tag),
      "ANTHROPIC_API_KEY",
    );

    // Proves the real request shape (model name, forced tool_choice, image
    // content block) is still accepted and still returns a matching
    // tool_use block with real field names - not any particular value,
    // since real OCR/vision accuracy on a real photo isn't this test's
    // concern (that's tests/test_scale_ticket_real_photo.py's job on the
    // Python side, and this is the same idea applied to Claude directly).
    assert.equal(typeof fields, "object");
    assert.ok("manufacturer" in fields);
    assert.ok("gvwr_lb" in fields);
  },
);

test(
  "extractFields against the real Anthropic API rejects an invalid key with a real auth error",
  { skip: skipAnthropic },
  async () => {
    // Deliberately bad key, by design - not the assertNotAuthFailure/
    // rejectingAuthFailureAsBadKey case above (those exist for *this*
    // test's key, ANTHROPIC_API_KEY, unexpectedly being the one that's
    // wrong; this test's own point is proving a wrong key is correctly
    // rejected, not proving ANTHROPIC_API_KEY itself is good).
    await assert.rejects(
      extractFields("sk-ant-api03-invalid-release-test-key", "aGVsbG8=", "image/jpeg", DOC_TYPE_CONFIG.truck_tag),
      (err: unknown) => {
        const status = (err as { status?: unknown }).status;
        const message = err instanceof Error ? err.message : String(err);
        return status === 401 || /401|authentication/i.test(message);
      },
    );
  },
);
