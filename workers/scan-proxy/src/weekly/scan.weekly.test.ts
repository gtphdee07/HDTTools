// Weekly tier — real, bounded network calls against the actual deployed
// Worker and RevenueCat, using dedicated disposable test customers (never
// smoke-test-user, which stays reserved for manual Android field testing).
// Deliberately kept out of `src/*.test.ts`'s glob (used by `npm test`/
// `npm run test:sanity`) by living in this subdirectory — run explicitly
// via `npm run test:weekly`, not on every commit. No local secrets
// needed here (unlike the Release tier) - every case below only ever
// talks to the public /v1/scan endpoint, the same way a real client does.
import assert from "node:assert/strict";
import { Buffer } from "node:buffer";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const SCAN_ENDPOINT = "https://rigcheck-scan-proxy.wanderingtrailswaggingtails.workers.dev/v1/scan";
const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");

async function scan(appUserId: string, docType: string, imageBase64: string, mediaType: string) {
  const response = await fetch(SCAN_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      app_user_id: appUserId,
      doc_type: docType,
      image_base64: imageBase64,
      media_type: mediaType,
    }),
  });
  return { status: response.status, body: await response.json() };
}

// weekly-test-user-no-credits: created 2026-08-21 specifically for this
// case, deliberately left at its default zero SCAN balance (no dashboard
// grant needed - RevenueCat.entitlement_check has nothing to do with this
// path either; see NEXT_STEPS.md for why an entitlement-based test
// customer wouldn't exercise any real logic as of this writing). A tiny
// placeholder image is enough - spendCredit fails and the request short-
// circuits before Claude is ever called, so this costs nothing per run.
test("a customer with no SCAN credits gets 402 insufficient_credits, never reaches Claude", async () => {
  const result = await scan("weekly-test-user-no-credits", "truck_tag", "aGVsbG8=", "image/jpeg");

  assert.equal(result.status, 402);
  assert.deepEqual(result.body, {
    ok: false,
    code: "insufficient_credits",
    message: "Not enough scan credits.",
  });
});

// weekly-test-user: created 2026-08-21 with a real SCAN balance (see
// NEXT_STEPS.md) specifically so this file could eventually exercise a
// real successful scan, not just the free insufficient-credits case
// above. Real cost: each of the next two cases charges one real SCAN
// credit and makes one real, billed Claude call (~$0.01 each) - unlike
// the case above, these are NOT free to re-run repeatedly. At 50
// starting credits and roughly one run per pickup of this tier, that's
// a long runway before a dashboard top-up is needed.
test("a real scan of a real truck tag succeeds and returns real extracted fields", async () => {
  const imageBase64 = readFileSync(path.join(REPO_ROOT, "ExampleDocs", "AddieTag.jpg"), "base64");

  const result = await scan("weekly-test-user", "truck_tag", imageBase64, "image/jpeg");

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

  const result = await scan("weekly-test-user", "truck_tag", imageBase64, "image/png");

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

  const result = await scan("weekly-test-user", "truck_tag", truncated, "image/png");

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
