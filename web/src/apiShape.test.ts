import { describe, expect, it } from 'vitest';
import type { BreakdownItem, VerdictInfo } from './types';
import CONTRACT from '../../test-vectors/breakdown_response_shape_contract.json';

// Cross-platform interface test, paired with tests/test_api.py's
// test_breakdown_response_matches_the_shared_api_contract via the shared
// test-vectors/breakdown_response_shape_contract.json fixture ("Option
// B" from the web/ API-shape-drift discussion - see
// ../../FUTURE_API_SCHEMA_VALIDATION.md for the fuller schema-export
// approach this deliberately stops short of).
//
// This half doesn't touch a real response - it only proves that
// BreakdownItem/VerdictInfo, as currently declared in types.ts, have
// exactly the keys the shared contract expects. TypeScript's excess-
// property checking on the object literals below does the rest of the
// work: add a field to the interface without adding it here and the
// build fails (missing property) before this test even runs; remove a
// field from the interface without removing it here and the build fails
// too (excess property) - either way, a human is forced to touch this
// file, and this file's own assertion then forces them to touch the
// shared contract (and, in turn, the paired Python test) to make it
// green again.
describe('BreakdownItem/VerdictInfo shape', () => {
  it('BreakdownItem has exactly the keys the shared API contract declares', () => {
    const sample: BreakdownItem = {
      label: 'Front Axle (Steer)',
      tone: 'success',
      badgeLabel: '500 lb to spare',
      pct: 80,
      barColor: 'var(--state-success)',
      actualLabel: '5,000 lb',
      limitLabel: '6,000 lb',
      note: null,
      estimated: false,
    };

    expect(Object.keys(sample).sort()).toEqual([...CONTRACT.breakdown_item_keys].sort());
  });

  it('VerdictInfo has exactly the keys the shared API contract declares', () => {
    const sample: VerdictInfo = {
      status: 'pass',
      headline: 'Safe to Tow',
      subline: 'Every axle checks out under its rated limit.',
      bandBg: 'var(--state-success)',
      icon: 'check-circle-2',
    };

    expect(Object.keys(sample).sort()).toEqual([...CONTRACT.verdict_keys].sort());
  });
});
