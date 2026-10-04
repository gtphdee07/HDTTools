import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { HistoryEntry, Verdict } from '../types';
import { History } from './History';

function entry(verdict: Verdict, overrides: Partial<HistoryEntry> = {}): HistoryEntry {
  return { id: '1', date: '2026-08-21', rigNickname: 'Big Blue', verdict, ...overrides };
}

describe('History', () => {
  it('renders the title and each entry\'s nickname and date', () => {
    render(<History history={[entry('pass')]} />);
    expect(screen.getByText('Check History')).toBeInTheDocument();
    // "Big Blue" appears twice: once as a filter pill, once as the row's nickname.
    expect(screen.getAllByText('Big Blue').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('2026-08-21')).toBeInTheDocument();
  });

  it('labels a pass verdict "Safe to Tow"', () => {
    render(<History history={[entry('pass')]} />);
    expect(screen.getByText('Safe to Tow')).toBeInTheDocument();
  });

  it('labels a fail verdict "Over Limit"', () => {
    render(<History history={[entry('fail')]} />);
    expect(screen.getByText('Over Limit')).toBeInTheDocument();
  });

  // Bug found 2026-08-21 auditing web/'s test coverage: History previously
  // rendered anything that wasn't a literal 'pass' as "Over Limit" - a
  // partial or insufficient check (missing data, not an actual over-limit
  // reading) got the same mislabel and warning-tone badge as a genuine
  // failure. Both non-fail, non-pass verdicts need their own, honest label.

  it('labels a partial verdict distinctly from an actual failure, not "Over Limit"', () => {
    render(<History history={[entry('partial')]} />);
    expect(screen.getByText('Partially Checked')).toBeInTheDocument();
    expect(screen.queryByText('Over Limit')).not.toBeInTheDocument();
  });

  it('labels an insufficient verdict distinctly from an actual failure, not "Over Limit"', () => {
    render(<History history={[entry('insufficient')]} />);
    expect(screen.getByText('Not Enough Info')).toBeInTheDocument();
    expect(screen.queryByText('Over Limit')).not.toBeInTheDocument();
  });

  it('renders multiple entries independently', () => {
    render(<History history={[entry('pass', { id: '1', rigNickname: 'Big Blue' }), entry('fail', { id: '2', rigNickname: 'Red Rocket' })]} />);
    expect(screen.getAllByText('Big Blue').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Red Rocket').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Safe to Tow')).toBeInTheDocument();
    expect(screen.getByText('Over Limit')).toBeInTheDocument();
  });
});

describe('History filters', () => {
  function mixedHistory(): HistoryEntry[] {
    return [
      entry('pass', { id: '1', date: '2026-08-21', rigNickname: 'Big Blue' }),
      entry('fail', { id: '2', date: '2026-08-22', rigNickname: 'Red Rocket' }),
      entry('partial', { id: '3', date: '2026-08-23', rigNickname: 'Big Blue' }),
      entry('insufficient', { id: '4', date: '2026-08-24', rigNickname: 'Red Rocket' }),
    ];
  }

  it('shows every entry under "All rigs"', () => {
    render(<History history={mixedHistory()} />);
    for (const date of ['2026-08-21', '2026-08-22', '2026-08-23', '2026-08-24']) {
      expect(screen.getByText(date)).toBeInTheDocument();
    }
  });

  it('"Within limits" shows only pass verdicts, not partial or insufficient ones', async () => {
    const user = userEvent.setup();
    render(<History history={mixedHistory()} />);
    await user.click(screen.getByRole('button', { name: 'Within limits' }));

    expect(screen.getByText('2026-08-21')).toBeInTheDocument();
    expect(screen.queryByText('2026-08-22')).not.toBeInTheDocument();
    expect(screen.queryByText('2026-08-23')).not.toBeInTheDocument();
    expect(screen.queryByText('2026-08-24')).not.toBeInTheDocument();
  });

  it('"Over limit" shows only fail verdicts, not partial or insufficient ones', async () => {
    const user = userEvent.setup();
    render(<History history={mixedHistory()} />);
    await user.click(screen.getByRole('button', { name: 'Over limit' }));

    expect(screen.getByText('2026-08-22')).toBeInTheDocument();
    expect(screen.queryByText('2026-08-21')).not.toBeInTheDocument();
    expect(screen.queryByText('2026-08-23')).not.toBeInTheDocument();
    expect(screen.queryByText('2026-08-24')).not.toBeInTheDocument();
  });

  it('a per-rig pill shows only that rig\'s entries, of any verdict', async () => {
    const user = userEvent.setup();
    render(<History history={mixedHistory()} />);
    await user.click(screen.getByRole('button', { name: 'Big Blue' }));

    expect(screen.getByText('2026-08-21')).toBeInTheDocument();
    expect(screen.getByText('2026-08-23')).toBeInTheDocument();
    expect(screen.queryByText('2026-08-22')).not.toBeInTheDocument();
    expect(screen.queryByText('2026-08-24')).not.toBeInTheDocument();
  });

  it('shows the empty state when the active filter matches nothing', async () => {
    const user = userEvent.setup();
    render(<History history={[entry('fail', { id: '1', rigNickname: 'Red Rocket' })]} />);
    expect(screen.queryByText('No checks match this filter.')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Within limits' }));
    expect(screen.getByText('No checks match this filter.')).toBeInTheDocument();
  });

  it('shows the empty state with no history and no filter applied', () => {
    render(<History history={[]} />);
    expect(screen.getByText('No checks match this filter.')).toBeInTheDocument();
  });
});
