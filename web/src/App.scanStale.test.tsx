import { act, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { chooseAndExtract, fileInput, makeWorld, photo, reachTruckUpload, startNewRig } from './scanTestKit';

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

const standaloneWeight = () => screen.getByLabelText('Stand-alone Weight (lb, optional)');

describe('a scan that answers after its check is no longer the current one', () => {
  it('does not change the new check, and the balance on screen is still read again', async () => {
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

  it('does not show the failure of a dropped scan in the new check, and still reads the balance again', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction('fail');
    const user = await reachTruckUpload(world);
    const release = world.holdNextResponse();
    await chooseAndExtract(user);

    await startNewRig(user, 'Second');
    // A refunded scan leaves the balance as it was, so move it behind the app's back to see a read happen.
    world.setBalance(7);
    await act(async () => release());

    expect(await screen.findByText(/7 scans left/)).toBeInTheDocument();
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

    await startNewRig(user, 'Second');
    await chooseAndExtract(user, photo('second-truck.jpg'));
    await screen.findByText('Check the numbers');
    expect(standaloneWeight()).toHaveValue(null);

    await act(async () => release());

    // The weight read for the first check never reaches the second.
    await waitFor(() => expect(world.requests).toHaveLength(3));
    expect(standaloneWeight()).toHaveValue(null);
    expect(screen.getByLabelText('Manufacturer')).toHaveValue('Ford');
  });
});
