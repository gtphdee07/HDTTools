import { afterEach, describe, expect, it, vi } from 'vitest';
import { computeBreakdown, createBreakdown, verdictFor } from './breakdown';
import GOLDEN from '../../test-vectors/breakdown_cases.json';
import PIN_CONTRACT from '../../test-vectors/pin_weight_pct_contract.json';

// The golden-vector fixture is the source of truth for the breakdown math
// (ADR-0001 as amended by ADR-0007); Python, Kotlin and this TypeScript port
// are all implementations tested against it, so every case runs for real here
// - nothing is skipped via "requires". A case that requires a capability this
// runner doesn't know fails loudly instead, same as the Python and Kotlin runners.

const SUPPORTED_CAPABILITIES = new Set([
  'insufficient_tone',
  'gvwr_fallback_trailer_estimate',
  'adjustable_pin_weight_pct',
  'predictive_truck_estimate',
]);

function unsupportedCapabilities(requires: readonly string[]): string[] {
  return requires.filter((capability) => !SUPPORTED_CAPABILITIES.has(capability));
}

function parseLb(label: string): number {
  const match = /^([\d,]+) lb$/.exec(label);
  if (!match) throw new Error(`unexpected label format: ${label}`);
  return Number(match[1].replace(/,/g, ''));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

// Rows Android words differently on purpose (see Breakdown.kt); only these may carry "note_android".
const ANDROID_NOTE_ROWS = new Set(['Tow Vehicle Total (GVWR)', 'Combined Rig Weight']);

type GoldenCase = (typeof GOLDEN.cases)[number];

function checkCase(testCase: GoldenCase): void {
  expect(unsupportedCapabilities(testCase.requires), `${testCase.name}: unknown capability`).toEqual([]);
  const items = computeBreakdown(testCase.truck, testCase.trailer, testCase.scale, testCase.pin_weight_pct);
  const verdict = verdictFor(items);
  expect(verdict.status).toBe(testCase.expected.verdict_status);
  expect(verdict.headline, `${testCase.name}: headline`).toBe(testCase.expected.headline);
  expect(verdict.subline, `${testCase.name}: subline`).toBe(testCase.expected.subline);

  const byLabel = new Map(items.map((item) => [item.label, item]));
  for (const expected of testCase.expected.items) {
    const actual = byLabel.get(expected.label);
    expect(actual, `${testCase.name}: missing row ${expected.label}`).toBeDefined();
    expect(actual!.tone, `${expected.label}: tone`).toBe(expected.tone);
    expect(parseLb(actual!.actualLabel), `${expected.label}: actual_lb`).toBe(expected.actual_lb);
    expect(parseLb(actual!.limitLabel), `${expected.label}: limit_lb`).toBe(expected.limit_lb);
    expect(actual!.pct, `${expected.label}: pct`).toBe(expected.pct);
    expect(actual!.estimated, `${expected.label}: estimated`).toBe(expected.estimated);
    expect(actual!.badgeLabel, `${expected.label}: badge`).toBe(expected.badge);
    expect(actual!.note, `${expected.label}: note`).toBe(expected.note);
  }
}

describe('golden vectors', () => {
  it.each(GOLDEN.cases.map((c) => [c.name, c] as const))('%s', (_name, testCase) => {
    checkCase(testCase);
  });

  it('has an over-limit case for every breakdown row', () => {
    const overLimitRows = new Set(
      GOLDEN.cases.flatMap((c) => c.expected.items.filter((i) => i.tone === 'warning').map((i) => i.label)),
    );
    const allRows = computeBreakdown({}, {}, {}, 0.2).map((item) => item.label);
    expect(allRows.filter((label) => !overLimitRows.has(label))).toEqual([]);
  });

  it('fails the run for a fixture case that needs an unknown capability', () => {
    const badCase = { ...GOLDEN.cases[0], requires: ['no_such_capability'] };
    expect(() => checkCase(badCase)).toThrow(/unknown capability/);
  });

  it('only puts note_android on the rows Android words differently', () => {
    const stray = GOLDEN.cases.flatMap((c) =>
      c.expected.items
        .filter((i) => 'note_android' in i && !ANDROID_NOTE_ROWS.has(i.label))
        .map((i) => `${c.name}/${i.label}`),
    );
    expect(stray).toEqual([]);
  });

  it('fails, not skips, a case that needs an unknown capability', () => {
    expect(unsupportedCapabilities(['no_such_capability'])).toEqual(['no_such_capability']);
    expect(unsupportedCapabilities(['insufficient_tone'])).toEqual([]);
  });
});

describe('createBreakdown', () => {
  it('computes the verdict locally without any network call', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const baseline = GOLDEN.cases[0];

    const result = createBreakdown(baseline.truck, baseline.trailer, baseline.scale, 20);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(result.verdict).toBe(baseline.expected.verdict_status);
    expect(result.verdictInfo.status).toBe(baseline.expected.verdict_status);
    expect(result.breakdownItems).toHaveLength(baseline.expected.items.length);
  });

  it('stamps the result with a "Mon DD, YYYY" date', () => {
    expect(createBreakdown({}, {}, {}, 20).date).toMatch(/^[A-Z][a-z]{2} \d{2}, \d{4}$/);
  });

  // Paired with test-vectors/pin_weight_pct_contract.json: the UI works in whole
  // percentage points, the math in a 0-1 fraction, and createBreakdown is the one
  // place that divides by 100.
  it('converts the UI whole-number pin weight percentage to the fraction the math uses', () => {
    const predictive = GOLDEN.cases.find((c) => c.name === 'rounding_half_way_predictive_truck_estimate')!;

    const viaUi = createBreakdown(predictive.truck, predictive.trailer, predictive.scale, PIN_CONTRACT.ui_percent);
    const direct = computeBreakdown(predictive.truck, predictive.trailer, predictive.scale, PIN_CONTRACT.api_fraction);

    expect(viaUi.breakdownItems).toEqual(direct);
  });

  it('treats a NaN reading like a missing one, as JSON serialization to the old API did', () => {
    const withNaN = createBreakdown({ gvwr_lb: 14000, front_gawr_lb: 6000 }, {}, { steer_axle_lb: Number.NaN }, 20);
    const withoutIt = createBreakdown({ gvwr_lb: 14000, front_gawr_lb: 6000 }, {}, {}, 20);

    expect(withNaN.breakdownItems).toEqual(withoutIt.breakdownItems);
  });
});
