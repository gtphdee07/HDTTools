// Offline stand-in for Supabase's token signing: a locally generated ES256
// key pair, a JWKS document for it, and a signer for tokens whose header and
// claims default to exactly what accountTokenContract.ts describes. Tests
// override single fields to build each kind of bad token.
import { Buffer } from "node:buffer";
import {
  ACCOUNT_TOKEN_ALG,
  ACCOUNT_TOKEN_AUDIENCE,
  accountTokenIssuer,
  type AccountJwk,
  type AccountTokenClaims,
  type AccountTokenHeader,
  type JwksDocument,
} from "./accountTokenContract.ts";
import { decodeJwtPart } from "./jwt.ts";

export const TEST_SUPABASE_URL = "https://test-project.supabase.co";
const TEST_KID = "test-key-1";

export interface TestKeyPair {
  kid: string;
  privateKey: CryptoKey;
  jwk: AccountJwk;
}

export async function generateTestKeyPair(kid = TEST_KID): Promise<TestKeyPair> {
  const pair = (await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, [
    "sign",
    "verify",
  ])) as CryptoKeyPair;
  const exported = (await crypto.subtle.exportKey("jwk", pair.publicKey)) as { x: string; y: string };
  return { kid, privateKey: pair.privateKey, jwk: { kty: "EC", crv: "P-256", x: exported.x, y: exported.y, kid } };
}

export function jwksFor(...keys: TestKeyPair[]): JwksDocument {
  return { keys: keys.map((key) => key.jwk) };
}

function base64url(data: string | Uint8Array): string {
  return Buffer.from(data).toString("base64url");
}

export interface SignOptions {
  key: TestKeyPair;
  header?: Partial<AccountTokenHeader>;
  claims?: Record<string, unknown>;
  // Claim names to drop from the defaults (a missing claim, as opposed to a wrong one).
  omitClaims?: string[];
  supabaseUrl?: string;
  nowSeconds?: number;
}

function defaultClaims(userId: string, supabaseUrl = TEST_SUPABASE_URL, nowSeconds = Math.floor(Date.now() / 1000)): AccountTokenClaims {
  return {
    iss: accountTokenIssuer(supabaseUrl),
    aud: ACCOUNT_TOKEN_AUDIENCE,
    sub: userId,
    exp: nowSeconds + 3600,
  };
}

// Signs with ES256 (WebCrypto's ECDSA output is already the raw r||s form JWTs use).
export async function signToken(userId: string, options: SignOptions): Promise<string> {
  const claims: Record<string, unknown> = {
    ...defaultClaims(userId, options.supabaseUrl, options.nowSeconds),
    ...options.claims,
  };
  for (const name of options.omitClaims ?? []) delete claims[name];
  const header = { alg: ACCOUNT_TOKEN_ALG, kid: options.key.kid, typ: "JWT", ...options.header };
  const signingInput = `${base64url(JSON.stringify(header))}.${base64url(JSON.stringify(claims))}`;
  const signature = await crypto.subtle.sign(
    { name: "ECDSA", hash: "SHA-256" },
    options.key.privateKey,
    new TextEncoder().encode(signingInput),
  );
  return `${signingInput}.${base64url(new Uint8Array(signature))}`;
}

// A token with the given header/claims and an arbitrary (invalid) signature -
// for the algorithms that must be rejected before any signature check.
export function unsignedToken(header: Record<string, unknown>, claims: Record<string, unknown>, signature = ""): string {
  return `${base64url(JSON.stringify(header))}.${base64url(JSON.stringify(claims))}.${signature}`;
}

export function decodeTokenPart(token: string, index: 0 | 1): unknown {
  return decodeJwtPart(token.split(".")[index]);
}
