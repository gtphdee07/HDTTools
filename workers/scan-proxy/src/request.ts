import type { DocType } from "./docTypes.ts";
import type { MediaType } from "./types.ts";

export const DOC_TYPES = new Set<DocType>(["truck_tag", "trailer_tag", "scale_ticket"]);
export const MEDIA_TYPES = new Set<MediaType>(["image/jpeg", "image/png", "image/webp", "image/gif"]);

export interface ScanRequest {
  app_user_id: string;
  doc_type: DocType;
  image_base64: string;
  media_type: MediaType;
  // Client-generated, stable across retries of the same logical scan
  // attempt - used as the RevenueCat idempotency key so a retry after a
  // lost/timed-out response doesn't spend a second credit. Optional and
  // backward compatible: omitted (e.g. by an already-shipped app build)
  // falls back to a fresh random key per request, today's behavior.
  client_request_id?: string;
}

// Returns the parsed request, or an error message string describing what's wrong.
export function parseScanRequest(payload: unknown): ScanRequest | string {
  if (typeof payload !== "object" || payload === null) {
    return "Body must be a JSON object.";
  }
  const body = payload as Record<string, unknown>;

  const appUserId = body.app_user_id;
  if (typeof appUserId !== "string" || !appUserId.trim()) {
    return "app_user_id is required.";
  }

  const docType = body.doc_type;
  if (typeof docType !== "string" || !DOC_TYPES.has(docType as DocType)) {
    return "doc_type must be one of truck_tag, trailer_tag, scale_ticket.";
  }

  const imageBase64 = body.image_base64;
  if (typeof imageBase64 !== "string" || !imageBase64) {
    return "image_base64 is required.";
  }

  const mediaType = body.media_type ?? "image/jpeg";
  if (typeof mediaType !== "string" || !MEDIA_TYPES.has(mediaType as MediaType)) {
    return "media_type must be image/jpeg, image/png, image/webp, or image/gif.";
  }

  const clientRequestId = body.client_request_id ?? undefined;
  if (clientRequestId !== undefined && (typeof clientRequestId !== "string" || !clientRequestId.trim())) {
    return "client_request_id must be a non-empty string when present.";
  }

  const parsed: ScanRequest = {
    app_user_id: appUserId,
    doc_type: docType as DocType,
    image_base64: imageBase64,
    media_type: mediaType as MediaType,
  };
  if (typeof clientRequestId === "string") {
    parsed.client_request_id = clientRequestId;
  }
  return parsed;
}
