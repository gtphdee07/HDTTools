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

// Per isolate: the last JWKS fetched for each Supabase project URL.
const jwksCache = new Map<string, JwksDocument>();

export function clearJwksCache(): void {
  jwksCache.clear();
}

async function loadJwks(url: string, deps: AuthDeps): Promise<JwksDocument> {
  const doc = await deps.fetchJwks(url);
  const violation = jwksViolation(doc);
  if (violation) throw new Error(violation);
  const keys = { keys: usableKeys(doc) };
  jwksCache.set(url, keys);
  return keys;
}

// The cached key set normally holds the key; an unknown kid means Supabase
// may have rotated its keys, so re-fetch once before giving up.
async function findKey(url: string, kid: string, deps: AuthDeps): Promise<AccountJwk | undefined> {
  const cached = jwksCache.get(url);
  const fromCache = cached?.keys.find((key) => key.kid === kid);
  if (fromCache) return fromCache;
  return (await loadJwks(url, deps)).keys.find((key) => key.kid === kid);
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
