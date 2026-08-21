import { render, screen } from '@testing-library/react';
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
    expect(screen.getByText('Big Blue')).toBeInTheDocument();
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
    expect(screen.getByText('Big Blue')).toBeInTheDocument();
    expect(screen.getByText('Red Rocket')).toBeInTheDocument();
    expect(screen.getByText('Safe to Tow')).toBeInTheDocument();
    expect(screen.getByText('Over Limit')).toBeInTheDocument();
  });
});
