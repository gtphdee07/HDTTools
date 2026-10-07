// Weekly tier — real, bounded network calls against the actual deployed
// Worker and RevenueCat, using dedicated disposable test customers (never
// smoke-test-user, which stays reserved for manual Android field testing).
// Deliberately kept out of `src/*.test.ts`'s glob (used by `npm test`/
// `npm run test:sanity`) by living in this subdirectory — run explicitly
// via `npm run test:weekly`, not on every commit. Needs no Anthropic or
// RevenueCat key (unlike the Release tier) - every scan case below only
// talks to the public /v1/scan endpoint, the same way a real client does -
// but since #21 it does need the Supabase test users' sign-in credentials
// (see liveToken.ts), because that endpoint now requires an account token.
//
// package.json's `pretest:weekly` hook (npm's own pre-script convention)
// runs `typecheck` then `deploy` before this file ever runs, so "the
// deployed Worker" above always means Worker code that matches what's on
// disk right now - not whatever was last manually deployed. Found the
// hard way 2026-08-23: a real hands-on idempotency check against the
// Android app genuinely failed because the local fix wasn't live yet -
// see NEXT_STEPS.md / ARCHIVE_MONETIZATION.md item #5.
import assert from "node:assert/strict";
import { Buffer } from "node:buffer";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  claimsViolation,
  headerViolation,
  jwksUrl,
  jwksViolation,
} from "../accountTokenContract.ts";
import { liveSupabaseUrl, signInTestAccount, type TestAccount } from "../liveToken.ts";

const SCAN_ENDPOINT = "https://rigcheck-scan-proxy.wanderingtrailswaggingtails.workers.dev/v1/scan";
const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");

// Since #21 the Worker spends the account named by the request's Supabase
// access token (the RevenueCat customer is the Supabase user's UUID), so
// each case below signs in a real Supabase test user - "funded" and
// "noCredits" in liveToken.ts - instead of naming a customer in the body.
// Never smoke-test-user. Credentials: see liveToken.ts.
async function scan(account: TestAccount | null, docType: string, imageBase64: string, mediaType: string) {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (account !== null) headers.Authorization = `Bearer ${await signInTestAccount(account)}`;
  const response = await fetch(SCAN_ENDPOINT, {
    method: "POST",
    headers,
    body: JSON.stringify({
      doc_type: docType,
      image_base64: imageBase64,
      media_type: mediaType,
    }),
  });
  return { status: response.status, body: await response.json() };
}

// Free (no token, so nothing is spent and Claude is never reached): the
// deployed Worker refuses a scan that carries no account token.
test("a request with no account token gets 401 unauthorized from the deployed Worker", async () => {
  const result = await scan(null, "truck_tag", "aGVsbG8=", "image/jpeg");

  assert.equal(result.status, 401);
  assert.deepEqual(result.body, {
    ok: false,
    code: "unauthorized",
    message: "Missing or invalid account token.",
  });
});

// Free: signs in a real Supabase user and checks the real token's header and
// claims, and the real JWKS document, against the same contract definition
// (accountTokenContract.ts) the Worker verifies and the offline fakes mint to
// - so Supabase changing its signing setup fails here, not in a user's scan.
test("a real Supabase token and JWKS match the shared account-token contract", async () => {
  const supabaseUrl = liveSupabaseUrl();
  const token = await signInTestAccount("funded");
  const [header, claims] = token
    .split(".")
    .slice(0, 2)
    .map((part) => JSON.parse(Buffer.from(part, "base64url").toString("utf8")) as unknown);

  assert.equal(headerViolation(header), null);
  assert.equal(claimsViolation(claims, supabaseUrl, Math.floor(Date.now() / 1000)), null);

  const jwks = await (await fetch(jwksUrl(supabaseUrl))).json();
  assert.equal(jwksViolation(jwks), null);
  assert.ok(
    (jwks as { keys: Array<{ kid: string }> }).keys.some((key) => key.kid === (header as { kid: string }).kid),
    "the token's kid is not in the published JWKS",
  );
});

