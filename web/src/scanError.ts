export type ScanErrorCode =
  | 'insufficient_credits'
  | 'unauthorized'
  | 'auth_unavailable'
  | 'extraction_failed'
  // The scan was charged, nothing was read, and the automatic refund also failed.
  | 'extraction_failed_no_refund'
  | 'billing_error'
  | 'bad_request'
  // The photo itself cannot be sent (a format or size the Scan service cannot take); checked before any request.
  | 'bad_photo'
  // No scan service address in this build.
  | 'unavailable'
  // The request got no usable answer: no connection, or a reply that is not the service's.
  | 'network'
  // The service did not finish answering within the time limit (api.ts); the request was abandoned.
  | 'timeout'
  // The service delivered and charged, but the answer has no weight in it (the tow-vehicle-only ticket).
  | 'no_weight'
  | 'unknown';

// A delivered stand-alone ticket answer with no weight in it: the Scan was charged and is not refunded.
export const NO_WEIGHT_MESSAGE =
  "We read the ticket but couldn't find a weight. That Scan was used, and trying again uses another. Type the weight in, or choose a different photo.";

// Outcomes where sending the same photo again cannot help: a delivered answer (a retry is another paid Scan
// that reads the same), a refusal that repeats, or a photo that cannot be sent. After these the next step is
// a different photo, signing in, or typing the numbers in.
const NO_TRY_AGAIN: ReadonlySet<ScanErrorCode> = new Set<ScanErrorCode>([
  'no_weight',
  'unauthorized',
  'bad_request',
  'bad_photo',
  'insufficient_credits',
  'unavailable',
]);

// Of the failures a photo can be sent into, the ones where the way forward is a different photo (or, for
// 'unauthorized', signing in first) rather than the same one again.
const NEEDS_DIFFERENT_PHOTO: ReadonlySet<ScanErrorCode> = new Set<ScanErrorCode>(['unauthorized', 'bad_request', 'bad_photo']);
// The ones where the photo itself is what the service or the browser would not take.
const PHOTO_REFUSED: ReadonlySet<ScanErrorCode> = new Set<ScanErrorCode>(['bad_request', 'bad_photo']);

export const needsDifferentPhoto = (code: ScanErrorCode) => NEEDS_DIFFERENT_PHOTO.has(code);
export const photoRefused = (code: ScanErrorCode) => PHOTO_REFUSED.has(code);

// A scan that did not deliver fields. `message` is written for the user.
export class ScanError extends Error {
  readonly code: ScanErrorCode;
  // True when the request got no usable answer, so the service may or may not have charged for it (or it
  // charged and could not refund). A retry of the same photo must then send the same request id, which is what
  // keeps the charge to one. Any other answer from the service, success or a named failure, settles the attempt.
  readonly lostResponse: boolean;

  constructor(code: ScanErrorCode, message: string, lostResponse = false) {
    super(message);
    this.name = 'ScanError';
    this.code = code;
    this.lostResponse = lostResponse;
  }

  // Whether re-sending the same photo is worth offering.
  get canTryAgain(): boolean {
    return !NO_TRY_AGAIN.has(this.code);
  }
}
