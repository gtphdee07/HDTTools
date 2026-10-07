// The one definition of what an account token (a Supabase access token) and
// Supabase's JWKS document look like, as far as this Worker is concerned.
// auth.ts verifies against it, the offline token fixtures mint to it, and
// the live token check validates a real Supabase token against it - so the
// fake and the real thing can only drift apart loudly.

export const ACCOUNT_TOKEN_ALG = "ES256";
export const ACCOUNT_TOKEN_AUDIENCE = "authenticated";

// How far past `exp` (or ahead of `nbf`) a token is still accepted, for
// clock differences between Supabase and this Worker.
const CLOCK_SKEW_SECONDS = 30;

export interface AccountJwk {
  kty: "EC";
  crv: "P-256";
  x: string;
  y: string;
  kid: string;
}

export interface JwksDocument {
  keys: AccountJwk[];
}

export interface AccountTokenHeader {
  alg: string;
  kid: string;
}

export interface AccountTokenClaims {
  iss: string;
  aud: string | string[];
  sub: string;
  exp: number;
  nbf?: number;
  is_anonymous?: boolean;
}

function baseUrl(supabaseUrl: string): string {
  return supabaseUrl.replace(/\/+$/, "");
}

export function accountTokenIssuer(supabaseUrl: string): string {
  return `${baseUrl(supabaseUrl)}/auth/v1`;
}

export function jwksUrl(supabaseUrl: string): string {
  return `${accountTokenIssuer(supabaseUrl)}/.well-known/jwks.json`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

// Each check returns null when the value conforms, or a short description of
// what's wrong (logged server-side only - never sent to the caller).

function isUsableKey(key: unknown): key is AccountJwk {
  return (
    isRecord(key) &&
    key.kty === "EC" &&
    key.crv === "P-256" &&
    typeof key.x === "string" &&
    typeof key.y === "string" &&
    typeof key.kid === "string" &&
    key.kid !== ""
  );
}

// Keys of other types or shapes (Supabase may publish extras, e.g. during a
// rotation) are skipped, not fatal: the document only has to carry at least
// one usable EC P-256 key.
export function usableKeys(doc: unknown): AccountJwk[] {
  return isRecord(doc) && Array.isArray(doc.keys) ? doc.keys.filter(isUsableKey) : [];
}

export function jwksViolation(doc: unknown): string | null {
  if (!isRecord(doc) || !Array.isArray(doc.keys)) return "JWKS has no keys array";
  return usableKeys(doc).length > 0 ? null : "JWKS has no usable EC P-256 key";
}

export function headerViolation(header: unknown): string | null {
  if (!isRecord(header)) return "header is not an object";
  if (header.alg !== ACCOUNT_TOKEN_ALG) return `alg is ${JSON.stringify(header.alg)}, not ${ACCOUNT_TOKEN_ALG}`;
  if (typeof header.kid !== "string" || !header.kid) return "header lacks kid";
  return null;
}

export function claimsViolation(claims: unknown, supabaseUrl: string, nowSeconds: number): string | null {
  if (!isRecord(claims)) return "claims are not an object";
  if (typeof claims.exp !== "number") return "exp is missing or not a number";
  if (nowSeconds > claims.exp + CLOCK_SKEW_SECONDS) return "token expired";
  if (claims.nbf !== undefined && (typeof claims.nbf !== "number" || nowSeconds + CLOCK_SKEW_SECONDS < claims.nbf)) {
    return "token not yet valid";
  }
  if (claims.iss !== accountTokenIssuer(supabaseUrl)) return `iss is ${JSON.stringify(claims.iss)}`;
  const audiences = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
  if (!audiences.includes(ACCOUNT_TOKEN_AUDIENCE)) return `aud is ${JSON.stringify(claims.aud)}`;
  if (typeof claims.sub !== "string" || !claims.sub.trim()) return "sub is missing or blank";
  if (claims.is_anonymous === true) return "anonymous user";
  return null;
}
