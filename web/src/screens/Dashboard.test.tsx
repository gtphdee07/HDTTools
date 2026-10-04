import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { HistoryEntry, RecentRig, Verdict } from '../types';
import { Dashboard } from './Dashboard';

function rig(overrides: Partial<RecentRig> = {}): RecentRig {
  return {
    nickname: 'Big Blue',
    truck: { manufacturer: 'Ford' },
    trailer: { manufacturer: 'Forest River' },
    lastUsedAt: new Date().toISOString(),
    ...overrides,
  };
}

function entry(verdict: Verdict): HistoryEntry {
  return { id: '1', date: '2026-08-21', rigNickname: 'Big Blue', verdict };
}

// Same VERDICT_BADGE bug as screens/History.test.tsx, found duplicated
// in this file's Recent Checks list 2026-08-21: a partial/insufficient
// entry previously got mislabeled "Over Limit", the same as a genuine
// failure. Both files now share verdictBadge.ts.
describe('Dashboard Recent Checks labeling', () => {
  it('labels a partial verdict "Partially Checked", not "Over Limit"', () => {
    render(<Dashboard recentRigs={[]} history={[entry('partial')]} onStartWizard={vi.fn()} onGoHistory={vi.fn()} />);
    expect(screen.getByText('Partially Checked')).toBeInTheDocument();
    expect(screen.queryByText('Over Limit')).not.toBeInTheDocument();
  });

  it('labels an insufficient verdict "Not Enough Info", not "Over Limit"', () => {
    render(<Dashboard recentRigs={[]} history={[entry('insufficient')]} onStartWizard={vi.fn()} onGoHistory={vi.fn()} />);
    expect(screen.getByText('Not Enough Info')).toBeInTheDocument();
    expect(screen.queryByText('Over Limit')).not.toBeInTheDocument();
  });

  it('still labels a real failure "Over Limit"', () => {
    render(<Dashboard recentRigs={[]} history={[entry('fail')]} onStartWizard={vi.fn()} onGoHistory={vi.fn()} />);
    expect(screen.getByText('Over Limit')).toBeInTheDocument();
  });
});

describe('Dashboard rig grid', () => {
  it('renders a rig card with its nickname and manufacturer subtitles', () => {
    render(
      <Dashboard
        recentRigs={[rig({ nickname: 'Big Blue' })]}
        history={[]}
        onStartWizard={vi.fn()}
        onGoHistory={vi.fn()}
      />,
    );
    expect(screen.getByText('Big Blue')).toBeInTheDocument();
    expect(screen.getByText('Truck: Ford')).toBeInTheDocument();
    expect(screen.getByText('Trailer: Forest River')).toBeInTheDocument();
  });

  it('omits a manufacturer line when that half of the rig has none', () => {
    render(
      <Dashboard
        recentRigs={[rig({ truck: {}, trailer: { manufacturer: 'Forest River' } })]}
        history={[]}
        onStartWizard={vi.fn()}
        onGoHistory={vi.fn()}
      />,
    );
    expect(screen.queryByText(/^Truck:/)).not.toBeInTheDocument();
    expect(screen.getByText('Trailer: Forest River')).toBeInTheDocument();
  });

  it('clicking a rig card starts the wizard', async () => {
    const user = userEvent.setup();
    const onStartWizard = vi.fn();
    render(
      <Dashboard recentRigs={[rig({ nickname: 'Big Blue' })]} history={[]} onStartWizard={onStartWizard} onGoHistory={vi.fn()} />,
    );
    await user.click(screen.getByText('Big Blue'));
    expect(onStartWizard).toHaveBeenCalledTimes(1);
  });

  it('clicking "New rig" starts the wizard', async () => {
    const user = userEvent.setup();
    const onStartWizard = vi.fn();
    render(<Dashboard recentRigs={[]} history={[]} onStartWizard={onStartWizard} onGoHistory={vi.fn()} />);
    await user.click(screen.getByText('New rig'));
    expect(onStartWizard).toHaveBeenCalledTimes(1);
  });

  it('clicking "Start New Check" starts the wizard', async () => {
    const user = userEvent.setup();
    const onStartWizard = vi.fn();
    render(<Dashboard recentRigs={[]} history={[]} onStartWizard={onStartWizard} onGoHistory={vi.fn()} />);
    await user.click(screen.getByRole('button', { name: 'Start New Check' }));
    expect(onStartWizard).toHaveBeenCalledTimes(1);
  });

  it('clicking "View History" goes to history', async () => {
    const user = userEvent.setup();
    const onGoHistory = vi.fn();
    render(<Dashboard recentRigs={[]} history={[]} onStartWizard={vi.fn()} onGoHistory={onGoHistory} />);
    await user.click(screen.getByRole('button', { name: 'View History' }));
    expect(onGoHistory).toHaveBeenCalledTimes(1);
  });
});

describe('Dashboard recent checks', () => {
  it('shows only the two most recent checks, each with its rig subtitle joined from truck + trailer', () => {
    const history: HistoryEntry[] = [
      { id: '1', date: '2026-08-21', rigNickname: 'Big Blue', verdict: 'pass' },
      { id: '2', date: '2026-08-20', rigNickname: 'Big Blue', verdict: 'pass' },
      { id: '3', date: '2026-08-19', rigNickname: 'Big Blue', verdict: 'pass' },
    ];
    render(<Dashboard recentRigs={[rig({ nickname: 'Big Blue' })]} history={history} onStartWizard={vi.fn()} onGoHistory={vi.fn()} />);

    expect(screen.getByText(/2026-08-21.*Ford \+ Forest River/)).toBeInTheDocument();
    expect(screen.getByText(/2026-08-20.*Ford \+ Forest River/)).toBeInTheDocument();
    expect(screen.queryByText(/2026-08-19/)).not.toBeInTheDocument();
  });

  it('omits the subtitle join when the rig is no longer in recentRigs', () => {
    const history: HistoryEntry[] = [{ id: '1', date: '2026-08-21', rigNickname: 'Gone Rig', verdict: 'pass' }];
    render(<Dashboard recentRigs={[]} history={history} onStartWizard={vi.fn()} onGoHistory={vi.fn()} />);
    expect(screen.getByText('2026-08-21')).toBeInTheDocument();
  });

  it('shows "View history" only once there is at least one check', () => {
    const { rerender } = render(<Dashboard recentRigs={[]} history={[]} onStartWizard={vi.fn()} onGoHistory={vi.fn()} />);
    expect(screen.queryByRole('button', { name: 'View history' })).not.toBeInTheDocument();

    rerender(
      <Dashboard
        recentRigs={[]}
        history={[{ id: '1', date: '2026-08-21', rigNickname: 'Big Blue', verdict: 'pass' }]}
        onStartWizard={vi.fn()}
        onGoHistory={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', { name: 'View history' })).toBeInTheDocument();
  });

  it('clicking "View history" (Recent Checks header) goes to history', async () => {
    const user = userEvent.setup();
    const onGoHistory = vi.fn();
    render(
      <Dashboard
        recentRigs={[]}
        history={[{ id: '1', date: '2026-08-21', rigNickname: 'Big Blue', verdict: 'pass' }]}
        onStartWizard={vi.fn()}
        onGoHistory={onGoHistory}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'View history' }));
    expect(onGoHistory).toHaveBeenCalledTimes(1);
  });

  it('shows the empty state when there are no checks yet', () => {
    render(<Dashboard recentRigs={[]} history={[]} onStartWizard={vi.fn()} onGoHistory={vi.fn()} />);
    expect(screen.getByText('No checks yet — run your first one above.')).toBeInTheDocument();
  });
});
