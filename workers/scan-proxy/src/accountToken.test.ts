// Account-token verification, tested at the Worker's HTTP boundary (worker.fetch)
// with RevenueCat, Anthropic and Supabase's JWKS endpoint all faked behind one
// mocked global fetch. A locally generated ES256 key pair stands in for Supabase's.
import "./requireInstall.ts";
import assert from "node:assert/strict";
import test, { beforeEach, type TestContext } from "node:test";
import {
  claimsViolation,
  headerViolation,
  jwksUrl,
  jwksViolation,
  type JwksDocument,
} from "./accountTokenContract.ts";
import {
  decodeTokenPart,
  generateTestKeyPair,
  jwksFor,
  signToken,
  TEST_SUPABASE_URL,
  unsignedToken,
} from "./accountTokenFixtures.ts";
import { clearJwksCache } from "./auth.ts";
import worker from "./index.ts";
import type { Env } from "./types.ts";

const env: Env = {
  ANTHROPIC_API_KEY: "sk-ant-test",
  REVENUECAT_SECRET_KEY: "sk_test",
  REVENUECAT_PROJECT_ID: "proj",
  REVENUECAT_CURRENCY_CODE: "SCAN",
  SUPABASE_URL: TEST_SUPABASE_URL,
};

const USER_A = "11111111-1111-4111-8111-111111111111";
const USER_B = "22222222-2222-4222-8222-222222222222";

const goodKey = await generateTestKeyPair("good-key");
const otherKey = await generateTestKeyPair("good-key"); // same kid, different key material

const anthropicOk = {
  id: "msg_test",
  type: "message",
  role: "assistant",
  model: "claude-sonnet-5",
  content: [{ type: "tool_use", id: "toolu_1", name: "record_truck_tag", input: { manufacturer: "Ford" } }],
  stop_reason: "tool_use",
  stop_sequence: null,
  usage: { input_tokens: 1, output_tokens: 1 },
};

interface World {
  revenuecatCustomers: string[];
  anthropicCalls: () => number;
  jwksFetches: () => number;
  setJwks: (jwks: JwksDocument | "unreachable") => void;
}

