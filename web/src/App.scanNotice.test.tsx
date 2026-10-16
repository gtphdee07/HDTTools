import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { chooseAndExtract, makeWorld, reachTruckUpload, renderApp, startNewRig } from './scanTestKit';

// A Scan that was delivered is charged even when nothing (or not everything) was read off the photo
// (workers/scan-proxy/CONTEXT.md). The review step it lands on says so, as a notice and not a failure:
// no error, and no Try again. Driven through the real screens against the fake Scan service.

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

const NOTHING_READ = /A Scan was used and nothing could be read\. Type the numbers in, or go back and choose a different photo\./;
const SOME_UNREAD = /A Scan was used\. We couldn't read:/;

describe('the review step after a Scan', () => {
  it('says a Scan was used when no field was read, offers no Try again, and still counts the Scan', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction({ fields: {} });
    const user = await reachTruckUpload(world);

    await chooseAndExtract(user);

    expect(await screen.findByText('Check the numbers')).toBeInTheDocument();
    expect(screen.getByText(NOTHING_READ)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
    expect(screen.queryByText(SOME_UNREAD)).not.toBeInTheDocument();
    expect(world.balance()).toBe(2);

    // The balance on screen is read again: back on the photo step it shows the new count.
    await user.click(screen.getByRole('button', { name: 'Choose a different photo' }));
    expect(await screen.findByText(/2 scans left/)).toBeInTheDocument();
  });

  it('sends no second Scan until the user chooses a different photo and extracts again', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction({ fields: {} });
    const user = await reachTruckUpload(world);
    await chooseAndExtract(user);
    await screen.findByText(NOTHING_READ);

    await user.click(screen.getByRole('button', { name: 'Choose a different photo' }));
    expect(world.requests).toHaveLength(1);

    await chooseAndExtract(user);
    expect(await screen.findByText('Check the numbers')).toBeInTheDocument();
    expect(screen.queryByText(NOTHING_READ)).not.toBeInTheDocument();
    expect(screen.getByLabelText('Manufacturer')).toHaveValue('Ford');
    expect(world.requests).toHaveLength(2);
  });

  it('names the fields that were not read when only some were', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction({ fields: { manufacturer: 'Ford', gvwr_lb: 9000 } });
    const user = await reachTruckUpload(world);

    await chooseAndExtract(user);

    const notice = await screen.findByText(SOME_UNREAD);
    expect(notice).toHaveTextContent(
      "A Scan was used. We couldn't read: Front GAWR (lb), Rear GAWR (lb). Fill those in yourself.",
    );
    expect(screen.queryByText(NOTHING_READ)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Choose a different photo' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
    expect(screen.getByLabelText('Manufacturer')).toHaveValue('Ford');
    expect(world.balance()).toBe(2);
  });

  it('shows no notice when every field was read (the optional ones are not counted)', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction({ fields: { manufacturer: 'Ford', gvwr_lb: 9000, front_gawr_lb: 4500, rear_gawr_lb: 5500 } });
    const user = await reachTruckUpload(world);

    await chooseAndExtract(user);

    expect(await screen.findByText('Check the numbers')).toBeInTheDocument();
    expect(screen.queryByText(/A Scan was used/)).not.toBeInTheDocument();
    expect(world.balance()).toBe(2);
  });

  it('works the same on the Trailer Tag and the Scale Ticket, naming that step\'s own fields', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction(
      { fields: { manufacturer: 'Ford', gvwr_lb: 9000, front_gawr_lb: 4500, rear_gawr_lb: 5500 } },
      { fields: { manufacturer: 'Big Tex', gvwr_lb: 7000, gawr_per_axle_lb: 3500 } },
      { fields: {} },
    );
    const user = await reachTruckUpload(world);

    await chooseAndExtract(user);
    await user.click(await screen.findByRole('button', { name: 'Next: Trailer Tag' }));
    await chooseAndExtract(user);
    expect(await screen.findByText(SOME_UNREAD)).toHaveTextContent(
      "We couldn't read: Unloaded Weight / UVW (lb). Fill those in yourself.",
    );

    await user.click(screen.getByRole('button', { name: 'Next: Scale Ticket' }));
    // The trailer's notice does not follow the user to the next step.
    expect(screen.queryByText(SOME_UNREAD)).not.toBeInTheDocument();
    await chooseAndExtract(user);
    expect(await screen.findByText(NOTHING_READ)).toBeInTheDocument();
  });

  it('shows no notice when the photo is skipped, since no Scan was used', async () => {
    const world = makeWorld({ balance: 3 });
    const user = renderApp({ world });
    await startNewRig(user);
    await screen.findByText(/3 scans left/);

    await user.click(screen.getByRole('button', { name: "I don't have this image" }));

    expect(await screen.findByText('Check the numbers')).toBeInTheDocument();
    expect(screen.queryByText(/A Scan was used/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Choose a different photo' })).not.toBeInTheDocument();
    expect(world.requests).toHaveLength(0);
    expect(world.balance()).toBe(3);
  });
});
