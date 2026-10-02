import type { BreakdownItem, ScaleTicketData, TrailerTagData, TruckTagData, VerdictInfo } from './types';

// TypeScript implementation of the breakdown/verdict math. The shared golden-vector
// fixture (test-vectors/breakdown_cases.json) is the source of truth, not this file
// and not the Python one (ADR-0001 as amended by ADR-0007).

const DEFAULT_PIN_WEIGHT_PCT = 0.2;

export interface CreateBreakdownResult {
  date: string;
  verdict: 'pass' | 'fail' | 'partial' | 'insufficient';
  breakdownItems: BreakdownItem[];
  verdictInfo: VerdictInfo;
}

// Ties round toward +infinity, matching the fixture's rule (Kotlin roundToInt, Math.round).
// `value - floor` is exact in binary floating point, so no tie is mis-detected.
function roundHalfUp(value: number): number {
  const floor = Math.floor(value);
  return value - floor >= 0.5 ? floor + 1 : floor;
}

// A NaN reading (a half-typed number field) used to reach the old API as JSON null, so
// it must keep behaving as "not entered", not as a real number.
function reading(value: number | null | undefined): number | undefined {
  return typeof value === 'number' && !Number.isNaN(value) ? value : undefined;
}

function lb(value: number | undefined): number {
  return value ?? 0;
}

function formatLb(value: number): string {
  return `${roundHalfUp(value).toLocaleString('en-US', { maximumFractionDigits: 0 })} lb`;
}

function wholeNumber(value: number): string {
  return roundHalfUp(value).toLocaleString('en-US', { maximumFractionDigits: 0 });
}

function percent(fraction: number): string {
  return `${Math.round(fraction * 100)}%`;
}

export function computeBreakdown(
  truck: TruckTagData,
  trailer: TrailerTagData,
  scale: ScaleTicketData,
  pinWeightPctIn: number = DEFAULT_PIN_WEIGHT_PCT,
): BreakdownItem[] {
  // `1 - pinWeightPct` is a divisor below; exactly 1.0 would divide by zero.
  const pinWeightPct = pinWeightPctIn === 1.0 ? 0.99 : pinWeightPctIn;

  const steerRaw = reading(scale.steer_axle_lb);
  const driveRaw = reading(scale.drive_axle_lb);
  const trailerAxleRaw = reading(scale.trailer_axle_lb);
  const grossRaw = reading(scale.gross_weight_lb);
  const truckGvwrRaw = reading(truck.gvwr_lb);
  const trailerGvwrRaw = reading(trailer.gvwr_lb);
  const frontGawrRaw = reading(truck.front_gawr_lb);
  const rearGawrRaw = reading(truck.rear_gawr_lb);
  const gawrPerAxleRaw = reading(trailer.gawr_per_axle_lb);

  const steer = lb(steerRaw);
  const drive = lb(driveRaw);
  const trailerAxle = lb(trailerAxleRaw);
  const gross = lb(grossRaw);
  const truckGvwr = lb(truckGvwrRaw);
  const trailerGvwr = lb(trailerGvwrRaw);
  const gawrPerAxle = lb(gawrPerAxleRaw);

  const axleCountRaw = reading(trailer.axle_count);
  const axleCount = axleCountRaw ? Math.trunc(axleCountRaw) : 2;
  const trailerAxleNote = axleCountRaw
    ? `Trailer axle rating: ${axleCount} axle(s) at the tag's per-axle rating.`
    : "Assumes a 2-axle trailer at the tag's per-axle rating.";

  const standaloneRaw = reading(truck.standalone_weight_lb);
  const standaloneWeight = lb(standaloneRaw);
  const haveHitched = steerRaw !== undefined && driveRaw !== undefined;
  // Truthy, not just defined: an explicit 0 means "not entered".
  const haveStandalone = Boolean(standaloneRaw);

  let trailerTotalActual: number;
  let trailerTotalNote: string;
  let trailerTotalEstimated = false;
  if (haveHitched && haveStandalone) {
    const tongueWeight = Math.max(0, steer + drive - standaloneWeight);
    trailerTotalActual = trailerAxle + tongueWeight;
    trailerTotalNote =
      `Includes an estimated ${wholeNumber(tongueWeight)} lb tongue weight ` +
      "(steer + drive minus your truck's stand-alone weight).";
  } else if (trailerAxleRaw !== undefined) {
    trailerTotalActual = trailerAxle / (1 - pinWeightPct);
    trailerTotalNote =
      'Estimated total weight — assumes the axle reading is ' +
      `${percent(1 - pinWeightPct)} of actual trailer weight; ` +
      "enter your truck's stand-alone weight for an exact figure.";
    trailerTotalEstimated = true;
  } else {
    trailerTotalActual = trailerGvwr;
    trailerTotalNote =
      'Estimated total weight — no scale reading yet, so this assumes ' +
      'the trailer is loaded to its rated GVWR; weigh it for a real figure.';
    trailerTotalEstimated = true;
  }

  let truckTotalEstimated = false;
  let truckTotalActual: number | null;
  let truckTotalNote: string;
  if (haveHitched) {
    truckTotalActual = steer + drive;
    truckTotalNote = "Steer + drive axle readings vs. your truck tag's GVWR.";
  } else if (haveStandalone) {
    const truckTongueWeightEstimate = trailerTotalActual * pinWeightPct;
    truckTotalActual = standaloneWeight + truckTongueWeightEstimate;
    truckTotalNote =
      'Estimated total weight — includes an estimated ' +
      `${wholeNumber(truckTongueWeightEstimate)} lb tongue weight ` +
      `(${percent(pinWeightPct)} of the trailer's estimated total); enter a ` +
      'real hitched scale reading for an exact figure.';
    truckTotalEstimated = true;
  } else {
    truckTotalActual = null;
    truckTotalNote = "Steer + drive axle readings vs. your truck tag's GVWR.";
  }

  // [label, actual, limit, note, insufficient, estimated]. A rated limit of exactly 0
  // means "not entered", never "really rated for zero".
  const rawItems: [string, number, number, string | null, boolean, boolean][] = [
    ['Front Axle (Steer)', steer, lb(frontGawrRaw), null, steerRaw === undefined || !frontGawrRaw, false],
    ['Rear Axle (Drive)', drive, lb(rearGawrRaw), null, driveRaw === undefined || !rearGawrRaw, false],
    [
      'Tow Vehicle Total (GVWR)',
      truckTotalActual ?? 0,
      truckGvwr,
      truckTotalNote,
      truckTotalActual === null || !truckGvwrRaw,
      truckTotalEstimated,
    ],
    [
      'Trailer Axle(s)',
      trailerAxle,
      gawrPerAxle * axleCount,
      trailerAxleNote,
      trailerAxleRaw === undefined || !gawrPerAxleRaw,
      false,
    ],
    ['Trailer Total (GVWR)', trailerTotalActual, trailerGvwr, trailerTotalNote, !trailerGvwrRaw, trailerTotalEstimated],
    [
      'Combined Rig Weight',
      gross,
      truckGvwr + trailerGvwr,
      null,
      grossRaw === undefined || !truckGvwrRaw || !trailerGvwrRaw,
      false,
    ],
  ];

  return rawItems.map(([label, actual, limit, note, insufficient, estimated]): BreakdownItem => {
    if (insufficient) {
      return {
        label,
        tone: 'insufficient',
        badgeLabel: 'Not enough info',
        pct: 0,
        barColor: 'var(--state-info)',
        actualLabel: formatLb(actual),
        limitLabel: formatLb(limit),
        note,
        estimated: false,
      };
    }
    const passed = actual <= limit;
    const margin = roundHalfUp(limit - actual);
    return {
      label,
      tone: passed ? 'success' : 'warning',
      badgeLabel: passed ? `${margin.toLocaleString('en-US')} lb to spare` : `${Math.abs(margin).toLocaleString('en-US')} lb over`,
      pct: Math.min(100, roundHalfUp((actual / limit) * 100)),
      barColor: passed ? 'var(--state-success)' : 'var(--state-danger)',
      actualLabel: formatLb(actual),
      limitLabel: formatLb(limit),
      note,
      estimated,
    };
  });
}

