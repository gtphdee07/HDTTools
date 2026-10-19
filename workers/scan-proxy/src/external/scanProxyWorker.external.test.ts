// External suite (ADR-0008): the deployed scan Worker's own contract - the real
// `POST /v1/scan` at its workers.dev URL, the one Android's ScanApiClient and
// Web call. Run only via test-external.ps1 / `npm run test:external`. The
// "[scan-proxy-worker]" name tag is what the wrapper filters on.
//
// The suite tests whatever is deployed. It does not deploy: after a change to
// the Worker's source or wrangler.toml, `npm run deploy` first (the Weekly
// suite's pretest does that for itself).
//
// Cost: exactly one real, billed Claude call and one SCAN credit - the
// journey that spends (matching scripts/external_manifest/surfaces/
// scan-proxy-worker.json's max_paid_calls, enforced by scripts/
// external_wrapper.py). Every other case is free: bad requests stop at the
// 400, the no-credit account stops at the 402, and a truncated image is
// refused by Anthropic before any model call, so its credit is refunded.
//
// Missing credentials fail the run naming what is missing: REVENUECAT_SECRET_KEY
// here (to read the balances that prove the spend and the refund), and the
// Supabase test users' variables via liveToken.ts. Skipping is only ever the
// wrapper's explicit -Skip, which records `skipped` and leaves the surface stale.
//
// Not repeated here: the 401 for a missing, malformed or tampered account
// token is the [worker-token-verification] surface's, and the Android release
// gate waits on both.
import assert from "node:assert/strict";
import { Buffer } from "node:buffer";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { DOC_TYPE_CONFIG } from "../docTypes.ts";
import { signInTestAccount, subjectOf } from "../liveToken.ts";

const REVENUECAT_SECRET_KEY = process.env.REVENUECAT_SECRET_KEY;
if (!REVENUECAT_SECRET_KEY) {
  throw new Error(
    "External test credentials missing: REVENUECAT_SECRET_KEY is not set in the environment " +
      "(a v2 key with Customer information read).",
  );
}

const WORKER_URL = "https://rigcheck-scan-proxy.wanderingtrailswaggingtails.workers.dev";
const SCAN_ENDPOINT = `${WORKER_URL}/v1/scan`;
const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");

// Same non-secret values as wrangler.toml's [vars].
const REVENUECAT_PROJECT_ID = "proj07f52826";
const SCAN_CURRENCY = "SCAN";

const freshId = () => `external-test-${crypto.randomUUID()}`;

async function scan(token: string | null, body: unknown) {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token !== null) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(SCAN_ENDPOINT, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(60_000),
  });
  return { status: response.status, body: (await response.json()) as unknown };
}

// The account's SCAN balance straight from RevenueCat; the Worker has no balance route.
async function balanceOf(token: string): Promise<number> {
  const customer = encodeURIComponent(subjectOf(token));
  const response = await fetch(
    `https://api.revenuecat.com/v2/projects/${REVENUECAT_PROJECT_ID}/customers/${customer}/virtual_currencies`,
    { headers: { Authorization: `Bearer ${REVENUECAT_SECRET_KEY}` }, signal: AbortSignal.timeout(15_000) },
  );
  const body = (await response.json().catch(() => null)) as { items?: { currency_code: string; balance: number }[] } | null;
  assert.equal(
    response.status,
    200,
    `RevenueCat balance read failed (${response.status}) - check REVENUECAT_SECRET_KEY's permissions and that this test account's customer exists`,
  );
  return body?.items?.find((item) => item.currency_code === SCAN_CURRENCY)?.balance ?? 0;
}

const BAD_REQUEST_CODE = "bad_request";

test("[scan-proxy-worker] reachable: the CORS preflight Web's browser sends is answered 204 with the allowed method and headers", async () => {
  const response = await fetch(SCAN_ENDPOINT, { method: "OPTIONS", signal: AbortSignal.timeout(20_000) });

  assert.equal(response.status, 204);
  assert.equal(response.headers.get("access-control-allow-origin"), "*");
  assert.match(response.headers.get("access-control-allow-methods") ?? "", /POST/);
  const allowedHeaders = response.headers.get("access-control-allow-headers") ?? "";
  assert.match(allowedHeaders, /Authorization/);
  assert.match(allowedHeaders, /Content-Type/);
});

test("[scan-proxy-worker] error contract: any other route or method is a 404 not_found envelope", async () => {
  const expected = { ok: false, code: "not_found", message: "POST /v1/scan only." };

  const wrongMethod = await fetch(SCAN_ENDPOINT, { method: "GET", signal: AbortSignal.timeout(20_000) });
  assert.equal(wrongMethod.status, 404);
  assert.deepEqual(await wrongMethod.json(), expected);

  const wrongPath = await fetch(`${WORKER_URL}/v1/other`, { method: "POST", signal: AbortSignal.timeout(20_000) });
  assert.equal(wrongPath.status, 404);
  assert.deepEqual(await wrongPath.json(), expected);
});

