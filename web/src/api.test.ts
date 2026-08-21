import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createBreakdown } from './api';
import CONTRACT from '../../test-vectors/pin_weight_pct_contract.json';

// Interface-contract test, paired with tests/test_api.py's matching case
// via the shared test-vectors/pin_weight_pct_contract.json fixture. The
// UI (this file's callers: Web's ReviewStep slider, Android's
// TruckTagEntryScreen slider) works in whole percentage points (15-25);
// compute_breakdown/computeBreakdown and the /api/breakdown request body
// work in the equivalent 0.15-0.25 fraction. This is the one place in
// web/ that does that conversion (pin_weight_pct: pinWeightPct / 100) -
// a change to that line breaks this test, not just a UI slider.

describe('createBreakdown', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('sends pin_weight_pct as the fraction the UI whole-number percentage converts to', async () => {
    await createBreakdown({}, {}, {}, CONTRACT.ui_percent);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(options.body as string);
    expect(body.pin_weight_pct).toBeCloseTo(CONTRACT.api_fraction);
  });
});
