import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { RecentRig } from '../types';
import { RigStep } from './RigStep';

function rig(overrides: Partial<RecentRig> = {}): RecentRig {
  return {
    nickname: 'Big Blue',
    truck: { manufacturer: 'Ford' },
    trailer: { manufacturer: 'Forest River' },
    lastUsedAt: '2026-08-21T00:00:00.000Z',
    ...overrides,
  };
}

function baseProps(overrides: Partial<Parameters<typeof RigStep>[0]> = {}) {
  return {
    recentRigs: [],
    onSelectExisting: vi.fn(),
    onStartNew: vi.fn(),
    ...overrides,
  };
}

describe('RigStep', () => {
  it('renders no rig cards when there are no recent rigs', () => {
    render(<RigStep {...baseProps()} />);
    expect(screen.queryByText('CHOOSE')).not.toBeInTheDocument();
  });

  it("renders each recent rig's nickname and a manufacturer subtitle when both are known", () => {
    render(<RigStep {...baseProps({ recentRigs: [rig()] })} />);
    expect(screen.getByText('Big Blue')).toBeInTheDocument();
    expect(screen.getByText('Ford + Forest River')).toBeInTheDocument();
  });

  it('omits the subtitle line when neither manufacturer is known', () => {
    render(<RigStep {...baseProps({ recentRigs: [rig({ truck: {}, trailer: {} })] })} />);
    expect(screen.getByText('Big Blue')).toBeInTheDocument();
    expect(screen.queryByText('Ford')).not.toBeInTheDocument();
    expect(screen.queryByText('+')).not.toBeInTheDocument();
  });

  it('calls onSelectExisting with the clicked rig', async () => {
    const onSelectExisting = vi.fn();
    const theRig = rig();
    render(<RigStep {...baseProps({ recentRigs: [theRig], onSelectExisting })} />);

    await userEvent.click(screen.getByText('Big Blue'));

    expect(onSelectExisting).toHaveBeenCalledWith(theRig);
  });

  it('disables Start New Rig until a non-blank nickname is typed', async () => {
    render(<RigStep {...baseProps()} />);
    const button = screen.getByRole('button', { name: 'Start New Rig' });
    expect(button).toBeDisabled();

    await userEvent.type(screen.getByPlaceholderText('e.g. Big Blue'), 'Red Rocket');

    expect(button).toBeEnabled();
  });

  it('keeps Start New Rig disabled for a whitespace-only nickname', async () => {
    render(<RigStep {...baseProps()} />);

    await userEvent.type(screen.getByPlaceholderText('e.g. Big Blue'), '   ');

    expect(screen.getByRole('button', { name: 'Start New Rig' })).toBeDisabled();
  });

  it('calls onStartNew with the trimmed nickname', async () => {
    const onStartNew = vi.fn();
    render(<RigStep {...baseProps({ onStartNew })} />);

    await userEvent.type(screen.getByPlaceholderText('e.g. Big Blue'), '  Red Rocket  ');
    await userEvent.click(screen.getByRole('button', { name: 'Start New Rig' }));

    expect(onStartNew).toHaveBeenCalledWith('Red Rocket');
  });
});
