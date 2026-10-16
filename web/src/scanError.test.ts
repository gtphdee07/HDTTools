import { describe, expect, it } from 'vitest';
import { ScanError } from './scanError';
import type { ScanErrorCode } from './scanError';

// Whether re-sending the same photo can help is a fact about the outcome, written once here (see the
// "Scan did not deliver" research, R3): a retry helps only where the service did not read the photo
// for lack of a working attempt, never after a delivered answer or a refusal that repeats.

describe('ScanError.canTryAgain', () => {
  const tryAgain: ScanErrorCode[] = [
    'auth_unavailable',
    'extraction_failed',
    'extraction_failed_no_refund',
    'billing_error',
    'network',
    'unknown',
    'timeout',
  ];
  const noTryAgain: ScanErrorCode[] = ['no_weight', 'unauthorized', 'bad_request', 'bad_photo', 'insufficient_credits', 'unavailable'];

  for (const code of tryAgain) {
    it(`offers Try again after ${code}`, () => {
      expect(new ScanError(code, 'x').canTryAgain).toBe(true);
    });
  }

  for (const code of noTryAgain) {
    it(`does not offer Try again after ${code}`, () => {
      expect(new ScanError(code, 'x').canTryAgain).toBe(false);
    });
  }
});
