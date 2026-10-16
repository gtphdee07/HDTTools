import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { BillingStatus } from './billing';
import { SIGNED_IN_AGAIN_TOKEN, makeWorld, renderApp } from './scanTestKit';

// Scanning on Web, end to end through the real screens: signed-in Pro users spend scans through the shared
// Scan service; Free and signed-out visitors are sent to upgrade or sign in; a failed scan, a stale balance
// and a lost response each end the way the user would expect. The service is a fake that follows the
// Worker's contract (see scanTestKit.tsx).

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

type User = ReturnType<typeof userEvent.setup>;

const photo = (name = 'truck.jpg') => new File([`pixels of ${name}`], name, { type: 'image/jpeg' });
const fileInput = () => document.querySelector('input[type="file"]') as HTMLInputElement;

async function startNewRig(user: User, nickname = 'Big Blue') {
  await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
  await user.type(screen.getByPlaceholderText('e.g. Big Blue'), nickname);
  await user.click(screen.getByRole('button', { name: 'Start New Rig' }));
}

async function chooseAndExtract(user: User, file = photo()) {
  await user.upload(fileInput(), file);
  await user.click(screen.getByRole('button', { name: 'Extract Data' }));
}

describe('a Pro user with scans', () => {
  it('reads a photo for exactly one scan and shows the fields it returned', async () => {
    const world = makeWorld({ balance: 3 });
    const user = renderApp({ world });
    await startNewRig(user);
    expect(await screen.findByText(/3 scans left/)).toBeInTheDocument();

    await chooseAndExtract(user);

    expect(await screen.findByText('Check the numbers')).toBeInTheDocument();
    expect(screen.getByLabelText('Manufacturer')).toHaveValue('Ford');
    expect(world.requests).toHaveLength(1);
    expect(world.requests[0]).toMatchObject({ authorization: 'Bearer token-pat', docType: 'truck_tag', mediaType: 'image/jpeg' });
    expect(world.balance()).toBe(2);

    await user.click(screen.getByRole('button', { name: 'Next: Trailer Tag' }));
    expect(await screen.findByText(/2 scans left/)).toBeInTheDocument();
  });

  it('refunds a scan that could not read the photo, says so, and lets the user try again', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction('fail');
    const user = renderApp({ world });
    await startNewRig(user);
    await screen.findByText(/3 scans left/);

    await chooseAndExtract(user);

    expect(await screen.findByText(/your scan was refunded/i)).toBeInTheDocument();
    expect(world.balance()).toBe(3);
    expect(await screen.findByText(/3 scans left/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Extract Data' }));
    expect(await screen.findByText('Check the numbers')).toBeInTheDocument();
    expect(world.balance()).toBe(2);
  });

  it('is not charged twice when a retry follows an answer that never arrived', async () => {
    const world = makeWorld({ balance: 3 });
    world.loseNextResponse();
    const user = renderApp({ world });
    await startNewRig(user);
    await screen.findByText(/3 scans left/);

    await chooseAndExtract(user);
    expect(await screen.findByText(/check your connection/i)).toBeInTheDocument();
    expect(world.balance()).toBe(2);

    await user.click(screen.getByRole('button', { name: 'Extract Data' }));
    expect(await screen.findByText('Check the numbers')).toBeInTheDocument();

    expect(world.requests).toHaveLength(2);
    expect(world.requests[1].clientRequestId).toBeTruthy();
    expect(world.requests[1].clientRequestId).toBe(world.requests[0].clientRequestId);
    expect(world.balance()).toBe(2);
  });

  it('uses a new request id for the next photo, so a second scan is its own charge', async () => {
    const world = makeWorld({ balance: 3 });
    const user = renderApp({ world });
    await startNewRig(user);
    await screen.findByText(/3 scans left/);
    await chooseAndExtract(user);
    await user.click(await screen.findByRole('button', { name: 'Next: Trailer Tag' }));

    await chooseAndExtract(user, photo('trailer.jpg'));
    await screen.findByText('Check the numbers');

    expect(world.requests.map((r) => r.docType)).toEqual(['truck_tag', 'trailer_tag']);
    expect(world.requests[1].clientRequestId).not.toBe(world.requests[0].clientRequestId);
    expect(world.balance()).toBe(1);
  });

  it('is told they are out of scans, with a way to buy more, when the service finds the balance used up', async () => {
    const world = makeWorld({ balance: 2 });
    const user = renderApp({ world });
    await startNewRig(user);
    await screen.findByText(/2 scans left/);
    // Another device spent them after this page loaded.
    world.setBalance(0);

    await chooseAndExtract(user);

    expect(await screen.findAllByText(/out of scans/i)).not.toHaveLength(0);
    expect(screen.queryByRole('button', { name: 'Extract Data' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Buy more scans' })).toBeInTheDocument();
    expect(world.requests).toHaveLength(1);
  });

  it('still gets the way to buy more when the balance cannot be read again after the service said none left', async () => {
    const world = makeWorld({ balance: 2 });
    const user = renderApp({ world });
    await startNewRig(user);
    await screen.findByText(/2 scans left/);
    world.setBalance(0);
    world.billing.getStatus = vi.fn().mockRejectedValue(new Error('offline'));

    await chooseAndExtract(user);

    expect(await screen.findByRole('button', { name: 'Buy more scans' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Extract Data' })).not.toBeInTheDocument();
  });

  it('says plainly when a failed scan could not be refunded automatically, and a retry is not charged again', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction('fail-no-refund');
    const user = renderApp({ world });
    await startNewRig(user);
    await screen.findByText(/3 scans left/);

    await chooseAndExtract(user);
    expect(await screen.findByText(/contact support/i)).toBeInTheDocument();
    expect(world.balance()).toBe(2);

    await user.click(screen.getByRole('button', { name: 'Extract Data' }));
    expect(await screen.findByText('Check the numbers')).toBeInTheDocument();

    expect(world.requests[1].clientRequestId).toBe(world.requests[0].clientRequestId);
    expect(world.balance()).toBe(2);
  });

  it('scans a tow-vehicle-only ticket for one scan too', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction({ fields: { manufacturer: 'Ford' } }, { fields: { steer_axle_lb: 5000, drive_axle_lb: 1000 } });
    const user = renderApp({ world });
    await startNewRig(user);
    await screen.findByText(/3 scans left/);
    await chooseAndExtract(user);
    await screen.findByText('Check the numbers');

    await user.upload(fileInput(), photo('standalone.jpg'));

    await waitFor(() => expect(screen.getByLabelText('Stand-alone Weight (lb, optional)')).toHaveValue(6000));
    expect(world.requests.map((r) => r.docType)).toEqual(['truck_tag', 'scale_ticket']);
    expect(world.balance()).toBe(1);
  });

  it('says the scan was used, and that trying again costs another, when the ticket has no weight on it', async () => {
    const world = makeWorld({ balance: 3 });
    // The service answers, so the scan is charged; the answer just has no weight in it.
    world.queueExtraction({ fields: { manufacturer: 'Ford' } }, { fields: {} }, { fields: { gross_weight_lb: 7000 } });
    const user = renderApp({ world });
    await startNewRig(user);
    await screen.findByText(/3 scans left/);
    await chooseAndExtract(user);
    await screen.findByText('Check the numbers');
    const before = world.balance();

    await user.upload(fileInput(), photo('blank-ticket.jpg'));

    const message = await screen.findByText(/couldn't find a weight/i);
    expect(message).toHaveTextContent(/that scan was used/i);
    expect(message).toHaveTextContent(/trying again uses another/i);
    expect(message).toHaveTextContent(/type the weight in/i);
    expect(world.balance()).toBe(before - 1);

    // Re-sending the same photo is another paid Scan that reads the same, so Try again is not offered.
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Choose a different photo' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Type it in' })).toBeEnabled();
    expect(world.requests).toHaveLength(2);

    // A different photo is its own Scan, under its own request id.
    await user.upload(fileInput(), photo('clearer-ticket.jpg'));
    await waitFor(() => expect(screen.getByLabelText('Stand-alone Weight (lb, optional)')).toHaveValue(7000));
    expect(world.requests).toHaveLength(3);
    expect(world.requests[2].clientRequestId).not.toBe(world.requests[1].clientRequestId);
    expect(world.balance()).toBe(before - 2);
  });

  it('takes the user to the weight field when they choose to type it in after a ticket with no weight', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction({ fields: { manufacturer: 'Ford' } }, { fields: {} });
    const user = renderApp({ world });
    await startNewRig(user);
    await screen.findByText(/3 scans left/);
    await chooseAndExtract(user);
    await screen.findByText('Check the numbers');
    await user.upload(fileInput(), photo('blank-ticket.jpg'));
    await screen.findByText(/couldn't find a weight/i);

    await user.click(screen.getByRole('button', { name: 'Type it in' }));

    expect(screen.getByLabelText('Stand-alone Weight (lb, optional)')).toHaveFocus();
  });

  describe('when a tow-vehicle-only ticket scan does not deliver', () => {
    async function reachTruckReview(world: ReturnType<typeof makeWorld>) {
      const user = renderApp({ world });
      await startNewRig(user);
      await screen.findByText(/3 scans left/);
      await chooseAndExtract(user);
      await screen.findByText('Check the numbers');
      return user;
    }
    const standaloneWeight = () => screen.getByLabelText('Stand-alone Weight (lb, optional)');

    it('is not charged twice when "Try again" follows an answer that never arrived', async () => {
      const world = makeWorld({ balance: 3 });
      const ticket = { fields: { steer_axle_lb: 5000, drive_axle_lb: 1000 } };
      // The lost request still consumes an answer on the service's side, so the retry gets a second one.
      world.queueExtraction({ fields: { manufacturer: 'Ford' } }, ticket, ticket);
      const user = await reachTruckReview(world);
      world.loseNextResponse();

      await user.upload(fileInput(), photo('standalone.jpg'));
      expect(await screen.findByText(/check your connection/i)).toBeInTheDocument();
      expect(world.balance()).toBe(1);

      await user.click(screen.getByRole('button', { name: 'Try again' }));

      await waitFor(() => expect(standaloneWeight()).toHaveValue(6000));
      expect(world.requests).toHaveLength(3);
      expect(world.requests[2].clientRequestId).toBeTruthy();
      expect(world.requests[2].clientRequestId).toBe(world.requests[1].clientRequestId);
      expect(world.balance()).toBe(1);
      expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
    });

    it('retries a refunded failure without picking the photo again', async () => {
      const world = makeWorld({ balance: 3 });
      world.queueExtraction({ fields: { manufacturer: 'Ford' } }, 'fail', { fields: { gross_weight_lb: 7000 } });
      const user = await reachTruckReview(world);

      await user.upload(fileInput(), photo('standalone.jpg'));
      expect(await screen.findByText(/your scan was refunded/i)).toBeInTheDocument();
      expect(world.balance()).toBe(2);

      await user.click(screen.getByRole('button', { name: 'Try again' }));

      await waitFor(() => expect(standaloneWeight()).toHaveValue(7000));
      expect(world.balance()).toBe(1);
    });

    it('retries a failure that could not be refunded with the same request id, charged once', async () => {
      const world = makeWorld({ balance: 3 });
      const ticket = { fields: { gross_weight_lb: 7000 } };
      world.queueExtraction({ fields: { manufacturer: 'Ford' } }, 'fail-no-refund', ticket);
      const user = await reachTruckReview(world);

      await user.upload(fileInput(), photo('standalone.jpg'));
      expect(await screen.findByText(/contact support/i)).toBeInTheDocument();
      expect(world.balance()).toBe(1);

      await user.click(screen.getByRole('button', { name: 'Try again' }));

      await waitFor(() => expect(standaloneWeight()).toHaveValue(7000));
      expect(world.requests[2].clientRequestId).toBe(world.requests[1].clientRequestId);
      expect(world.balance()).toBe(1);
    });

    it('uses a new request id when a different photo is picked after the failure', async () => {
      const world = makeWorld({ balance: 3 });
      const user = await reachTruckReview(world);
      world.loseNextResponse();
      await user.upload(fileInput(), photo('first.jpg'));
      await screen.findByText(/check your connection/i);

      await user.upload(fileInput(), photo('second.jpg'));

      await waitFor(() => expect(world.requests).toHaveLength(3));
      expect(world.requests[2].clientRequestId).not.toBe(world.requests[1].clientRequestId);
    });
  });
});

describe('what the user is offered when a Scan does not deliver', () => {
  const heic = () => new File(['pixels'], 'tag.heic', { type: 'image/heic' });

  async function reachTruckUpload(world: ReturnType<typeof makeWorld>) {
    const user = renderApp({ world });
    await startNewRig(user);
    await screen.findByText(/3 scans left/);
    return user;
  }

  async function reachTruckReview(world: ReturnType<typeof makeWorld>) {
    const user = await reachTruckUpload(world);
    await chooseAndExtract(user);
    await screen.findByText('Check the numbers');
    return user;
  }

  describe('after the service refuses the account token', () => {
    it('offers "Sign in again" instead of the scan count, which leads to the Account screen and back to the same check', async () => {
      const world = makeWorld({ balance: 3 });
      world.queueExtraction('unauthorized');
      const user = await reachTruckUpload(world);

      await chooseAndExtract(user, photo('keep-me.jpg'));

      expect(await screen.findAllByText(/sign-in has expired/i)).not.toHaveLength(0);
      expect(screen.queryByText(/scans left/)).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Extract Data' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Choose a different photo' })).toBeInTheDocument();
      expect(world.balance()).toBe(3);

      await user.click(screen.getByRole('button', { name: 'Sign in again' }));
      await user.type(await screen.findByLabelText('Email'), 'pat@example.com');
      await user.type(screen.getByLabelText('Password'), 'secret1');
      // The header has a Sign in button too; the form's submit is the last one.
      await user.click(screen.getAllByRole('button', { name: 'Sign in' }).at(-1)!);
      await user.click(await screen.findByRole('button', { name: 'Back to your check' }));

      // The same check: the same photo is still chosen, and the stale refusal is gone.
      expect(await screen.findByText(/3 scans left/)).toBeInTheDocument();
      expect(screen.getByText('Selected: keep-me.jpg')).toBeInTheDocument();
      expect(screen.queryByText(/sign-in has expired/i)).not.toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: 'Extract Data' }));
      expect(await screen.findByText('Check the numbers')).toBeInTheDocument();
      expect(world.requests[1].authorization).toBe(`Bearer ${SIGNED_IN_AGAIN_TOKEN}`);
      expect(world.balance()).toBe(2);
    });

    it('offers it on the tow-vehicle-only ticket too, with no Try again', async () => {
      const world = makeWorld({ balance: 3 });
      world.queueExtraction({ fields: { manufacturer: 'Ford' } }, 'unauthorized');
      const user = await reachTruckReview(world);

      await user.upload(fileInput(), photo('standalone.jpg'));

      expect((await screen.findAllByText(/sign-in has expired/i)).length).toBeGreaterThan(0);
      expect(screen.getByRole('button', { name: 'Sign in again' })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Scan tow-vehicle-only ticket' })).not.toBeInTheDocument();
    });
  });

  describe('after the service rejects the request', () => {
    it("says nothing was used, without the service's internal detail, and offers a different photo, not Try again", async () => {
      const world = makeWorld({ balance: 3 });
      world.queueExtraction('bad-request');
      const user = await reachTruckUpload(world);

      await chooseAndExtract(user);

      const message = await screen.findByText(/nothing was used/i);
      expect(message).not.toHaveTextContent(/media_type/);
      expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
      // The same photo is not offered for sending again; a different one is.
      expect(screen.getByRole('button', { name: 'Extract Data' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Choose a different photo' })).toBeInTheDocument();
      expect(world.balance()).toBe(3);

      await user.upload(fileInput(), photo('other.jpg'));
      await user.click(screen.getByRole('button', { name: 'Extract Data' }));
      expect(await screen.findByText('Check the numbers')).toBeInTheDocument();
      expect(world.requests[1].clientRequestId).not.toBe(world.requests[0].clientRequestId);
    });

    it('does the same for the tow-vehicle-only ticket', async () => {
      const world = makeWorld({ balance: 3 });
      world.queueExtraction({ fields: { manufacturer: 'Ford' } }, 'bad-request');
      const user = await reachTruckReview(world);

      await user.upload(fileInput(), photo('standalone.jpg'));

      const message = await screen.findByText(/nothing was used/i);
      expect(message).not.toHaveTextContent(/media_type/);
      expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Choose a different photo' })).toBeEnabled();
    });
  });

  describe('after a photo that cannot be sent', () => {
    it('says nothing was used and offers a different photo, not Try again', async () => {
      const world = makeWorld({ balance: 3 });
      const user = await reachTruckUpload(world);

      await chooseAndExtract(user, heic());

      expect(await screen.findByText(/nothing was used/i)).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Extract Data' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Choose a different photo' })).toBeInTheDocument();
      expect(world.requests).toHaveLength(0);
      expect(world.balance()).toBe(3);
    });

    it('does the same for the tow-vehicle-only ticket', async () => {
      const world = makeWorld({ balance: 3 });
      const user = await reachTruckReview(world);

      await user.upload(fileInput(), heic());

      expect(await screen.findByText(/nothing was used/i)).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Choose a different photo' })).toBeEnabled();
      expect(world.requests).toHaveLength(1);
    });
  });

  it('keeps offering Extract Data with the same photo after an answer that can be retried', async () => {
    const world = makeWorld({ balance: 3 });
    world.queueExtraction('fail');
    const user = await reachTruckUpload(world);

    await chooseAndExtract(user);

    expect(await screen.findByText(/your scan was refunded/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Extract Data' })).toBeEnabled();
    expect(screen.queryByRole('button', { name: 'Choose a different photo' })).not.toBeInTheDocument();
  });
});

