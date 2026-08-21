import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { HistoryEntry, Verdict } from '../types';
import { Dashboard } from './Dashboard';

function entry(verdict: Verdict): HistoryEntry {
  return { id: '1', date: '2026-08-21', rigNickname: 'Big Blue', verdict };
}

// Same VERDICT_BADGE bug as screens/History.test.tsx, found duplicated
// in this file's Recent Checks list 2026-08-21: a partial/insufficient
// entry previously got mislabeled "Over Limit", the same as a genuine
// failure. Both files now share verdictBadge.ts.
describe('Dashboard Recent Checks labeling', () => {
  it('labels a partial verdict "Partially Checked", not "Over Limit"', () => {
    render(<Dashboard recentRigs={[]} history={[entry('partial')]} onStartWizard={vi.fn()} />);
    expect(screen.getByText('Partially Checked')).toBeInTheDocument();
    expect(screen.queryByText('Over Limit')).not.toBeInTheDocument();
  });

  it('labels an insufficient verdict "Not Enough Info", not "Over Limit"', () => {
    render(<Dashboard recentRigs={[]} history={[entry('insufficient')]} onStartWizard={vi.fn()} />);
    expect(screen.getByText('Not Enough Info')).toBeInTheDocument();
    expect(screen.queryByText('Over Limit')).not.toBeInTheDocument();
  });

  it('still labels a real failure "Over Limit"', () => {
    render(<Dashboard recentRigs={[]} history={[entry('fail')]} onStartWizard={vi.fn()} />);
    expect(screen.getByText('Over Limit')).toBeInTheDocument();
  });
});
