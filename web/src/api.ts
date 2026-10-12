import type { ScaleTicketData, TrailerTagData, TruckTagData } from './types';
import { prepareImage } from './scanImage';
import { ScanError } from './scanError';

// What one scan needs besides the photo: the signed-in account's token, and an id the caller keeps
// the same across retries of one scan attempt (see scanAttempts.ts) so a retry is not charged twice.
export interface ScanContext {
  accessToken: string;
  clientRequestId: string;
}

type DocType = 'truck_tag' | 'trailer_tag' | 'scale_ticket';

// Messages for the failures the Scan service names (workers/scan-proxy README, "Errors"). Where a scan
// could not have been charged, or was refunded, the message says so.
const MESSAGES = {
  insufficient_credits: "You're out of scans.",
  unauthorized: 'Your sign-in has expired. Sign in again to scan.',
  auth_unavailable: "We couldn't verify your account just now, so nothing was scanned and you were not charged. Try again in a moment.",
  extraction_failed:
    "We couldn't read that photo, and your scan was refunded. Try a clearer photo, or type the numbers in yourself.",
  extraction_failed_no_refund:
    "We couldn't read that photo, and we couldn't refund your scan automatically. Trying this photo again will not charge you again. If it keeps happening, contact support.",
  billing_error: "We couldn't reach the payment service, so nothing was scanned and you were not charged. Try again in a moment.",
} as const;

const NO_ANSWER = "We didn't get a usable answer from the scan service. Try again; a retry is not charged twice.";

// Set VITE_SCAN_SERVICE_URL at build time to the Scan service's address (the Worker, no trailing path).
// Read on each call so a build without it fails the scan cleanly rather than at load.
function scanEndpoint(): string | null {
  const base = String(import.meta.env.VITE_SCAN_SERVICE_URL ?? '').replace(/\/+$/, '');
  return base ? `${base}/v1/scan` : null;
}

interface ScanBody {
  ok?: unknown;
  code?: unknown;
  message?: unknown;
  fields?: unknown;
}

async function scan<T>(docType: DocType, file: File, context: ScanContext): Promise<T> {
  const endpoint = scanEndpoint();
  if (!endpoint) throw new ScanError('unavailable', 'Scanning is not set up on this site. You can type the numbers in yourself.');

  const image = await prepareImage(file);

  let res: Response;
  try {
    res = await fetch(endpoint, {
      method: 'POST',
      headers: { Authorization: `Bearer ${context.accessToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        doc_type: docType,
        image_base64: image.base64,
        media_type: image.mediaType,
        client_request_id: context.clientRequestId,
      }),
    });
  } catch {
    throw new ScanError('network', "We couldn't reach the scan service. Check your connection and try again. A retry is not charged twice.", true);
  }

  const body: ScanBody | null = await res.json().catch(() => null);

  if (res.ok && body?.ok === true && typeof body.fields === 'object' && body.fields !== null) {
    return body.fields as T;
  }

  const code = typeof body?.code === 'string' ? body.code : null;
  if (code && Object.hasOwn(MESSAGES, code)) {
    const named = code as keyof typeof MESSAGES;
    // A retry of an unrefunded failure carries the same request id, which the service charges only once.
    throw new ScanError(named, MESSAGES[named], named === 'extraction_failed_no_refund');
  }
  if (code === 'bad_request') {
    const detail = typeof body?.message === 'string' ? ` (${body.message})` : '';
    throw new ScanError('bad_request', `The scan service could not accept that request${detail}.`);
  }
  // Not an answer the service gave (an error page from the edge, an unreadable success): it may have
  // charged, so the retry must carry the same request id.
  throw new ScanError('unknown', NO_ANSWER, true);
}

export function extractTruckTag(file: File, context: ScanContext): Promise<TruckTagData> {
  return scan('truck_tag', file, context);
}

export function extractTrailerTag(file: File, context: ScanContext): Promise<TrailerTagData> {
  return scan('trailer_tag', file, context);
}

export function extractScaleTicket(file: File, context: ScanContext): Promise<ScaleTicketData> {
  return scan('scale_ticket', file, context);
}
