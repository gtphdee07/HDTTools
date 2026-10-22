import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import * as api from './api';
import * as breakdown from './breakdown';
import { makeWorld, renderApp } from './scanTestKit';
import GOLDEN from '../../test-vectors/breakdown_cases.json';
import type { RecentRig } from './types';

// Interaction tests: App.tsx has no exported handlers to unit-test in
// isolation - its ~10 handlers all read/write one shared `wizard` state
// object via closures, so the only way to verify their real call
// sequence is to drive the actual rendered UI, the same "sociable, real
// call sequence" category TESTING.md defines for Python/Kotlin. Network
// calls (extract*) are mocked and createBreakdown is a pass-through spy over the real local math; localStorage/
// sessionStorage are the real jsdom implementations, matching how
// recentRigs.ts and the disclaimer-acknowledged flag actually persist.
// DOM cleanup between tests is centralized in setupTests.ts.

vi.mock('./api');
vi.mock('./breakdown', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./breakdown')>();
  return { ...actual, createBreakdown: vi.fn(actual.createBreakdown) };
});
const mockedApi = vi.mocked(api);
const spiedBreakdown = vi.mocked(breakdown);

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

async function startNewRig(nickname: string) {
  const user = userEvent.setup();
  await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
  await user.type(screen.getByPlaceholderText('e.g. Big Blue'), nickname);
  await user.click(screen.getByRole('button', { name: 'Start New Rig' }));
  return user;
}

// Skips all three image steps to reach Results, with none of the
// per-step assertions the "start new rig..." test below makes along the
// way - just the click sequence, for tests that only care what's on the
// other side of it.
async function reachResults(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: "I don't have this image" }));
  await user.click(screen.getByRole('button', { name: 'Next: Trailer Tag' }));
  await user.click(screen.getByRole('button', { name: "I don't have this image" }));
  await user.click(screen.getByRole('button', { name: 'Next: Scale Ticket' }));
  await user.click(screen.getByRole('button', { name: 'No Image / Enter Weight Manually' }));
  await user.click(screen.getByRole('button', { name: 'See My Results' }));
}

describe('App wizard interactions', () => {
  it('start new rig, skip every image, reaches results and saves the rig + a history entry', async () => {
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

    await waitFor(() => expect(spiedBreakdown.createBreakdown).toHaveBeenCalledTimes(1));
    expect(spiedBreakdown.createBreakdown).toHaveBeenCalledWith({}, {}, {}, 20);

    expect(await screen.findByText('⚠️ Experimental Tool — Not for Safety Decisions')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'I Understand — Continue' }));

    expect(screen.getByText('Not Enough Information')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Back to Dashboard' }));
    // Appears twice: once as a Recent Rig card, once as a Recent Checks
    // entry - both slices of state (recentRigs and history) updated from
    // the same continueReview call.
    expect(screen.getAllByText('Big Blue')).toHaveLength(2);
    expect(screen.getByText(/^[A-Z][a-z]{2} \d{2}, \d{4}$/)).toBeInTheDocument();

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
    renderApp({ world: makeWorld() });
    const user = await startNewRig('Big Blue');
    await screen.findByText(/scans left/);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, new File(['x'], 'truck.jpg', { type: 'image/jpeg' }));
    await user.click(screen.getByRole('button', { name: 'Extract Data' }));

    expect(await screen.findByText('Could not read that tag — blurry photo.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: "I don't have this image" }));

    expect(screen.getByText('Check the numbers')).toBeInTheDocument();
    expect(screen.queryByText('Could not read that tag — blurry photo.')).not.toBeInTheDocument();
  });

  it('scanning a tow-vehicle-only ticket fills the stand-alone weight field and hides the pin-weight slider', async () => {
    mockedApi.extractScaleTicket.mockResolvedValue({ steer_axle_lb: 5000, drive_axle_lb: 1000 });
    renderApp({ world: makeWorld() });
    const user = await startNewRig('Big Blue');
    await screen.findByText(/scans left/);
    await user.click(screen.getByRole('button', { name: "I don't have this image" }));

    expect(screen.getByRole('slider')).toBeInTheDocument();

    const standaloneInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(standaloneInput, new File(['x'], 'standalone.jpg', { type: 'image/jpeg' }));

    const weightField = await screen.findByLabelText('Stand-alone Weight (lb, optional)');
    await waitFor(() => expect(weightField).toHaveValue(6000));
    expect(screen.queryByRole('slider')).not.toBeInTheDocument();
  });

  it('adjusting the pin-weight slider sends the raw whole-number percentage, not a fraction', async () => {
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

    await waitFor(() => expect(spiedBreakdown.createBreakdown).toHaveBeenCalledWith({}, {}, {}, 15));
  });
});

describe('Disclaimer gate', () => {
  it('withholds the results until the Disclaimer is acknowledged, then reveals them and records the acknowledgement', async () => {
    render(<App />);
    const user = await startNewRig('Big Blue');
    await reachResults(user);

    expect(await screen.findByText('⚠️ Experimental Tool — Not for Safety Decisions')).toBeInTheDocument();
    expect(screen.queryByText('Not Enough Information')).not.toBeInTheDocument();
    expect(sessionStorage.getItem('rigcheck:disclaimerAcknowledged')).not.toBe('true');

    await user.click(screen.getByRole('button', { name: 'I Understand — Continue' }));

    expect(screen.getByText('Not Enough Information')).toBeInTheDocument();
    expect(screen.queryByText('⚠️ Experimental Tool — Not for Safety Decisions')).not.toBeInTheDocument();
    expect(sessionStorage.getItem('rigcheck:disclaimerAcknowledged')).toBe('true');
  });

  it('does not show the Disclaimer again once it was already acknowledged earlier in the session', async () => {
    sessionStorage.setItem('rigcheck:disclaimerAcknowledged', 'true');
    render(<App />);
    const user = await startNewRig('Big Blue');
    await reachResults(user);

    expect(await screen.findByText('Not Enough Information')).toBeInTheDocument();
    expect(screen.queryByText('⚠️ Experimental Tool — Not for Safety Decisions')).not.toBeInTheDocument();
  });
});

