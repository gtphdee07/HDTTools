import { act, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { makeWorld, renderApp } from './scanTestKit';

// The backstop behind App.scanInFlight.test.tsx: blocking the controls makes a scan answering for a check
// that is gone rare, and dropping such an answer makes it impossible (a script, a stale tab or the browser's
// own back can still start a new check). Here the Header is replaced by one that is never locked, so a new
// check can be started while a scan is pending, which the real controls do not allow.

vi.mock('./components/Header', () => ({
  Header: ({ onStartWizard }: { onStartWizard: () => void }) => <button onClick={onStartWizard}>Start New Check</button>,
}));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

type User = ReturnType<typeof userEvent.setup>;
type World = ReturnType<typeof makeWorld>;

const photo = (name = 'truck.jpg') => new File([`pixels of ${name}`], name, { type: 'image/jpeg' });
const fileInput = () => document.querySelector('input[type="file"]') as HTMLInputElement;
const standaloneWeight = () => screen.getByLabelText('Stand-alone Weight (lb, optional)');

async function startNewRig(user: User, nickname = 'Big Blue') {
  await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
  await user.type(screen.getByPlaceholderText('e.g. Big Blue'), nickname);
  await user.click(screen.getByRole('button', { name: 'Start New Rig' }));
}

async function chooseAndExtract(user: User, file = photo()) {
  await user.upload(fileInput(), file);
  await user.click(screen.getByRole('button', { name: 'Extract Data' }));
}

async function reachTruckUpload(world: World) {
  const user = renderApp({ world });
  await startNewRig(user);
  await screen.findByText(/3 scans left/);
  return user;
}

describe('a scan that answers after its check is no longer the current one', () => {
  it('does not change the new check, and the balance on screen still follows the spent scan', async () => {
    const world = makeWorld({ balance: 3 });
    const user = await reachTruckUpload(world);
    const release = world.holdNextResponse();
    await chooseAndExtract(user);

    await startNewRig(user, 'Second');
    expect(await screen.findByText(/3 scans left/)).toBeInTheDocument();
    await act(async () => release());

    // The answer is dropped: the new check stays on its photo step, with no fields written into it.
    // The credit was spent, so the balance on screen is read again and shows it.
    expect(await screen.findByText(/2 scans left/)).toBeInTheDocument();
    expect(screen.queryByText('Check the numbers')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Extract Data' })).toBeDisabled();
  });

  it('does not show the failure of a dropped scan in the new check either', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction('fail');
    const user = await reachTruckUpload(world);
    const release = world.holdNextResponse();
    await chooseAndExtract(user);

    await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
    await act(async () => release());
    await user.type(screen.getByPlaceholderText('e.g. Big Blue'), 'Second');
    await user.click(screen.getByRole('button', { name: 'Start New Rig' }));

    // The failed scan was refunded, and the balance on screen shows it.
    expect(await screen.findByText(/3 scans left/)).toBeInTheDocument();
    expect(screen.queryByText(/your scan was refunded/i)).not.toBeInTheDocument();
  });

  it('does not write a stand-alone weight into the new check', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction({ fields: { manufacturer: 'Ford' } }, { fields: { gross_weight_lb: 7000 } });
    const user = await reachTruckUpload(world);
    await chooseAndExtract(user);
    await screen.findByText('Check the numbers');
    const release = world.holdNextResponse();
    await user.upload(fileInput(), photo('standalone.jpg'));

    await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
    await user.type(screen.getByPlaceholderText('e.g. Big Blue'), 'Second');
    await user.click(screen.getByRole('button', { name: 'Start New Rig' }));
    await chooseAndExtract(user, photo('second-truck.jpg'));
    await screen.findByText('Check the numbers');
    expect(standaloneWeight()).toHaveValue(null);

    await act(async () => release());

    // Both checks' scans are spent; the weight read for the first never reaches the second.
    await waitFor(() => expect(world.requests).toHaveLength(3));
    await waitFor(() => expect(world.balance()).toBe(0));
    expect(standaloneWeight()).toHaveValue(null);
    expect(screen.getByLabelText('Manufacturer')).toHaveValue('Ford');
  });
});
