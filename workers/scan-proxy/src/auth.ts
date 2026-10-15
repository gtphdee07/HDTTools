// Verifies the Supabase access token ("account token") a scan request carries,
// and says which account it belongs to. Supabase signs with ES256; the public
// key comes from its JWKS endpoint, so there is no shared secret to hold.
import {
  ACCOUNT_TOKEN_ALG,
  claimsViolation,
  headerViolation,
  jwksUrl,
  jwksViolation,
  usableKeys,
  type AccountJwk,
  type JwksDocument,
} from "./accountTokenContract.ts";
import { base64urlToBytes, decodeJwtPart } from "./jwt.ts";
import type { Env } from "./types.ts";

export type AuthResult =
  | { ok: true; userId: string }
  | { ok: false; reason: string; unavailable?: boolean };

export interface AuthDeps {
  fetchJwks: (url: string) => Promise<unknown>;
  nowSeconds: () => number;
}

const JWKS_TIMEOUT_MS = 5_000;

const defaultAuthDeps: AuthDeps = {
  fetchJwks: async (url) => {
    const res = await fetch(url, { signal: AbortSignal.timeout(JWKS_TIMEOUT_MS) });
    if (!res.ok) throw new Error(`JWKS endpoint returned ${res.status}`);
    return res.json();
  },
  nowSeconds: () => Math.floor(Date.now() / 1000),
};

// A JWKS fetch is started at most once per cooldown window per Supabase
// project, so a caller sending random kids cannot make the Worker hammer
// Supabase. A key published inside the window is picked up once it ends.
export const JWKS_REFETCH_COOLDOWN_SECONDS = 30;

// A cached key set is trusted for at most this long after it was fetched, so a
// key Supabase withdraws cannot stay accepted until the isolate is recycled.
// Past it the keys are re-fetched; if that fails the request is 503, never
// verified against stale keys.
export const JWKS_MAX_AGE_SECONDS = 10 * 60;

interface JwksState {
  // The last key set fetched successfully; past the max age it is no longer trusted.
  cached?: { doc: JwksDocument; fetchedAt: number };
  // When the latest fetch attempt (successful or not) was started.
  lastAttemptAt?: number;
  // The fetch running right now; requests arriving meanwhile wait for it.
  inFlight?: Promise<JwksDocument>;
}

// Per isolate: what was last learned from each Supabase project URL.
const jwksState = new Map<string, JwksState>();

export function clearJwksCache(): void {
  jwksState.clear();
}

async function loadJwks(url: string, state: JwksState, deps: AuthDeps): Promise<JwksDocument> {
  const doc = await deps.fetchJwks(url);
  const violation = jwksViolation(doc);
  if (violation) throw new Error(violation);
  const keys = { keys: usableKeys(doc) };
  state.cached = { doc: keys, fetchedAt: deps.nowSeconds() };
  return keys;
}

// Starts a fetch and records it; the cooldown is measured from this moment,
// not from when the fetch ends.
function startLoad(url: string, state: JwksState, deps: AuthDeps): Promise<JwksDocument> {
  state.lastAttemptAt = deps.nowSeconds();
  const loading = loadJwks(url, state, deps).finally(() => {
    state.inFlight = undefined;
  });
  state.inFlight = loading;
  return loading;
}

// The cached key set, unless it is older than the max age.
function trustedKeys(state: JwksState, now: number): JwksDocument | undefined {
  const { cached } = state;
  return cached && now - cached.fetchedAt < JWKS_MAX_AGE_SECONDS ? cached.doc : undefined;
}

const withKid = (doc: JwksDocument | undefined, kid: string) => doc?.keys.find((key) => key.kid === kid);

// The cached key set normally holds the key; an unknown kid means Supabase
// may have rotated its keys, so re-fetch before giving up - unless a fetch
// was started within the cooldown, in which case the kid is simply unknown.
async function findKey(url: string, kid: string, deps: AuthDeps): Promise<AccountJwk | undefined> {
  let state = jwksState.get(url);
  if (!state) jwksState.set(url, (state = {}));
  const now = deps.nowSeconds();
  const trusted = trustedKeys(state, now);
  const fromCache = withKid(trusted, kid);
  if (fromCache) return fromCache;
  if (state.inFlight) return withKid(await state.inFlight, kid);
  const inCooldown = state.lastAttemptAt !== undefined && now - state.lastAttemptAt < JWKS_REFETCH_COOLDOWN_SECONDS;
  if (inCooldown) {
    // No trusted keys to say the kid is unknown with: the service can't verify right now.
    if (!trusted) throw new Error("no trusted JWKS, and the last fetch was too recent to retry");
    return undefined;
  }
  return withKid(await startLoad(url, state, deps), kid);
}

async function signatureIsValid(key: AccountJwk, signingInput: string, signature: string): Promise<boolean> {
  try {
    const publicKey = await crypto.subtle.importKey(
      "jwk",
      { kty: key.kty, crv: key.crv, x: key.x, y: key.y },
      { name: "ECDSA", namedCurve: "P-256" },
      false,
      ["verify"],
    );
    return await crypto.subtle.verify(
      { name: "ECDSA", hash: "SHA-256" },
      publicKey,
      base64urlToBytes(signature),
      new TextEncoder().encode(signingInput),
    );
  } catch {
    return false;
  }
}

export async function verifyAccountToken(
  env: Env,
  authorizationHeader: string | null,
  deps: AuthDeps = defaultAuthDeps,
): Promise<AuthResult> {
  const token = /^Bearer +(\S+)$/i.exec(authorizationHeader ?? "")?.[1];
  if (!token) return { ok: false, reason: "no Bearer token" };

  const parts = token.split(".");
  if (parts.length !== 3) return { ok: false, reason: "token is not a three-part JWT" };
  const [headerPart, claimsPart, signaturePart] = parts as [string, string, string];

  // The algorithm is checked against our own fixed value before any key is
  // looked up, so "none" and symmetric algorithms can never be negotiated.
  const header = decodeJwtPart(headerPart);
  const headerProblem = headerViolation(header);
  if (headerProblem) return { ok: false, reason: headerProblem };
  const kid = (header as { kid: string }).kid;

  if (!env.SUPABASE_URL) {
    console.error("SUPABASE_URL is not configured; cannot verify account tokens");
    return { ok: false, reason: "SUPABASE_URL not configured", unavailable: true };
  }

  let key: AccountJwk | undefined;
  try {
    key = await findKey(jwksUrl(env.SUPABASE_URL), kid, deps);
  } catch (err) {
    console.error("could not load the Supabase JWKS", err);
    return { ok: false, reason: "JWKS unavailable", unavailable: true };
  }
  if (!key) return { ok: false, reason: `no key with kid ${JSON.stringify(kid)}` };

  if (!(await signatureIsValid(key, `${headerPart}.${claimsPart}`, signaturePart))) {
    return { ok: false, reason: `bad ${ACCOUNT_TOKEN_ALG} signature` };
  }

  const claims = decodeJwtPart(claimsPart);
  const claimsProblem = claimsViolation(claims, env.SUPABASE_URL, deps.nowSeconds());
  if (claimsProblem) return { ok: false, reason: claimsProblem };

  return { ok: true, userId: (claims as { sub: string }).sub };
}