// The optional truck GCWR (#46), driven through the real screens. Rigs and scale readings come from the shared
// golden-vector fixture so the cases here are the same ones the math is held to.
describe('Truck GCWR', () => {
  const NO_GCWR = GOLDEN.cases.find((c) => c.name === 'no_gcwr_omits_combined_row_and_adds_caveat')!;
  const WITH_GCWR = GOLDEN.cases.find((c) => c.name === 'gcwr_under_limit_safe_to_tow')!;

  beforeEach(() => {
    sessionStorage.setItem('rigcheck:disclaimerAcknowledged', 'true');
  });

  async function typeInto(user: ReturnType<typeof userEvent.setup>, label: string, value: number | undefined) {
    if (value !== undefined) await user.type(screen.getByLabelText(label), String(value));
  }

  // Picks the saved Rig, keys in the case's scale readings by hand and goes to Results.
  async function checkSavedRig(truck: RecentRig['truck'], testCase: typeof NO_GCWR) {
    const rig: RecentRig = { nickname: 'Big Blue', truck, trailer: testCase.trailer, lastUsedAt: new Date().toISOString() };
    localStorage.setItem('rigcheck:recentRigs', JSON.stringify([rig]));
    render(<App />);
    const user = userEvent.setup();
    await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
    await user.click(screen.getByText('Big Blue'));
    await user.click(screen.getByRole('button', { name: 'No Image / Enter Weight Manually' }));
    await typeInto(user, 'Steer Axle (lb)', testCase.scale.steer_axle_lb);
    await typeInto(user, 'Drive Axle (lb)', testCase.scale.drive_axle_lb);
    await typeInto(user, 'Trailer Axle(s) (lb)', testCase.scale.trailer_axle_lb);
    await typeInto(user, 'Gross Weight (lb)', testCase.scale.gross_weight_lb);
    await user.click(screen.getByRole('button', { name: 'See My Results' }));
    return user;
  }

  it('a Rig saved before GCWR existed still loads; its Results have no Combined row and the Safe to Tow caveat', async () => {
    await checkSavedRig(NO_GCWR.truck, NO_GCWR);

    expect(await screen.findByText('Safe to Tow')).toBeInTheDocument();
    expect(screen.getByText(NO_GCWR.expected.subline)).toBeInTheDocument();
    expect(screen.getByText('Trailer Total (GVWR)')).toBeInTheDocument();
    expect(screen.queryByText('Combined Rig Weight')).not.toBeInTheDocument();
  });

  it('a Rig saved with a GCWR restores it when selected: Results show the Combined row and no caveat', async () => {
    await checkSavedRig(WITH_GCWR.truck, WITH_GCWR);

    expect(await screen.findByText('Safe to Tow')).toBeInTheDocument();
    expect(screen.getByText(WITH_GCWR.expected.subline)).toBeInTheDocument();
    expect(screen.getByText('Combined Rig Weight')).toBeInTheDocument();
    expect(screen.getByText('28,000 lb rated')).toBeInTheDocument();
    expect(screen.queryByText(/GCWR\) wasn't checked/)).not.toBeInTheDocument();
  });

  it('a GCWR typed on the truck review step is used, warns below the GVWR, and is saved with the Rig', async () => {
    render(<App />);
    const user = await startNewRig('Big Blue');
    await user.click(screen.getByRole('button', { name: "I don't have this image" }));

    expect(screen.getByText("From your owner's manual. Leave blank if you can't find it.")).toBeInTheDocument();
    await user.type(screen.getByLabelText('GVWR (lb)'), '14000');
    await user.type(screen.getByLabelText('GCWR (lb), optional'), '10000');
    expect(screen.getByRole('alert')).toHaveTextContent("below the truck's GVWR");

    await user.clear(screen.getByLabelText('GCWR (lb), optional'));
    await user.type(screen.getByLabelText('GCWR (lb), optional'), '28000');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Next: Trailer Tag' }));
    await user.click(screen.getByRole('button', { name: "I don't have this image" }));
    await user.click(screen.getByRole('button', { name: 'Next: Scale Ticket' }));
    await user.click(screen.getByRole('button', { name: 'No Image / Enter Weight Manually' }));
    await user.type(screen.getByLabelText('Gross Weight (lb)'), '26000');
    await user.click(screen.getByRole('button', { name: 'See My Results' }));

    expect(await screen.findByText('Combined Rig Weight')).toBeInTheDocument();
    expect(screen.getByText('26,000 lb actual')).toBeInTheDocument();
    expect(screen.getByText('28,000 lb rated')).toBeInTheDocument();

    const stored: RecentRig[] = JSON.parse(localStorage.getItem('rigcheck:recentRigs') ?? '[]');
    expect(stored[0].truck.gcwr_lb).toBe(28000);
  });
});
