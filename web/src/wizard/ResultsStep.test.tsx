import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { BreakdownItem, VerdictInfo } from '../types';
import { ResultsStep } from './ResultsStep';

const PASS_VERDICT: VerdictInfo = {
  status: 'pass',
  headline: 'Safe to Tow',
  subline: 'Every axle checks out under its rated limit.',
  bandBg: 'var(--state-success)',
  icon: 'check-circle-2',
};

function item(overrides: Partial<BreakdownItem> = {}): BreakdownItem {
  return {
    label: 'Front Axle (Steer)',
    tone: 'success',
    badgeLabel: '500 lb to spare',
    pct: 80,
    barColor: 'var(--state-success)',
    actualLabel: '5,000 lb',
    limitLabel: '6,000 lb',
    note: null,
    estimated: false,
    ...overrides,
  };
}

function baseProps(overrides: Partial<Parameters<typeof ResultsStep>[0]> = {}) {
  return {
    verdict: PASS_VERDICT,
    breakdownItems: [item()],
    onRestart: vi.fn(),
    onGoHome: vi.fn(),
    ...overrides,
  };
}

describe('ResultsStep', () => {
  it("renders the verdict's headline and subline", () => {
    render(<ResultsStep {...baseProps()} />);
    expect(screen.getByText('Safe to Tow')).toBeInTheDocument();
    expect(screen.getByText('Every axle checks out under its rated limit.')).toBeInTheDocument();
  });

  it("renders each breakdown item's label, badge, and actual/rated weights", () => {
    render(
      <ResultsStep
        {...baseProps({
          breakdownItems: [item({ label: 'Trailer Total (GVWR)', badgeLabel: '460 lb to spare', actualLabel: '12,040 lb', limitLabel: '12,500 lb' })],
        })}
      />,
    );

    expect(screen.getByText('Trailer Total (GVWR)')).toBeInTheDocument();
    expect(screen.getByText('460 lb to spare')).toBeInTheDocument();
    expect(screen.getByText('12,040 lb actual')).toBeInTheDocument();
    expect(screen.getByText('12,500 lb rated')).toBeInTheDocument();
  });

  it('renders a note when present, omits it when null', () => {
    const { rerender } = render(
      <ResultsStep {...baseProps({ breakdownItems: [item({ note: 'Assumes a 2-axle trailer.' })] })} />,
    );
    expect(screen.getByText('Assumes a 2-axle trailer.')).toBeInTheDocument();

    rerender(<ResultsStep {...baseProps({ breakdownItems: [item({ note: null })] })} />);
    expect(screen.queryByText('Assumes a 2-axle trailer.')).not.toBeInTheDocument();
  });

  it('shows the estimated-figures notice when any item is estimated', () => {
    render(<ResultsStep {...baseProps({ breakdownItems: [item({ estimated: true })] })} />);
    expect(screen.getByText('⚠️ Estimated Figures — Confirm Before You Buy')).toBeInTheDocument();
  });

  it('hides the estimated-figures notice when no item is estimated', () => {
    render(<ResultsStep {...baseProps({ breakdownItems: [item({ estimated: false })] })} />);
    expect(screen.queryByText('⚠️ Estimated Figures — Confirm Before You Buy')).not.toBeInTheDocument();
  });

  it('calls onRestart when "Run Another Check" is clicked', async () => {
    const onRestart = vi.fn();
    render(<ResultsStep {...baseProps({ onRestart })} />);

    await userEvent.click(screen.getByRole('button', { name: 'Run Another Check' }));

    expect(onRestart).toHaveBeenCalled();
  });

  it('calls onGoHome when "Back to Dashboard" is clicked', async () => {
    const onGoHome = vi.fn();
    render(<ResultsStep {...baseProps({ onGoHome })} />);

    await userEvent.click(screen.getByRole('button', { name: 'Back to Dashboard' }));

    expect(onGoHome).toHaveBeenCalled();
  });
});
