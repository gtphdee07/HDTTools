import { screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { chooseAndExtract, fileInput, makeWorld, photo, reachTruckUpload } from './scanTestKit';
import type { FakeWorld } from './scanTestKit';

// A scan spends a Scan Credit, so its answer must land in the check that asked for it. While a scan is in
// flight the user cannot leave or restart the check, and, as a backstop, a result that comes back for a
// check that is no longer the current one is dropped. The service is the fake from scanTestKit.tsx, with
// its answer held so a scan stays in flight for as long as a test needs.

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

const standaloneWeight = () => screen.getByLabelText('Stand-alone Weight (lb, optional)');

// On the Truck review step, with nothing in flight.
async function reachTruckReview(world: FakeWorld) {
  const user = await reachTruckUpload(world);
  await chooseAndExtract(user);
  await screen.findByText('Check the numbers');
  return user;
}

// Every control that leaves the check, wherever it sits on the page.
const leavingControls = () => [
  screen.getByRole('button', { name: /Back to Dashboard/ }),
  ...screen.getAllByRole('button', { name: 'Dashboard' }),
  ...screen.getAllByRole('button', { name: 'History' }),
  screen.getByRole('button', { name: /^(Account|Sign in)$/ }),
  ...screen.getAllByRole('button', { name: 'Start New Check' }),
];

const expectLeavingBlocked = () => {
  const controls = leavingControls();
  // Header (Dashboard, History, Account, Start New Check), the back link, and the footer's two links.
  expect(controls).toHaveLength(7);
  for (const control of controls) expect(control).toBeDisabled();
  expect(screen.getByRole('status')).toHaveTextContent(/reading your photo/i);
};

const expectLeavingAllowed = () => {
  for (const control of leavingControls()) expect(control).toBeEnabled();
  expect(screen.queryByText(/reading your photo/i)).not.toBeInTheDocument();
};

describe('while a scan of the Truck Tag photo is in flight', () => {
  it('cannot be left or restarted, says why, and can be again once the scan answers', async () => {
    const world = makeWorld({ balance: 3 });
    const user = await reachTruckUpload(world);
    const release = world.holdNextResponse();

    await chooseAndExtract(user);

    expect(await screen.findByText(/Reading Truck Compliance Label/)).toBeInTheDocument();
    expectLeavingBlocked();

    release();
    expect(await screen.findByText('Check the numbers')).toBeInTheDocument();
    expectLeavingAllowed();
    expect(screen.getByLabelText('Manufacturer')).toHaveValue('Ford');
  });

  it('can be left again once the scan fails', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction('fail');
    const user = await reachTruckUpload(world);
    const release = world.holdNextResponse();

    await chooseAndExtract(user);
    expectLeavingBlocked();

    release();
    expect(await screen.findByText(/your scan was refunded/i)).toBeInTheDocument();
    expectLeavingAllowed();
  });

  it('keeps the check when the user tries to leave and restart mid-scan', async () => {
    const world = makeWorld({ balance: 3 });
    const user = await reachTruckUpload(world);
    const release = world.holdNextResponse();
    await chooseAndExtract(user);

    for (const control of leavingControls()) await user.click(control);
    // The logo leads home too.
    await user.click(screen.getByAltText('Wandering Trails, Wagging Tails'));
    expect(screen.getByText(/Reading Truck Compliance Label/)).toBeInTheDocument();

    release();
    expect(await screen.findByText('Check the numbers')).toBeInTheDocument();
    expect(screen.getByLabelText('Manufacturer')).toHaveValue('Ford');
  });
});

describe('while a stand-alone ticket scan is in flight', () => {
  it('cannot be left or restarted, says why, and can be again once the scan answers', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction({ fields: { manufacturer: 'Ford' } }, { fields: { steer_axle_lb: 5000, drive_axle_lb: 1000 } });
    const user = await reachTruckReview(world);
    const release = world.holdNextResponse();

    await user.upload(fileInput(), photo('standalone.jpg'));

    expect(await screen.findByRole('button', { name: 'Reading…' })).toBeInTheDocument();
    expectLeavingBlocked();

    release();
    await waitFor(() => expect(standaloneWeight()).toHaveValue(6000));
    expectLeavingAllowed();
  });

  it('can be left again once the scan fails', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction({ fields: { manufacturer: 'Ford' } }, 'fail');
    const user = await reachTruckReview(world);
    const release = world.holdNextResponse();

    await user.upload(fileInput(), photo('standalone.jpg'));
    expectLeavingBlocked();

    release();
    expect(await screen.findByText(/your scan was refunded/i)).toBeInTheDocument();
    expectLeavingAllowed();
  });

  it('keeps the check when the user tries to leave and restart mid-scan', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction({ fields: { manufacturer: 'Ford' } }, { fields: { gross_weight_lb: 7000 } });
    const user = await reachTruckReview(world);
    const release = world.holdNextResponse();
    await user.upload(fileInput(), photo('standalone.jpg'));

    for (const control of leavingControls()) await user.click(control);
    expect(screen.getByText('Check the numbers')).toBeInTheDocument();

    release();
    await waitFor(() => expect(standaloneWeight()).toHaveValue(7000));
  });
});
