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
  | 'unknown';

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
}