function fakeWorld(t: TestContext, initialJwks: JwksDocument | "unreachable" = jwksFor(goodKey)): World {
  let jwks = initialJwks;
  let jwksFetches = 0;
  let anthropicCalls = 0;
  const revenuecatCustomers: string[] = [];
  t.mock.method(globalThis, "fetch", async (url: string | URL) => {
    const urlStr = String(url);
    if (urlStr === jwksUrl(TEST_SUPABASE_URL)) {
      jwksFetches++;
      if (jwks === "unreachable") throw new TypeError("fetch failed");
      return new Response(JSON.stringify(jwks), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    if (urlStr.includes("revenuecat.com")) {
      const customer = /\/customers\/([^/]+)\//.exec(urlStr)?.[1];
      revenuecatCustomers.push(decodeURIComponent(customer ?? ""));
      return new Response(JSON.stringify({ items: [{ balance: 4 }] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (urlStr.includes("anthropic.com")) {
      anthropicCalls++;
      return new Response(JSON.stringify(anthropicOk), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    throw new Error(`Unexpected fetch to ${urlStr}`);
  });
  return {
    revenuecatCustomers,
    anthropicCalls: () => anthropicCalls,
    jwksFetches: () => jwksFetches,
    setJwks: (next) => {
      jwks = next;
    },
  };
}

const body = { doc_type: "truck_tag", image_base64: "aGVsbG8=", media_type: "image/jpeg" };

function postScan(authorization: string | undefined, payload: unknown = body): Request {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (authorization !== undefined) headers.Authorization = authorization;
  return new Request("https://example.com/v1/scan", { method: "POST", headers, body: JSON.stringify(payload) });
}

const bearer = (token: string) => `Bearer ${token}`;
const nowSeconds = () => Math.floor(Date.now() / 1000);

// The JWKS cooldown and max cache age run off Date.now(), so those tests move a
// mocked clock instead of sleeping. Tokens stay valid for an hour, longer than any jump.
const COOLDOWN_MS = 30_000;
const MAX_CACHE_AGE_MS = 10 * 60_000;

function mockClock(t: TestContext): (ms: number) => void {
  t.mock.timers.enable({ apis: ["Date"], now: Date.now() });
  return (ms) => t.mock.timers.tick(ms);
}

const strayToken = async (kid: string) => bearer(await signToken(USER_A, { key: { ...goodKey, kid } }));

beforeEach(() => clearJwksCache());

async function assertUnauthorized(res: Response) {
  assert.equal(res.status, 401);
  assert.deepEqual(await res.json(), {
    ok: false,
    code: "unauthorized",
    message: "Missing or invalid account token.",
  });
}

const rejections: Array<[string, () => Promise<string | undefined>]> = [
  ["no Authorization header", async () => undefined],
  ["a non-Bearer scheme", async () => `Basic ${await signToken(USER_A, { key: goodKey })}`],
  ["a Bearer header with no token", async () => "Bearer "],
  ["a garbage token", async () => bearer("not-a-jwt")],
  ["a token with undecodable parts", async () => bearer("%%%.%%%.%%%")],
  [
    "an expired token",
    async () => bearer(await signToken(USER_A, { key: goodKey, claims: { exp: nowSeconds() - 3600 } })),
  ],
  [
    "a token signed by a different key under a known kid",
    async () => bearer(await signToken(USER_A, { key: otherKey })),
  ],
  [
    "a token whose payload was altered after signing",
    async () => {
      const token = await signToken(USER_A, { key: goodKey });
      const [header, , signature] = token.split(".");
      const forged = Buffer.from(JSON.stringify({ ...(decodeTokenPart(token, 1) as object), sub: USER_B })).toString("base64url");
      return bearer(`${header}.${forged}.${signature}`);
    },
  ],
  [
    "alg none",
    async () =>
      bearer(
        unsignedToken(
          { alg: "none", kid: goodKey.kid },
          { iss: `${TEST_SUPABASE_URL}/auth/v1`, aud: "authenticated", sub: USER_A, exp: nowSeconds() + 3600 },
        ),
      ),
  ],
  ["alg HS256", async () => bearer(await signToken(USER_A, { key: goodKey, header: { alg: "HS256" } }))],
  [
    "a token from a different issuer",
    async () => bearer(await signToken(USER_A, { key: goodKey, claims: { iss: "https://evil.supabase.co/auth/v1" } })),
  ],
  [
    "a token for a different audience",
    async () => bearer(await signToken(USER_A, { key: goodKey, claims: { aud: "anon" } })),
  ],
  ["a token with no sub", async () => bearer(await signToken(USER_A, { key: goodKey, omitClaims: ["sub"] }))],
  ["a token with a blank sub", async () => bearer(await signToken(USER_A, { key: goodKey, claims: { sub: " " } }))],
  ["a token with no exp", async () => bearer(await signToken(USER_A, { key: goodKey, omitClaims: ["exp"] }))],
  [
    "a token that is not valid yet (nbf in the future)",
    async () => bearer(await signToken(USER_A, { key: goodKey, claims: { nbf: nowSeconds() + 3600 } })),
  ],
  ["a token with a non-numeric nbf", async () => bearer(await signToken(USER_A, { key: goodKey, claims: { nbf: "soon" } }))],
  [
    "an anonymous user's token",
    async () => bearer(await signToken(USER_A, { key: goodKey, claims: { is_anonymous: true } })),
  ],
  [
    "a token naming a kid the JWKS doesn't have",
    async () => bearer(await signToken(USER_A, { key: { ...goodKey, kid: "unknown-kid" } })),
  ],
];

for (const [name, makeHeader] of rejections) {
  test(`rejects ${name} with 401 unauthorized, never touching RevenueCat or Anthropic`, async (t) => {
    const world = fakeWorld(t);
    const res = await worker.fetch(postScan(await makeHeader()), env);
    await assertUnauthorized(res);
    assert.deepEqual(world.revenuecatCustomers, []);
    assert.equal(world.anthropicCalls(), 0);
  });
}

test("[sanity] a valid token spends the token's account and returns extracted fields", async (t) => {
  const world = fakeWorld(t);
  const res = await worker.fetch(postScan(bearer(await signToken(USER_A, { key: goodKey }))), env);
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { ok: true, doc_type: "truck_tag", fields: { manufacturer: "Ford" } });
  assert.deepEqual(world.revenuecatCustomers, [USER_A]);
});

test("a body app_user_id naming another account is ignored; only the token's account is charged", async (t) => {
  const world = fakeWorld(t);
  const res = await worker.fetch(
    postScan(bearer(await signToken(USER_A, { key: goodKey })), { ...body, app_user_id: USER_B }),
    env,
  );
  assert.equal(res.status, 200);
  assert.deepEqual(world.revenuecatCustomers, [USER_A]);
});

test("a token is checked before the body: a bad token with a malformed body is 401, not 400", async (t) => {
  const world = fakeWorld(t);
  const res = await worker.fetch(
    new Request("https://example.com/v1/scan", { method: "POST", body: "{not json" }),
    env,
  );
  await assertUnauthorized(res);
  assert.deepEqual(world.revenuecatCustomers, []);
});

test("accepts a token whose aud is an array containing 'authenticated'", async (t) => {
  fakeWorld(t);
  const token = await signToken(USER_A, { key: goodKey, claims: { aud: ["authenticated", "other"] } });
  const res = await worker.fetch(postScan(bearer(token)), env);
  assert.equal(res.status, 200);
});

test("tolerates a few seconds of clock skew past exp", async (t) => {
  fakeWorld(t);
  const token = await signToken(USER_A, { key: goodKey, claims: { exp: nowSeconds() - 5 } });
  const res = await worker.fetch(postScan(bearer(token)), env);
  assert.equal(res.status, 200);
});

test("accepts a token whose nbf is already in the past", async (t) => {
  fakeWorld(t);
  const token = await signToken(USER_A, { key: goodKey, claims: { nbf: nowSeconds() - 60 } });
  assert.equal((await worker.fetch(postScan(bearer(token)), env)).status, 200);
});

test("a published key whose material can't be imported rejects the token (401), not a crash", async (t) => {
  const broken = { ...goodKey.jwk, x: "AAAA", y: "AAAA" };
  const world = fakeWorld(t, { keys: [broken] });
  await assertUnauthorized(await worker.fetch(postScan(bearer(await signToken(USER_A, { key: goodKey }))), env));
  assert.deepEqual(world.revenuecatCustomers, []);
});

test("an unreachable JWKS endpoint is 503 auth_unavailable (not 401), with no RevenueCat or Anthropic call", async (t) => {
  const world = fakeWorld(t, "unreachable");
  const res = await worker.fetch(postScan(bearer(await signToken(USER_A, { key: goodKey }))), env);
  assert.equal(res.status, 503);
  assert.equal(((await res.json()) as { code: string }).code, "auth_unavailable");
  assert.deepEqual(world.revenuecatCustomers, []);
  assert.equal(world.anthropicCalls(), 0);
});

test("keys of other types in the JWKS are skipped, not fatal", async (t) => {
  fakeWorld(t, { keys: [{ kty: "RSA", kid: "rsa-1", n: "x", e: "AQAB" }, goodKey.jwk] } as unknown as JwksDocument);
  const res = await worker.fetch(postScan(bearer(await signToken(USER_A, { key: goodKey }))), env);
  assert.equal(res.status, 200);
});

test("a JWKS with no usable EC key is 503 auth_unavailable", async (t) => {
  fakeWorld(t, { keys: [{ kty: "RSA", kid: "rsa-1" }] } as unknown as JwksDocument);
  const res = await worker.fetch(postScan(bearer(await signToken(USER_A, { key: goodKey }))), env);
  assert.equal(res.status, 503);
});

test("a JWKS response that isn't a valid key set is 503 auth_unavailable", async (t) => {
  fakeWorld(t, { keys: "nope" } as unknown as JwksDocument);
  const res = await worker.fetch(postScan(bearer(await signToken(USER_A, { key: goodKey }))), env);
  assert.equal(res.status, 503);
});

test("a missing SUPABASE_URL is 503 auth_unavailable, not a pass", async (t) => {
  const world = fakeWorld(t);
  const res = await worker.fetch(
    postScan(bearer(await signToken(USER_A, { key: goodKey }))),
    { ...env, SUPABASE_URL: "" },
  );
  assert.equal(res.status, 503);
  assert.deepEqual(world.revenuecatCustomers, []);
});

test("the JWKS is cached across requests", async (t) => {
  const world = fakeWorld(t);
  const token = bearer(await signToken(USER_A, { key: goodKey }));
  await worker.fetch(postScan(token), env);
  await worker.fetch(postScan(token), env);
  assert.equal(world.jwksFetches(), 1);
});

test("an unknown kid after the cooldown triggers one JWKS re-fetch, so a rotated key is picked up", async (t) => {
  const world = fakeWorld(t);
  const advance = mockClock(t);
  assert.equal((await worker.fetch(postScan(bearer(await signToken(USER_A, { key: goodKey }))), env)).status, 200);

  const rotated = await generateTestKeyPair("rotated-key");
  world.setJwks(jwksFor(rotated));
  advance(COOLDOWN_MS);
  const res = await worker.fetch(postScan(bearer(await signToken(USER_A, { key: rotated }))), env);
  assert.equal(res.status, 200);
  assert.equal(world.jwksFetches(), 2);
});

test("an unknown kid after the cooldown re-fetches the JWKS once, then is rejected", async (t) => {
  const world = fakeWorld(t);
  const advance = mockClock(t);
  await worker.fetch(postScan(bearer(await signToken(USER_A, { key: goodKey }))), env);
  assert.equal(world.jwksFetches(), 1);

  advance(COOLDOWN_MS);
  await assertUnauthorized(await worker.fetch(postScan(await strayToken("stray")), env));
  assert.equal(world.jwksFetches(), 2, "exactly one re-fetch for the unknown kid");
});

test("distinct unknown kids trigger at most one JWKS fetch per cooldown window", async (t) => {
  const world = fakeWorld(t);
  mockClock(t);
  await worker.fetch(postScan(bearer(await signToken(USER_A, { key: goodKey }))), env);
  assert.equal(world.jwksFetches(), 1);

  for (let i = 0; i < 5; i++) {
    await assertUnauthorized(await worker.fetch(postScan(await strayToken(`stray-${i}`)), env));
  }
  assert.equal(world.jwksFetches(), 1, "the first fetch is still inside the cooldown");
});

test("requests that arrive together share one JWKS fetch and are all verified against it", async (t) => {
  const world = fakeWorld(t);
  mockClock(t);
  const token = bearer(await signToken(USER_A, { key: goodKey }));

  const responses = await Promise.all([1, 2, 3, 4].map(() => worker.fetch(postScan(token), env)));
  assert.deepEqual(
    responses.map((res) => res.status),
    [200, 200, 200, 200],
  );
  assert.equal(world.jwksFetches(), 1);
});

test("a burst of unknown kids arriving together costs one JWKS fetch, and a key it publishes is accepted by all of them", async (t) => {
  const world = fakeWorld(t);
  const advance = mockClock(t);
  await worker.fetch(postScan(bearer(await signToken(USER_A, { key: goodKey }))), env);
  const rotated = await generateTestKeyPair("rotated-key");
  world.setJwks(jwksFor(rotated));
  advance(COOLDOWN_MS);

  const tokens = [
    bearer(await signToken(USER_A, { key: rotated })),
    bearer(await signToken(USER_A, { key: rotated })),
    await strayToken("stray-a"),
    await strayToken("stray-b"),
  ];
  const responses = await Promise.all(tokens.map((token) => worker.fetch(postScan(token), env)));
  assert.deepEqual(
    responses.map((res) => res.status),
    [200, 200, 401, 401],
  );
  assert.equal(world.jwksFetches(), 2, "one fetch at the start, one for the whole burst");
});

test("a failed JWKS fetch starts the cooldown: with no keys known, requests answer 503 without hitting Supabase again", async (t) => {
  const world = fakeWorld(t, "unreachable");
  const advance = mockClock(t);
  const token = bearer(await signToken(USER_A, { key: goodKey }));

  for (let i = 0; i < 3; i++) {
    const res = await worker.fetch(postScan(token), env);
    assert.equal(res.status, 503);
    assert.equal(((await res.json()) as { code: string }).code, "auth_unavailable");
  }
  assert.equal(world.jwksFetches(), 1);

  // Once the window is over and Supabase is back, the next request recovers.
  world.setJwks(jwksFor(goodKey));
  advance(COOLDOWN_MS);
  assert.equal((await worker.fetch(postScan(token), env)).status, 200);
  assert.equal(world.jwksFetches(), 2);
});

test("a failed re-fetch for an unknown kid is 503 once, then 401 inside the cooldown while the cached keys stand", async (t) => {
  const world = fakeWorld(t);
  const advance = mockClock(t);
  const good = bearer(await signToken(USER_A, { key: goodKey }));
  await worker.fetch(postScan(good), env);

  world.setJwks("unreachable");
  advance(COOLDOWN_MS);
  assert.equal((await worker.fetch(postScan(await strayToken("stray-1")), env)).status, 503);
  await assertUnauthorized(await worker.fetch(postScan(await strayToken("stray-2")), env));
  assert.equal(world.jwksFetches(), 2);
  assert.equal((await worker.fetch(postScan(good), env)).status, 200, "known keys still verify");
});

test("a known kid within the max cache age needs no fetch, however many cooldowns have passed", async (t) => {
  const world = fakeWorld(t);
  const advance = mockClock(t);
  const token = bearer(await signToken(USER_A, { key: goodKey }));
  await worker.fetch(postScan(token), env);

  advance(MAX_CACHE_AGE_MS - 1_000);
  assert.equal((await worker.fetch(postScan(token), env)).status, 200);
  assert.equal(world.jwksFetches(), 1);
});

test("cached keys expire after the max age: a still-published key is re-fetched and accepted", async (t) => {
  const world = fakeWorld(t);
  const advance = mockClock(t);
  const token = bearer(await signToken(USER_A, { key: goodKey }));
  await worker.fetch(postScan(token), env);

  advance(MAX_CACHE_AGE_MS);
  assert.equal((await worker.fetch(postScan(token), env)).status, 200);
  assert.equal(world.jwksFetches(), 2);
});

test("a key Supabase withdraws stops being trusted once the cached keys expire", async (t) => {
  const world = fakeWorld(t);
  const advance = mockClock(t);
  const token = bearer(await signToken(USER_A, { key: goodKey }));
  assert.equal((await worker.fetch(postScan(token), env)).status, 200);

  const replacement = await generateTestKeyPair("replacement-key");
  world.setJwks(jwksFor(replacement));
  assert.equal((await worker.fetch(postScan(token), env)).status, 200, "still trusted from cache before the max age");

  advance(MAX_CACHE_AGE_MS);
  await assertUnauthorized(await worker.fetch(postScan(token), env));
  assert.equal((await worker.fetch(postScan(bearer(await signToken(USER_A, { key: replacement }))), env)).status, 200);
});

test("expired cached keys are never used when the re-fetch fails: 503, and no further fetch inside the cooldown", async (t) => {
  const world = fakeWorld(t);
  const advance = mockClock(t);
  const token = bearer(await signToken(USER_A, { key: goodKey }));
  await worker.fetch(postScan(token), env);

  world.setJwks("unreachable");
  advance(MAX_CACHE_AGE_MS);
  for (let i = 0; i < 3; i++) {
    const res = await worker.fetch(postScan(token), env);
    assert.equal(res.status, 503);
    assert.equal(((await res.json()) as { code: string }).code, "auth_unavailable");
  }
  assert.equal(world.jwksFetches(), 2, "one failed re-fetch, then the cooldown holds");
  assert.deepEqual(world.revenuecatCustomers, [USER_A], "only the first, pre-expiry request spent anything");
});

test("the failure cause is not leaked in the 401 body", async (t) => {
  fakeWorld(t);
  const res = await worker.fetch(
    postScan(bearer(await signToken(USER_A, { key: goodKey, claims: { exp: nowSeconds() - 3600 } }))),
    env,
  );
  assert.doesNotMatch(JSON.stringify(await res.json()), /expired|signature/i);
});

test("the offline fixtures conform to the shared contract", async () => {
  const token = await signToken(USER_A, { key: goodKey });
  assert.equal(jwksViolation(jwksFor(goodKey)), null);
  assert.equal(headerViolation(decodeTokenPart(token, 0)), null);
  assert.equal(claimsViolation(decodeTokenPart(token, 1), TEST_SUPABASE_URL, nowSeconds()), null);
});
