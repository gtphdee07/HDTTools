import type { ScaleTicketData, TrailerTagData, TruckTagData } from './types';

export interface BreakdownItem {
  label: string;
  tone: 'success' | 'warning';
  badgeLabel: string;
  pct: number;
  barColor: string;
  actualLabel: string;
  limitLabel: string;
  note: string | null;
}

export interface Verdict {
  headline: string;
  subline: string;
  bandBg: string;
  icon: 'alert-triangle' | 'check-circle-2';
}

interface RawItem {
  label: string;
  actual: number;
  limit: number;
  note?: string;
}

/**
 * Ports the prototype's `_breakdown()`: compares scale readings against
 * rated limits from the truck/trailer tags, axle by axle.
 */
export function breakdown(truck: TruckTagData, trailer: TrailerTagData, scale: ScaleTicketData): BreakdownItem[] {
  const steer = scale.steer_axle_lb ?? 0;
  const drive = scale.drive_axle_lb ?? 0;
  const trailerAxle = scale.trailer_axle_lb ?? 0;
  const gross = scale.gross_weight_lb ?? 0;
  const truckGvwr = truck.gvwr_lb ?? 0;
  const trailerGvwr = trailer.gvwr_lb ?? 0;
  const gawrPerAxle = trailer.gawr_per_axle_lb ?? 0;

  const items: RawItem[] = [
    { label: 'Front Axle (Steer)', actual: steer, limit: truck.front_gawr_lb ?? 0 },
    { label: 'Rear Axle (Drive)', actual: drive, limit: truck.rear_gawr_lb ?? 0 },
    {
      label: 'Tow Vehicle Total (GVWR)',
      actual: steer + drive,
      limit: truckGvwr,
      note: "Steer + drive axle readings vs. your truck tag's GVWR.",
    },
    {
      label: 'Trailer Axle(s)',
      actual: trailerAxle,
      limit: gawrPerAxle * 2,
      note: "Assumes a 2-axle trailer at the tag's per-axle rating.",
    },
    {
      label: 'Trailer Total (GVWR)',
      actual: trailerAxle,
      limit: trailerGvwr,
      note: 'Excludes tongue weight carried by the truck — not on either tag.',
    },
    { label: 'Combined Rig Weight', actual: gross, limit: truckGvwr + trailerGvwr },
  ];

  return items.map((item) => {
    const pass = item.actual <= item.limit;
    const margin = Math.round(item.limit - item.actual);
    const pct = item.limit > 0 ? Math.min(100, Math.round((item.actual / item.limit) * 100)) : 0;
    return {
      label: item.label,
      tone: pass ? 'success' : 'warning',
      badgeLabel: pass ? `${margin.toLocaleString()} lb to spare` : `${Math.abs(margin).toLocaleString()} lb over`,
      pct,
      barColor: pass ? 'var(--state-success)' : 'var(--state-danger)',
      actualLabel: `${Math.round(item.actual).toLocaleString()} lb`,
      limitLabel: `${Math.round(item.limit).toLocaleString()} lb`,
      note: item.note ?? null,
    };
  });
}

export function verdictFor(items: BreakdownItem[]): Verdict {
  const anyFail = items.some((i) => i.tone === 'warning');
  return anyFail
    ? {
        headline: 'Not Safe to Tow',
        subline: 'One or more axles are over their rated limit — see the breakdown below.',
        bandBg: 'var(--state-danger)',
        icon: 'alert-triangle',
      }
    : {
        headline: 'Safe to Tow',
        subline: 'Every axle checks out under its rated limit.',
        bandBg: 'var(--state-success)',
        icon: 'check-circle-2',
      };
}
