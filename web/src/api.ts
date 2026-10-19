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
// could not have been charged, or was refunded, the message says so. The words are the "Scan outcomes" of
// workers/scan-proxy/CONTEXT.md, checked against test-vectors/scan_outcomes.json by scanOutcomes.test.ts.
const MESSAGES = {
  insufficient_credits: "You're out of scans. Nothing was used.",
  unauthorized: 'Your sign-in has expired. Nothing was used. Sign in again to scan.',
  auth_unavailable: "We couldn't verify your account just now. Nothing was used. Try again in a moment.",
  extraction_failed:
    "We couldn't read that photo, and your scan was refunded. Trying again uses another scan. A clearer photo may work better, or type the numbers in yourself.",
  extraction_failed_no_refund:
    "We couldn't read that photo, and we couldn't refund your scan automatically. Trying this photo again won't charge you again. If it keeps happening, contact support.",
  billing_error:
    "We couldn't confirm your scan balance with the payment service, so nothing was read. You may not have been charged. Try again in a moment; a retry is not charged twice.",
} as const;

// The service's own wording for what it disliked is for developers (e.g. which field), so it is not shown.
const BAD_REQUEST = "We couldn't use that photo. Nothing was used. Try a different photo, or type the numbers in yourself.";

const NO_ANSWER =
  "We didn't get a usable answer from the scan service. You may not have been charged. Try again; a retry is not charged twice.";

const NO_CONNECTION =
  "We couldn't reach the scan service. You may not have been charged. Check your connection and try again; a retry is not charged twice.";
const TOO_SLOW =
  'The scan service took too long to answer. You may not have been charged. Try again; a retry is not charged twice.';

// How long the whole exchange (sending the photo, waiting, reading the reply) may take before it is abandoned.
// While a scan is in flight the check cannot be left (#103), so without a limit a reply that never comes would
// lock the user in until the browser gives up, which can take minutes.
// 60 s, because it must outlast the Worker's own worst case or the app gives up on a scan the service would
// have delivered. That case is 45 s: the 5 s sign-in key fetch, the 10 s credit spend, one 20 s Claude attempt
// (the Worker does not retry it, #112) and 10 s more for a refund. It matches Android's 60 s read timeout.
// The arithmetic is in workers/scan-proxy/CONTEXT.md "Time limits", and a Worker test reads this value.
export const SCAN_TIMEOUT_MS = 60_000;

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
  if (!endpoint) throw new ScanError('unavailable', 'Scanning is not set up on this site. Nothing was used. You can type the numbers in yourself.');

  const image = await prepareImage(file);

  // The clock starts once the photo is ready and covers the reply body too. Running out of it is a lost
  // response, the same as a dropped connection: the service may have charged, so the retry keeps the request id.
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timedOut = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(new ScanError('timeout', TOO_SLOW, true));
      controller.abort();
    }, SCAN_TIMEOUT_MS);
  });

  const exchange = async () => {
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
        signal: controller.signal,
      });
    } catch {
      throw new ScanError('network', NO_CONNECTION, true);
    }
    const body: ScanBody | null = await res.json().catch(() => null);
    return { res, body };
  };

  let res: Response;
  let body: ScanBody | null;
  try {
    ({ res, body } = await Promise.race([exchange(), timedOut]));
  } finally {
    clearTimeout(timer);
  }

  if (res.ok && body?.ok === true && typeof body.fields === 'object' && body.fields !== null) {
    return body.fields as T;
  }

  const code = typeof body?.code === 'string' ? body.code : null;
  if (code && Object.hasOwn(MESSAGES, code)) {
    const named = code as keyof typeof MESSAGES;
    // A retry of an unrefunded failure, or of a balance check that gave no answer (the payment service may
    // have applied the charge before it timed out), carries the same request id, which is charged only once.
    throw new ScanError(named, MESSAGES[named], named === 'extraction_failed_no_refund' || named === 'billing_error');
  }
  if (code === 'bad_request') {
    throw new ScanError('bad_request', BAD_REQUEST);
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