describe('a Pro user with no scans', () => {
  it('is offered scan packs instead of a scan, and can come back to the same check', async () => {
    const world = makeWorld({ balance: 0 });
    const user = renderApp({ world });
    await startNewRig(user);

    expect(await screen.findByText(/out of scans/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Extract Data' })).not.toBeInTheDocument();
    expect(world.fetch).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Buy more scans' }));
    expect(await screen.findByText('10 scans')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Back to your check' }));
    expect(screen.getByText('Truck Compliance Label')).toBeInTheDocument();
  });

  it('can still type the numbers in instead', async () => {
    const world = makeWorld({ balance: 0 });
    const user = renderApp({ world });
    await startNewRig(user);
    await screen.findByText(/out of scans/i);

    await user.click(screen.getByRole('button', { name: "I don't have this image" }));

    expect(screen.getByText('Check the numbers')).toBeInTheDocument();
  });
});

describe('a Free user', () => {
  it('is prompted to upgrade instead of scanning, and nothing is sent', async () => {
    const world = makeWorld({ isPro: false, balance: 0 });
    const user = renderApp({ world });
    await startNewRig(user);

    expect(await screen.findByText(/part of RigCheck Pro/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Extract Data' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Upgrade to Pro' }));
    expect(await screen.findByRole('button', { name: 'Buy Pro' })).toBeInTheDocument();
    expect(world.fetch).not.toHaveBeenCalled();
  });

  it('is not offered the tow-vehicle-only ticket scan either', async () => {
    const world = makeWorld({ isPro: false, balance: 0 });
    const user = renderApp({ world });
    await startNewRig(user);
    await screen.findByText(/part of RigCheck Pro/i);

    await user.click(screen.getByRole('button', { name: "I don't have this image" }));

    expect(screen.queryByRole('button', { name: 'Scan tow-vehicle-only ticket' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Upgrade to Pro' })).toBeInTheDocument();
  });
});

describe('a visitor who is not signed in', () => {
  it('is asked to sign in instead of scanning', async () => {
    const world = makeWorld();
    const user = renderApp({ world, session: null });
    await startNewRig(user);

    expect(await screen.findByText(/sign in to scan/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Extract Data' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Sign in to scan' }));
    expect(await screen.findByLabelText('Email')).toBeInTheDocument();
    expect(world.fetch).not.toHaveBeenCalled();
  });
});

describe('a build without purchases', () => {
  it('says scanning is not available and keeps typing the numbers working', async () => {
    const user = renderApp({ world: null });
    await startNewRig(user);

    expect(await screen.findByText(/scanning isn't available/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Extract Data' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: "I don't have this image" }));
    expect(screen.getByText('Check the numbers')).toBeInTheDocument();
  });
});

describe('while the plan is still loading', () => {
  it('holds the scan back and says it is checking', async () => {
    const world = makeWorld();
    let release: () => void = () => {};
    world.billing.getStatus = vi.fn(
      () => new Promise<BillingStatus>((resolve) => (release = () => resolve({ isPro: true, scanBalance: 3 }))),
    );
    const user = renderApp({ world });
    await startNewRig(user);

    expect(await screen.findByText(/checking your scans/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Extract Data' })).not.toBeInTheDocument();

    release();
    expect(await screen.findByText(/3 scans left/)).toBeInTheDocument();
  });

  it('offers Try again when the plan would not load', async () => {
    const world = makeWorld();
    world.billing.getStatus = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ isPro: true, scanBalance: 3 });
    const user = renderApp({ world });
    await startNewRig(user);

    await user.click(await screen.findByRole('button', { name: 'Try again' }));

    expect(await screen.findByText(/3 scans left/)).toBeInTheDocument();
  });
});