// The "noCredits" account: a second Supabase test user whose RevenueCat
// customer (named by that user's UUID) exists for this case and is
// deliberately left at its default zero SCAN balance (no dashboard grant
// needed). It replaces weekly-test-user-no-credits, created 2026-08-21.
// A tiny placeholder image is enough - spendCredit fails and the request
// short-circuits before Claude is ever called, so this costs nothing per run.
test("a customer with no SCAN credits gets 402 insufficient_credits, never reaches Claude", async () => {
  const result = await scan("noCredits", "truck_tag", "aGVsbG8=", "image/jpeg");

  assert.equal(result.status, 402);
  assert.deepEqual(result.body, {
    ok: false,
    code: "insufficient_credits",
    message: "Not enough scan credits.",
  });
});

// The "funded" account (the web external test user; its RevenueCat customer,
// named by its UUID, carries a real SCAN balance - replaces weekly-test-user,
// created 2026-08-21) exists so this file can exercise a
// real successful scan, not just the free insufficient-credits case
// above. Real cost: each of the next two cases charges one real SCAN
// credit and makes one real, billed Claude call (~$0.01 each) - unlike
// the case above, these are NOT free to re-run repeatedly. At 50
// starting credits and roughly one run per pickup of this tier, that's
// a long runway before a dashboard top-up is needed.
test("a real scan of a real truck tag succeeds and returns real extracted fields", async () => {
  const imageBase64 = readFileSync(path.join(REPO_ROOT, "ExampleDocs", "AddieTag.jpg"), "base64");

  const result = await scan("funded", "truck_tag", imageBase64, "image/jpeg");

  assert.equal(result.status, 200, `Expected 200, got ${result.status}: ${JSON.stringify(result.body)}`);
  const body = result.body as { ok: boolean; doc_type: string; fields: Record<string, unknown> };
  assert.equal(body.ok, true);
  assert.equal(body.doc_type, "truck_tag");
  assert.ok("manufacturer" in body.fields);
  assert.ok("gvwr_lb" in body.fields);
});

// A real, valid, real-world image (the WTWT logo already shipped in
// streamlit_app/assets/) that just isn't a truck tag. Claude's tool_use
// is *forced* (see claude.ts's tool_choice) - it can't refuse to call
// the extraction tool just because the image is irrelevant, so this
// still succeeds with (expected) empty/null fields, exactly like a real
// user accidentally photographing the wrong thing. Proves scan.ts's
// refund path is genuinely conditioned on extractFields throwing, not
// on "did we get anything useful back" - a wrong-but-readable photo is
// charged, not refunded.
test("a real scan of a valid but irrelevant image still succeeds and is charged, not refunded", async () => {
  const imageBase64 = readFileSync(
    path.join(REPO_ROOT, "streamlit_app", "assets", "wtwt_logo.png"),
    "base64",
  );

  const result = await scan("funded", "truck_tag", imageBase64, "image/png");

  assert.equal(result.status, 200, `Expected 200, got ${result.status}: ${JSON.stringify(result.body)}`);
  const body = result.body as { ok: boolean; doc_type: string };
  assert.equal(body.ok, true);
  assert.equal(body.doc_type, "truck_tag");
});

// Same logo file, deliberately truncated to an undecodable fragment -
// Anthropic's API rejects this at the request layer before any model
// call happens, so extractFields throws for a genuinely real reason
// (not a mocked one) and scan.ts's refund path fires for real. Free to
// run: a rejected, undecodable image is never billed. The response
// itself is the proof the refund succeeded - code "extraction_failed"
// only appears when refundCredit's own real call also succeeded (see
// scan.ts); "extraction_failed_no_refund" would mean the refund itself
// failed, a different, worse outcome this test would also catch.
test("a corrupted/undecodable image triggers the real refund path", async () => {
  const fullImage = readFileSync(path.join(REPO_ROOT, "streamlit_app", "assets", "wtwt_logo.png"));
  const truncated = Buffer.from(fullImage.subarray(0, 200)).toString("base64");

  const result = await scan("funded", "truck_tag", truncated, "image/png");

  assert.equal(result.status, 502, `Expected 502, got ${result.status}: ${JSON.stringify(result.body)}`);
  const body = result.body as { ok: boolean; code: string; message: string };
  assert.equal(body.ok, false);
  assert.equal(
    body.code,
    "extraction_failed",
    `Expected the refund to succeed (code "extraction_failed"), got "${body.code}": ${body.message}`,
  );
  assert.match(body.message, /credit refunded/i);
});