test("[scan-proxy-worker] reachable and authenticated: a signed-in request gets past the token check to request validation", async () => {
  const token = await signInTestAccount("funded");

  const result = await scan(token, {});

  assert.equal(result.status, 400, `Expected 400, got ${result.status}: ${JSON.stringify(result.body)}`);
  assert.equal((result.body as { code?: string }).code, BAD_REQUEST_CODE);
});

test("[scan-proxy-worker] error contract: each bad request is a 400 bad_request naming the problem, and spends nothing", async () => {
  const token = await signInTestAccount("funded");
  const before = await balanceOf(token);
  const image = { image_base64: "aGVsbG8=", media_type: "image/jpeg" };
  const cases: { label: string; body: unknown; message: RegExp }[] = [
    { label: "not an object", body: null, message: /Body must be a JSON object/ },
    { label: "unknown doc_type", body: { ...image, doc_type: "driver_license" }, message: /doc_type must be one of truck_tag, trailer_tag, scale_ticket/ },
    { label: "no image", body: { doc_type: "truck_tag" }, message: /image_base64 is required/ },
    { label: "unsupported media_type", body: { ...image, doc_type: "truck_tag", media_type: "image/bmp" }, message: /media_type must be/ },
    { label: "malformed client_request_id", body: { ...image, doc_type: "truck_tag", client_request_id: "has spaces!" }, message: /client_request_id must be/ },
  ];

  for (const { label, body, message } of cases) {
    const result = await scan(token, body);
    assert.equal(result.status, 400, `${label}: expected 400, got ${result.status}: ${JSON.stringify(result.body)}`);
    const envelope = result.body as { ok?: boolean; code?: string; message?: string };
    assert.equal(envelope.ok, false, label);
    assert.equal(envelope.code, BAD_REQUEST_CODE, label);
    assert.match(envelope.message ?? "", message, label);
  }

  assert.equal(await balanceOf(token), before, "a rejected request must not change the balance");
});

test("[scan-proxy-worker] error contract: an account with no SCAN credits gets 402 insufficient_credits and stays at zero", async () => {
  const token = await signInTestAccount("noCredits");

  const result = await scan(token, { doc_type: "truck_tag", image_base64: "aGVsbG8=", media_type: "image/jpeg" });

  assert.equal(result.status, 402, `Expected 402, got ${result.status}: ${JSON.stringify(result.body)}`);
  assert.deepEqual(result.body, { ok: false, code: "insufficient_credits", message: "Not enough scan credits." });
  assert.equal(await balanceOf(token), 0);
});

// The one paid case. A real truck tag through the deployed Worker proves two
// depths from the same billed call: the success body is the shape clients
// parse, and the scan spent exactly one credit.
test("[scan-proxy-worker] response shape and journey: a real scan returns the contract body and spends exactly one credit", async () => {
  const token = await signInTestAccount("funded");
  const before = await balanceOf(token);
  assert.ok(before >= 1, `the funded test account holds ${before} SCAN credits; top it up in the RevenueCat dashboard`);
  const image = readFileSync(path.join(REPO_ROOT, "ExampleDocs", "AddieTag.jpg"), "base64");

  const result = await scan(token, {
    doc_type: "truck_tag",
    image_base64: image,
    media_type: "image/jpeg",
    client_request_id: freshId(),
  });

  assert.equal(result.status, 200, `Expected 200, got ${result.status}: ${JSON.stringify(result.body)}`);
  const body = result.body as { ok: unknown; doc_type: unknown; fields: Record<string, unknown> };
  assert.deepEqual(Object.keys(body).sort(), ["doc_type", "fields", "ok"]);
  assert.equal(body.ok, true);
  assert.equal(body.doc_type, "truck_tag");
  for (const field of DOC_TYPE_CONFIG.truck_tag.schema.required ?? []) {
    assert.ok(field in body.fields, `the scan result is missing the required field ${field}`);
  }
  // The tire entries are always objects, so only the scalar fields show the image was actually read.
  const readScalars = Object.values(body.fields).filter((value) => value !== null && typeof value !== "object");
  assert.ok(readScalars.length > 0, "every scalar field came back empty");

  assert.equal(await balanceOf(token), before - 1, "a delivered scan must cost exactly one credit");
});

test("[scan-proxy-worker] journey: a scan that cannot be read is a 502 extraction_failed, and its credit is refunded", async () => {
  const token = await signInTestAccount("funded");
  const before = await balanceOf(token);
  const logo = readFileSync(path.join(REPO_ROOT, "streamlit_app", "assets", "wtwt_logo.png"));
  const truncated = Buffer.from(logo.subarray(0, 200)).toString("base64");

  const result = await scan(token, {
    doc_type: "truck_tag",
    image_base64: truncated,
    media_type: "image/png",
    client_request_id: freshId(),
  });

  assert.equal(result.status, 502, `Expected 502, got ${result.status}: ${JSON.stringify(result.body)}`);
  assert.deepEqual(result.body, {
    ok: false,
    code: "extraction_failed",
    message: "Could not read the image. Credit refunded.",
  });
  assert.equal(await balanceOf(token), before, "the failed scan's credit must come back");
});
