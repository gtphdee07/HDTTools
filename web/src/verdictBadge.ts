import type { Verdict } from './types';

// Shared between Dashboard.tsx's "Recent Checks" list and History.tsx's
// full history, both of which render a HistoryEntry's verdict as a
// compact badge. Extracted here after finding the same bug duplicated in
// both files 2026-08-21: each previously treated anything that wasn't a
// literal 'pass' as "Over Limit" - a partial or insufficient check
// (missing data, not an actual over-limit reading) got the same
// alarming label as a genuine failure. Labels match breakdown.py's
// verdict_for headlines, shortened for a compact badge.
export const VERDICT_BADGE: Record<Verdict, { tone: 'success' | 'warning' | 'insufficient'; label: string }> = {
  pass: { tone: 'success', label: 'Safe to Tow' },
  fail: { tone: 'warning', label: 'Over Limit' },
  partial: { tone: 'insufficient', label: 'Partially Checked' },
  insufficient: { tone: 'insufficient', label: 'Not Enough Info' },
};
