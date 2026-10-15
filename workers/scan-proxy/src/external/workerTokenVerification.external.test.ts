// External suite (ADR-0008): the account-token verification surface - what the
// deployed Worker (auth.ts) accepts and refuses, and whether a real Supabase
// token and JWKS still look the way accountTokenContract.ts says they do.
// Run only via test-external.ps1 / `npm run test:external`. The
// "[worker-token-verification]" name tag is what the wrapper filters on.
//
// Every case is free: nothing is spent and Claude is never reached (a token
// that is refused stops at the 401, and the accepted-token case sends a body
// that is not JSON, so the Worker answers 400 before touching RevenueCat).
// Credentials are the `funded` Supabase test user's, from liveToken.ts; missing
// ones fail the run naming the variable, never skip.
import assert from "node:assert/strict";
import test from "node:test";
import {
  claimsViolation,
  headerViolation,
  jwksUrl,
  jwksViolation,
  usableKeys,
} from "../accountTokenContract.ts";
import { decodeJwt } from "../jwt.ts";
import { liveSupabaseUrl, signInTestAccount } from "../liveToken.ts";

const SCAN_ENDPOINT = "https://rigcheck-scan-proxy.wanderingtrailswaggingtails.workers.dev/v1/scan";

const UNAUTHORIZED = {
  ok: false,
  code: "unauthorized",
  message: "Missing or invalid account token.",
};

async function post(authorization: string | null, body: string) {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (authorization !== null) headers.Authorization = authorization;
  const response = await fetch(SCAN_ENDPOINT, {
    method: "POST",
    headers,
    body,
    signal: AbortSignal.timeout(20_000),
  });
  return { status: response.status, body: await response.json() };
}

// A well-formed scan body, so a refusal can only come from the token.
const SCAN_BODY = JSON.stringify({ doc_type: "truck_tag", image_base64: "aGVsbG8=", media_type: "image/jpeg" });

// The token with its signature's first character changed: still three
// well-formed parts and a published kid, but no longer signed by Supabase.
function withTamperedSignature(token: string): string {
  const [header, claims, signature] = token.split(".") as [string, string, string];
  const first = signature[0] === "A" ? "B" : "A";
  return `${header}.${claims}.${first}${signature.slice(1)}`;
}

test("[worker-token-verification] reachable: a request with no account token gets 401 unauthorized from the deployed Worker", async () => {
  const result = await post(null, SCAN_BODY);

  assert.equal(result.status, 401);
  assert.deepEqual(result.body, UNAUTHORIZED);
});

test("[worker-token-verification] error contract: a Bearer value that is not a JWT gets the same 401", async () => {
  const result = await post("Bearer not-a-jwt", SCAN_BODY);

  assert.equal(result.status, 401);
  assert.deepEqual(result.body, UNAUTHORIZED);
});

test("[worker-token-verification] error contract: a real token with a tampered signature gets the same 401", async () => {
  const token = await signInTestAccount("funded");

  const result = await post(`Bearer ${withTamperedSignature(token)}`, SCAN_BODY);

  assert.equal(result.status, 401);
  assert.deepEqual(result.body, UNAUTHORIZED);
});

test("[worker-token-verification] journey: a real token is accepted by the deployed Worker, which goes on to read the body", async () => {
  const token = await signInTestAccount("funded");

  // Authentication runs before the body is read, so a body that is not JSON
  // gets the 400 only a verified token can reach - no credit is looked at.
  const result = await post(`Bearer ${token}`, "this is not json");

  assert.equal(result.status, 400, `Expected 400, got ${result.status}: ${JSON.stringify(result.body)}`);
  assert.deepEqual(result.body, { ok: false, code: "bad_request", message: "Body must be valid JSON." });
});

// Signs in a real Supabase user and checks the real token's header and claims,
// and the real JWKS document, against the same contract definition
// (accountTokenContract.ts) the Worker verifies and the offline fakes mint to
// - so Supabase changing its signing setup fails here, not in a user's scan.
test("[worker-token-verification] response shape: a real Supabase token and JWKS match the shared account-token contract", async () => {
  const supabaseUrl = liveSupabaseUrl();
  const token = await signInTestAccount("funded");
  const { header, claims } = decodeJwt(token);

  assert.equal(headerViolation(header), null);
  assert.equal(claimsViolation(claims, supabaseUrl, Math.floor(Date.now() / 1000)), null);

  const response = await fetch(jwksUrl(supabaseUrl), { signal: AbortSignal.timeout(15_000) });
  const jwks = await response.json();
  assert.equal(jwksViolation(jwks), null);
  const publishedKids = usableKeys(jwks).map((key) => key.kid);
  assert.ok(publishedKids.includes((header as { kid: string }).kid), "the token's kid is not in the published JWKS");
});
