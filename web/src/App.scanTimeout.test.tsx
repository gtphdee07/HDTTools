import { act, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SCAN_TIMEOUT_MS } from './api';
import { chooseAndExtract, fileInput, makeWorld, photo, reachTruckUpload } from './scanTestKit';
import type { FakeWorld } from './scanTestKit';

// A scan that never answers must not lock the user in the check (#103 blocks leaving while a scan is in
// flight). The Scan service is the fake from scanTestKit.tsx, silent for one request; the time limit is run
// out with fake timers, so nothing here waits for real. Timers are faked only after the check is reached, and
// only setTimeout/clearTimeout, so the screens and the testing library keep working as usual.

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

const standaloneWeight = () => screen.getByLabelText('Stand-alone Weight (lb, optional)');

const leavingControls = () => [
  screen.getByRole('button', { name: /Back to Dashboard/ }),
  ...screen.getAllByRole('button', { name: 'Dashboard' }),
  ...screen.getAllByRole('button', { name: 'History' }),
  screen.getByRole('button', { name: /^(Account|Sign in)$/ }),
  ...screen.getAllByRole('button', { name: 'Start New Check' }),
];

// The testing library settles after every async helper with a setTimeout(0) and only moves a faked clock
// when it finds a `jest` global; without this stand-in every findBy and user action would wait forever.
function fakeClock() {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  vi.stubGlobal('jest', { advanceTimersByTime: (ms: number) => vi.advanceTimersByTime(ms) });
}
const requestSentBy = (world: FakeWorld, count: number) => waitFor(() => expect(world.requests).toHaveLength(count));
const runOutTheClock = () => act(async () => void (await vi.advanceTimersByTimeAsync(SCAN_TIMEOUT_MS)));

function expectLeavingBlocked() {
  for (const control of leavingControls()) expect(control).toBeDisabled();
  expect(screen.getByRole('status')).toHaveTextContent(/reading your photo/i);
}

function expectLeavingAllowed() {
  for (const control of leavingControls()) expect(control).toBeEnabled();
  expect(screen.queryByText(/reading your photo/i)).not.toBeInTheDocument();
}

describe('a scan of the Truck Tag photo that never answers', () => {
  it('is given up on, says it took too long, and lets the check be left again', async () => {
    const world = makeWorld({ balance: 3 });
    const user = await reachTruckUpload(world);
    world.neverAnswerNextRequest();
    fakeClock();

    await chooseAndExtract(user);
    await requestSentBy(world, 1);
    expectLeavingBlocked();

    await runOutTheClock();

    expect(await screen.findByText(/took too long.*not charged twice/i)).toBeInTheDocument();
    expectLeavingAllowed();
  });

  it('is retried under the same request id, so the retry is charged once', async () => {
    const world = makeWorld({ balance: 3 });
    const user = await reachTruckUpload(world);
    world.neverAnswerNextRequest();
    fakeClock();

    await chooseAndExtract(user);
    await requestSentBy(world, 1);
    await runOutTheClock();
    await screen.findByText(/took too long/i);
    expect(world.balance()).toBe(2);

    await user.click(screen.getByRole('button', { name: 'Extract Data' }));

    expect(await screen.findByText('Check the numbers')).toBeInTheDocument();
    expect(world.requests).toHaveLength(2);
    expect(world.requests[1].clientRequestId).toBeTruthy();
    expect(world.requests[1].clientRequestId).toBe(world.requests[0].clientRequestId);
    expect(world.balance()).toBe(2);
  });
});

describe('a stand-alone ticket scan that never answers', () => {
  async function reachTruckReview(world: FakeWorld) {
    const user = await reachTruckUpload(world);
    await chooseAndExtract(user);
    await screen.findByText('Check the numbers');
    return user;
  }

  it('is given up on, says it took too long, and lets the check be left again', async () => {
    const world = makeWorld({ balance: 3 });
    const user = await reachTruckReview(world);
    world.neverAnswerNextRequest();
    fakeClock();

    await user.upload(fileInput(), photo('standalone.jpg'));
    await requestSentBy(world, 2);
    expectLeavingBlocked();

    await runOutTheClock();

    expect(await screen.findByText(/took too long.*not charged twice/i)).toBeInTheDocument();
    expectLeavingAllowed();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeEnabled();
  });

  it('is retried with "Try again" under the same request id, charged once', async () => {
    const world = makeWorld({ balance: 3 });
    const ticket = { fields: { steer_axle_lb: 5000, drive_axle_lb: 1000 } };
    // The abandoned request still consumes an answer on the service's side, so the retry gets a second one.
    world.queueExtraction({ fields: { manufacturer: 'Ford' } }, ticket, ticket);
    const user = await reachTruckReview(world);
    world.neverAnswerNextRequest();
    fakeClock();

    await user.upload(fileInput(), photo('standalone.jpg'));
    await requestSentBy(world, 2);
    await runOutTheClock();
    await screen.findByText(/took too long/i);
    expect(world.balance()).toBe(1);

    await user.click(screen.getByRole('button', { name: 'Try again' }));

    await waitFor(() => expect(standaloneWeight()).toHaveValue(6000));
    expect(world.requests).toHaveLength(3);
    expect(world.requests[2].clientRequestId).toBeTruthy();
    expect(world.requests[2].clientRequestId).toBe(world.requests[1].clientRequestId);
    expect(world.balance()).toBe(1);
  });
});
