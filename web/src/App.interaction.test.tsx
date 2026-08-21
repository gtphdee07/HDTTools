import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import * as api from './api';
import type { CreateBreakdownResult } from './api';
import type { RecentRig } from './types';

// Interaction tests: App.tsx has no exported handlers to unit-test in
// isolation - its ~10 handlers all read/write one shared `wizard` state
// object via closures, so the only way to verify their real call
// sequence is to drive the actual rendered UI, the same "sociable, real
// call sequence" category TESTING.md defines for Python/Kotlin. Network
// calls (extract*/createBreakdown) are mocked; localStorage/
// sessionStorage are the real jsdom implementations, matching how
// recentRigs.ts and the disclaimer-acknowledged flag actually persist.
// DOM cleanup between tests is centralized in setupTests.ts.

vi.mock('./api');
const mockedApi = vi.mocked(api);

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  vi.clearAllMocks();
});

const RESULT: CreateBreakdownResult = {
  date: '2026-08-21',
  verdict: 'pass',
  breakdownItems: [
    {
      label: 'Front Axle (Steer)',
      tone: 'success',
      badgeLabel: '500 lb to spare',
      pct: 80,
      barColor: 'var(--state-success)',
      actualLabel: '5,000 lb',
      limitLabel: '6,000 lb',
      note: null,
      estimated: false,
    },
  ],
  verdictInfo: {
    status: 'pass',
    headline: 'Safe to Tow',
    subline: 'Every axle checks out under its rated limit.',
    bandBg: 'var(--state-success)',
    icon: 'check-circle-2',
  },
};

async function startNewRig(nickname: string) {
  const user = userEvent.setup();
  await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
  await user.type(screen.getByPlaceholderText('e.g. Big Blue'), nickname);
  await user.click(screen.getByRole('button', { name: 'Start New Rig' }));
  return user;
}

describe('App wizard interactions', () => {
  it('start new rig, skip every image, reaches results and saves the rig + a history entry', async () => {
    mockedApi.createBreakdown.mockResolvedValue(RESULT);
    render(<App />);
    const user = await startNewRig('Big Blue');

    expect(screen.getByText('Truck Compliance Label')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: "I don't have this image" }));
    expect(screen.getByText('Check the numbers')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Next: Trailer Tag' }));

    expect(screen.getByText('Trailer Compliance Label')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: "I don't have this image" }));
    await user.click(screen.getByRole('button', { name: 'Next: Scale Ticket' }));

    expect(screen.getByText('CAT Scale Ticket')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'No Image / Enter Weight Manually' }));
    await user.click(screen.getByRole('button', { name: 'See My Results' }));

    await waitFor(() => expect(mockedApi.createBreakdown).toHaveBeenCalledTimes(1));
    expect(mockedApi.createBreakdown).toHaveBeenCalledWith({}, {}, {}, 20);

    expect(await screen.findByText('⚠️ Experimental Tool — Not for Safety Decisions')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'I Understand — Continue' }));

    expect(screen.getByText('Safe to Tow')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Back to Dashboard' }));
    // Appears twice: once as a Recent Rig card, once as a Recent Checks
    // entry - both slices of state (recentRigs and history) updated from
    // the same continueReview call.
    expect(screen.getAllByText('Big Blue')).toHaveLength(2);
    expect(screen.getByText('2026-08-21')).toBeInTheDocument();

    const stored: RecentRig[] = JSON.parse(localStorage.getItem('rigcheck:recentRigs') ?? '[]');
    expect(stored).toHaveLength(1);
    expect(stored[0].nickname).toBe('Big Blue');
  });

  it('selecting an existing rig jumps straight to the scale step, skipping truck and trailer', async () => {
    const existing: RecentRig = {
      nickname: 'Big Blue',
      truck: { manufacturer: 'Ford' },
      trailer: { manufacturer: 'Forest River' },
      lastUsedAt: new Date().toISOString(),
    };
    localStorage.setItem('rigcheck:recentRigs', JSON.stringify([existing]));
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
    await user.click(screen.getByText('Big Blue'));

    expect(screen.getByText('CAT Scale Ticket')).toBeInTheDocument();
    expect(screen.queryByText('Truck Compliance Label')).not.toBeInTheDocument();
    expect(screen.queryByText('Trailer Compliance Label')).not.toBeInTheDocument();
  });

  it('an extraction error clears once the user skips instead of retrying', async () => {
    mockedApi.extractTruckTag.mockRejectedValueOnce(new Error('Could not read that tag — blurry photo.'));
    const { container } = render(<App />);
    const user = await startNewRig('Big Blue');

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, new File(['x'], 'truck.jpg', { type: 'image/jpeg' }));
    await user.click(screen.getByRole('button', { name: 'Extract Data' }));

    expect(await screen.findByText('Could not read that tag — blurry photo.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: "I don't have this image" }));

    expect(screen.getByText('Check the numbers')).toBeInTheDocument();
    expect(screen.queryByText('Could not read that tag — blurry photo.')).not.toBeInTheDocument();
  });

  it('scanning a tow-vehicle-only ticket fills the stand-alone weight field and hides the pin-weight slider', async () => {
    mockedApi.extractScaleTicket.mockResolvedValue({ steer_axle_lb: 5000, drive_axle_lb: 1000 });
    const { container } = render(<App />);
    const user = await startNewRig('Big Blue');
    await user.click(screen.getByRole('button', { name: "I don't have this image" }));

    expect(screen.getByRole('slider')).toBeInTheDocument();

    const standaloneInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(standaloneInput, new File(['x'], 'standalone.jpg', { type: 'image/jpeg' }));

    const weightField = await screen.findByLabelText('Stand-alone Weight (lb, optional)');
    await waitFor(() => expect(weightField).toHaveValue(6000));
    expect(screen.queryByRole('slider')).not.toBeInTheDocument();
  });

  it('adjusting the pin-weight slider sends the raw whole-number percentage, not a fraction', async () => {
    mockedApi.createBreakdown.mockResolvedValue(RESULT);
    render(<App />);
    const user = await startNewRig('Big Blue');
    await user.click(screen.getByRole('button', { name: "I don't have this image" }));

    fireEvent.change(screen.getByRole('slider'), { target: { value: '15' } });
    expect(screen.getByText("No ticket? Estimate pin/hitch weight as 15% of the trailer's weight")).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Next: Trailer Tag' }));
    await user.click(screen.getByRole('button', { name: "I don't have this image" }));
    await user.click(screen.getByRole('button', { name: 'Next: Scale Ticket' }));
    await user.click(screen.getByRole('button', { name: 'No Image / Enter Weight Manually' }));
    await user.click(screen.getByRole('button', { name: 'See My Results' }));

    await waitFor(() => expect(mockedApi.createBreakdown).toHaveBeenCalledWith({}, {}, {}, 15));
  });
});
