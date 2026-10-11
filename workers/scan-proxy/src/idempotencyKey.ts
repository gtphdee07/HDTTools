// The RevenueCat Idempotency-Key for a Scan's Spend (the Refund's key is this
// plus "-refund", added in revenuecat.ts). RevenueCat replays a repeated key
// without charging again, so whatever a caller can vary freely while the key
// stays the same is something they get for free. The key therefore binds
// everything that makes a Scan *this* Scan: the verified account, the
// document type, the media type and the image itself, plus the caller's id
// (which keeps an honest retry of the same request on the same key).
//
// The result is a fixed-width lowercase-hex SHA-256, so it cannot contain the
// "-refund" suffix and no caller-chosen id can steer one request's key onto
// another request's spend or refund key.
import type { ScanRequest } from "./request.ts";

const encoder = new TextEncoder();

async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(text));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

// requestId is the caller's client_request_id, or a fresh random id when the
// caller sent none (every such request is then its own Scan, as before).
export async function scanIdempotencyKey(
  userId: string,
  request: ScanRequest,
  requestId: string,
): Promise<string> {
  const imageHash = await sha256Hex(request.image_base64);
  // JSON array: unambiguous, so no field can bleed into its neighbour.
  return sha256Hex(
    JSON.stringify(["scan-spend-v1", userId, request.doc_type, request.media_type, imageHash, requestId]),
  );
}
