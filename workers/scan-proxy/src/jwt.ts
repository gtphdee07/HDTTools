// Reading the parts of a compact JWT (base64url JSON header.claims.signature).
// Shared by the Worker's verifier, the test fixtures and the live suites so
// there is one decoder, using only APIs available in Workers and Node alike.

export function base64urlToBytes(value: string): Uint8Array {
  if (!/^[A-Za-z0-9_-]*$/.test(value)) throw new Error("not base64url");
  const base64 = value.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, "="));
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

// The JSON value of one base64url part, or undefined if it isn't valid JSON.
export function decodeJwtPart(part: string | undefined): unknown {
  if (!part) return undefined;
  try {
    return JSON.parse(new TextDecoder().decode(base64urlToBytes(part)));
  } catch {
    return undefined;
  }
}

// The decoded header and claims of a token (undefined for an unreadable part).
export function decodeJwt(token: string): { header: unknown; claims: unknown } {
  const [header, claims] = token.split(".");
  return { header: decodeJwtPart(header), claims: decodeJwtPart(claims) };
}