export function verdictFor(items: BreakdownItem[]): VerdictInfo {
  const tones = items.map((item) => item.tone);
  const anyFail = tones.includes('warning');
  const allInsufficient = tones.every((tone) => tone === 'insufficient');
  const anyInsufficient = tones.includes('insufficient');

  // A real failure always wins, even if other rows are insufficient.
  if (anyFail) {
    return {
      status: 'fail',
      headline: 'Not Safe to Tow',
      subline: 'One or more axles are over their rated limit — see the breakdown below.',
      bandBg: 'var(--state-danger)',
      icon: 'alert-triangle',
    };
  }
  if (allInsufficient) {
    return {
      status: 'insufficient',
      headline: 'Not Enough Information',
      subline: 'Add at least a truck tag, trailer tag, or scale ticket to check anything.',
      bandBg: 'var(--state-info)',
      icon: 'help-circle',
    };
  }
  if (anyInsufficient) {
    return {
      status: 'partial',
      headline: 'Partially Checked',
      subline: "Some axles couldn't be checked yet — add more data for a complete picture.",
      bandBg: 'var(--state-info)',
      icon: 'help-circle',
    };
  }
  return {
    status: 'pass',
    headline: 'Safe to Tow',
    subline: 'Every axle checks out under its rated limit.',
    bandBg: 'var(--state-success)',
    icon: 'check-circle-2',
  };
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function formatDate(now: Date): string {
  const day = String(now.getUTCDate()).padStart(2, '0');
  return `${MONTHS[now.getUTCMonth()]} ${day}, ${now.getUTCFullYear()}`;
}

// The UI works in whole percentage points (15-25); the math works in the 0-1 fraction.
// This is the one place that divides by 100 (test-vectors/pin_weight_pct_contract.json).
export function createBreakdown(
  truck: TruckTagData,
  trailer: TrailerTagData,
  scale: ScaleTicketData,
  pinWeightPct: number,
): CreateBreakdownResult {
  const breakdownItems = computeBreakdown(truck, trailer, scale, pinWeightPct / 100);
  const verdictInfo = verdictFor(breakdownItems);
  return { date: formatDate(new Date()), verdict: verdictInfo.status, breakdownItems, verdictInfo };
}
