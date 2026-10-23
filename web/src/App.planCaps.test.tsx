import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { AuthProvider } from './auth';
import type { AuthClient, AuthSession } from './auth';
import { BillingProvider } from './billing';
import type { BillingClient, ScanRecheck } from './billing';
import { GarageFullError, GarageProvider } from './garage';
import type { GarageBackend } from './garage';
import { HistoryProvider } from './history';
import type { HistoryBackend } from './history';
import type { Plan } from './plan';
import type { HistoryEntry, RecentRig } from './types';

// Interaction tests for Pro raising the Garage and History caps (#30): the real screens, a fake Supabase
// auth client, a fake RevenueCat client and in-memory Garage and History stores that apply a cap by the plan
// the app reports, the way add_rig and add_history_entry do. The database's own rule (which cap a plan, or
// an unknown plan, gets) is pinned in planCapsSchema.test.ts; here the question is what the app reports and
// what the user sees. The cap numbers below are this file's own, small enough to fill by hand; the real
// ones live in the plan_caps table.

const CAPS = { free: { rigs: 2, checks: 3 }, pro: { rigs: 4, checks: 5 } };
// What the database does with a plan: an unknown one (null) is held to the Free Garage cap, but History is
// kept to the Pro count so a failed read never prunes a Pro account's checks.
const garageCapFor = (plan: Plan | null) => (plan === 'pro' ? CAPS.pro.rigs : CAPS.free.rigs);
const historyCapFor = (plan: Plan | null) => (plan === 'free' ? CAPS.free.checks : CAPS.pro.checks);

const SESSION: AuthSession = { access_token: 'token-pat', user: { id: 'acct-pat', email: 'pat@example.com' } };

function signedInAuth(): AuthClient {
  return {
    getSession: vi.fn(async () => ({ data: { session: SESSION }, error: null })),
    onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: () => {} } } })),
    signUp: vi.fn(),
    signInWithPassword: vi.fn(),
    signOut: vi.fn(),
    resetPasswordForEmail: vi.fn(),
    updateUser: vi.fn(),
  } as unknown as AuthClient;
}

function makeBilling({ pro = false, readFails = false }: { pro?: boolean; readFails?: boolean } = {}) {
  let isPro = pro;
  let failing = readFails;
  const client = {
    identify: vi.fn(async () => {}),
    getProOffer: vi.fn(async () => ({ price: '$9.99' })),
    getScanPacks: vi.fn(async () => []),
    getStatus: vi.fn(async () => {
      if (failing) throw new Error('RevenueCat is down');
      return { isPro, scanBalance: isPro ? 5 : 0 };
    }),
    purchasePro: vi.fn(async () => {
      isPro = true;
      return 'purchased' as const;
    }),
    purchaseScanPack: vi.fn(),
  };
  return {
    client: client as unknown as BillingClient & typeof client,
    // Pro bought on another device: this device's RevenueCat read now says Pro.
    boughtElsewhere: () => {
      isPro = true;
    },
    recover: () => {
      failing = false;
    },
  };
}

function makeGarage(initial: string[] = []) {
  const stored = new Map<string, RecentRig>(
    initial.map((nickname, i) => [nickname, { id: `rig-${i}`, nickname, truck: {}, trailer: {}, lastUsedAt: '2026-01-01T00:00:00.000Z' }]),
  );
  const backend = {
    list: vi.fn(async () => [...stored.values()]),
    addRig: vi.fn(async (_key: string, rig: Pick<RecentRig, 'nickname' | 'truck' | 'trailer'>, plan: Plan | null) => {
      if (stored.size >= garageCapFor(plan)) throw new GarageFullError(garageCapFor(plan));
      stored.set(rig.nickname, { ...rig, id: `rig-${stored.size}`, lastUsedAt: new Date().toISOString() });
    }),
    updateRig: vi.fn(async () => {}),
    deleteRig: vi.fn(async () => {}),
  } satisfies GarageBackend;
  return { backend, stored };
}

function makeHistory(count = 0) {
  const stored: HistoryEntry[] = Array.from({ length: count }, (_, i) => ({
    id: `h-${count - i}`,
    date: 'Oct 01, 2026',
    rigNickname: `Old ${count - i}`,
    verdict: 'pass' as const,
  }));
  const backend = {
    list: vi.fn(async () => [...stored]),
    addEntry: vi.fn(async (_key: string, entry: Pick<HistoryEntry, 'rigNickname' | 'verdict'>, plan: Plan | null) => {
      stored.unshift({ id: `h-new-${stored.length}`, date: 'Oct 22, 2026', ...entry });
      stored.length = Math.min(stored.length, historyCapFor(plan));
    }),
    caps: vi.fn(async () => ({ free: CAPS.free.checks, pro: CAPS.pro.checks })),
  } satisfies HistoryBackend;
  return { backend, stored };
}

const RECHECK: ScanRecheck = { intervalMs: 10, windowMs: 100, checkTimeoutMs: 50 };

type User = ReturnType<typeof userEvent.setup>;

function renderApp(
  billing: ReturnType<typeof makeBilling>,
  garage: ReturnType<typeof makeGarage>,
  history: ReturnType<typeof makeHistory> = makeHistory(),
) {
  render(
    <AuthProvider client={signedInAuth()}>
      <BillingProvider client={billing.client} scanRecheck={RECHECK}>
        <GarageProvider backend={garage.backend}>
          <HistoryProvider backend={history.backend}>
            <App />
          </HistoryProvider>
        </GarageProvider>
      </BillingProvider>
    </AuthProvider>,
  );
  return userEvent.setup();
}

// Waits until the app has read the account's plan: the Account screen only says "Free plan" or "Pro plan" then.
async function planLoaded(user: User, plan: 'Free' | 'Pro') {
  await user.click(await screen.findByRole('button', { name: 'Account' }));
  await screen.findByText(`${plan} plan`);
  await user.click(screen.getByRole('button', { name: 'Back to Dashboard' }));
}

async function finishCheckForNewRig(user: User, nickname: string) {
  await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
  await user.type(screen.getByPlaceholderText('e.g. Big Blue'), nickname);
  await user.click(screen.getByRole('button', { name: 'Start New Rig' }));
  await user.click(screen.getByRole('button', { name: "I don't have this image" }));
  await user.click(screen.getByRole('button', { name: 'Next: Trailer Tag' }));
  await user.click(screen.getByRole('button', { name: "I don't have this image" }));
  await user.click(screen.getByRole('button', { name: 'Next: Scale Ticket' }));
  await user.click(screen.getByRole('button', { name: 'No Image / Enter Weight Manually' }));
  await user.click(screen.getByRole('button', { name: 'See My Results' }));
}

const acknowledgeDisclaimer = async (user: User) =>
  user.click(await screen.findByRole('button', { name: 'I Understand — Continue' }));

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe('Garage cap by plan', () => {
  it('tells a Free user at the cap that Pro would make room, and leads to buying it, then back to the check', async () => {
    const garage = makeGarage(['Rig One', 'Rig Two']);
    const user = renderApp(makeBilling(), garage);
    await planLoaded(user, 'Free');

    await finishCheckForNewRig(user, 'Rig Three');
    await acknowledgeDisclaimer(user);

    expect(await screen.findByText(/garage is full \(the Free plan holds 2 Rigs\)/i)).toBeInTheDocument();
    expect(garage.stored.has('Rig Three')).toBe(false);
    await user.click(screen.getByRole('button', { name: 'Upgrade to Pro' }));
    expect(await screen.findByText('Free plan')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Buy Pro' }));
    expect(await screen.findByText('Pro plan')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Back to your check' }));
    expect(screen.getByText('Not Enough Information')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
  });

  it('saves a Rig beyond the Free cap straight after buying Pro, with no reload', async () => {
    const garage = makeGarage(['Rig One', 'Rig Two']);
    const user = renderApp(makeBilling(), garage);
    await planLoaded(user, 'Free');
    await user.click(screen.getByRole('button', { name: 'Account' }));
    await user.click(await screen.findByRole('button', { name: 'Buy Pro' }));
    await screen.findByText('Pro plan');
    await user.click(screen.getByRole('button', { name: 'Back to Dashboard' }));

    await finishCheckForNewRig(user, 'Rig Three');
    await acknowledgeDisclaimer(user);

    await waitFor(() => expect(garage.stored.has('Rig Three')).toBe(true));
    expect(garage.backend.addRig).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({ nickname: 'Rig Three' }), 'pro');
    expect(screen.queryByText(/garage is full/i)).not.toBeInTheDocument();
  });

  it('reports Free to the database for a Free account, so it is held to the Free cap', async () => {
    const garage = makeGarage();
    const user = renderApp(makeBilling(), garage);
    await planLoaded(user, 'Free');

    await finishCheckForNewRig(user, 'Rig One');
    await acknowledgeDisclaimer(user);

    await waitFor(() => expect(garage.backend.addRig).toHaveBeenCalled());
    expect(garage.backend.addRig.mock.calls[0][2]).toBe('free');
  });

  it('holds more Rigs for a Pro account than the Free cap, and offers no upgrade when even Pro is full', async () => {
    const garage = makeGarage(Array.from({ length: CAPS.pro.rigs }, (_, i) => `Rig ${i + 1}`));
    const user = renderApp(makeBilling({ pro: true }), garage);
    await planLoaded(user, 'Pro');

    await finishCheckForNewRig(user, 'One More');
    await acknowledgeDisclaimer(user);

    expect(await screen.findByText(new RegExp(`garage is full \\(Pro holds ${CAPS.pro.rigs} Rigs\\)`, 'i'))).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
    expect(CAPS.pro.rigs).toBeGreaterThan(CAPS.free.rigs);
  });

  it('picks up Pro bought on another device when this tab is shown again, so the larger cap applies here too', async () => {
    const billing = makeBilling();
    const garage = makeGarage(['Rig One', 'Rig Two']);
    // jsdom reports every document as "prerender"; the app only looks again at a visible one.
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
    const user = renderApp(billing, garage);
    await planLoaded(user, 'Free');

    billing.boughtElsewhere();
    document.dispatchEvent(new Event('visibilitychange'));
    await user.click(screen.getByRole('button', { name: 'Account' }));
    await screen.findByText('Pro plan');
    await user.click(screen.getByRole('button', { name: 'Back to Dashboard' }));
    await finishCheckForNewRig(user, 'Rig Three');
    await acknowledgeDisclaimer(user);

    await waitFor(() => expect(garage.stored.has('Rig Three')).toBe(true));
    expect(garage.backend.addRig.mock.calls[0][2]).toBe('pro');
  });

  it('keeps a Pro account on its Pro cap when a read on showing the tab lags and says Free', async () => {
    const billing = makeBilling({ pro: true });
    const garage = makeGarage(Array.from({ length: CAPS.free.rigs }, (_, i) => `Rig ${i + 1}`));
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
    const user = renderApp(billing, garage);
    await planLoaded(user, 'Pro');

    // RevenueCat's read behind a purchase can lag; showing the tab again must not take Pro away.
    const reads = billing.client.getStatus.mock.calls.length;
    billing.client.getStatus.mockResolvedValue({ isPro: false, scanBalance: 0 });
    document.dispatchEvent(new Event('visibilitychange'));
    await waitFor(() => expect(billing.client.getStatus.mock.calls.length).toBeGreaterThan(reads));
    await finishCheckForNewRig(user, 'One More');
    await acknowledgeDisclaimer(user);

    await waitFor(() => expect(garage.stored.has('One More')).toBe(true));
    expect(garage.backend.addRig.mock.calls[0][2]).toBe('pro');
    expect(CAPS.free.rigs).toBeLessThan(CAPS.pro.rigs);
  });

  it('reports an unreadable plan as unknown, and offers no upgrade it cannot stand behind', async () => {
    const garage = makeGarage(['Rig One', 'Rig Two']);
    const billing = makeBilling({ readFails: true });
    const user = renderApp(billing, garage);
    await waitFor(() => expect(billing.client.getStatus).toHaveBeenCalled());

    await finishCheckForNewRig(user, 'Rig Three');
    await acknowledgeDisclaimer(user);

    await waitFor(() => expect(garage.backend.addRig).toHaveBeenCalled());
    expect(garage.backend.addRig.mock.calls[0][2]).toBeNull();
    expect(await screen.findByText(/couldn't check your plan/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
  });

  it('imports every browser Rig a Pro account has room for, past the Free cap', async () => {
    localStorage.setItem(
      'rigcheck:recentRigs',
      JSON.stringify(['Alpha', 'Bravo', 'Charlie'].map((nickname, i) => ({ nickname, truck: {}, trailer: {}, lastUsedAt: `2026-01-0${i + 1}T00:00:00.000Z` }))),
    );
    const garage = makeGarage();
    const user = renderApp(makeBilling({ pro: true }), garage);
    await planLoaded(user, 'Pro');

    await user.click(await screen.findByRole('button', { name: 'Import to my Garage' }));

    await waitFor(() => expect([...garage.stored.keys()].sort()).toEqual(['Alpha', 'Bravo', 'Charlie']));
    expect(CAPS.free.rigs).toBeLessThan(3);
    expect(garage.backend.addRig.mock.calls.every(([, , plan]) => plan === 'pro')).toBe(true);
  });

  it('names the Free cap and leads to Pro when an import does not fit', async () => {
    localStorage.setItem(
      'rigcheck:recentRigs',
      JSON.stringify(['Alpha', 'Bravo', 'Charlie'].map((nickname, i) => ({ nickname, truck: {}, trailer: {}, lastUsedAt: `2026-01-0${i + 1}T00:00:00.000Z` }))),
    );
    const garage = makeGarage();
    const user = renderApp(makeBilling(), garage);
    await planLoaded(user, 'Free');

    await user.click(await screen.findByRole('button', { name: 'Import to my Garage' }));

    const banner = await screen.findByText(/the Free plan holds 2 Rigs/i);
    expect(banner).toBeInTheDocument();
    await user.click(within(banner.parentElement!).getByRole('button', { name: 'Upgrade to Pro' }));
    expect(await screen.findByText('Free plan')).toBeInTheDocument();
  });
});

describe('History cap by plan', () => {
  const goHistory = (user: User) => user.click(screen.getAllByRole('button', { name: 'History' })[0]);

  it('tells a Free user whose History is full what Free keeps and Pro keeps, and leads to buying Pro', async () => {
    const user = renderApp(makeBilling(), makeGarage(), makeHistory(CAPS.free.checks));
    await planLoaded(user, 'Free');

    await goHistory(user);

    expect(await screen.findByText(new RegExp(`Free plan keeps your last ${CAPS.free.checks} checks.*Pro keeps your last ${CAPS.pro.checks}`))).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Upgrade to Pro' }));
    expect(await screen.findByText('Free plan')).toBeInTheDocument();
  });

  it('says nothing about the cap while a Free user’s History has room', async () => {
    const user = renderApp(makeBilling(), makeGarage(), makeHistory(CAPS.free.checks - 1));
    await planLoaded(user, 'Free');
    await goHistory(user);
    expect(await screen.findAllByText('Old 1')).not.toHaveLength(0);
    expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
  });

  it('shows no upgrade to a Pro user with a History as full as a Free one', async () => {
    const user = renderApp(makeBilling({ pro: true }), makeGarage(), makeHistory(CAPS.free.checks));
    await planLoaded(user, 'Pro');

    await goHistory(user);

    expect(await screen.findAllByText('Old 1')).not.toHaveLength(0);
    expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
  });

  it('reports the plan with each finished check, so a Pro account keeps more of them than a Free one', async () => {
    const history = makeHistory(CAPS.free.checks);
    const user = renderApp(makeBilling({ pro: true }), makeGarage(), history);
    await planLoaded(user, 'Pro');

    await finishCheckForNewRig(user, 'Big Blue');
    await acknowledgeDisclaimer(user);

    await waitFor(() => expect(history.backend.addEntry).toHaveBeenCalled());
    expect(history.backend.addEntry.mock.calls[0][2]).toBe('pro');
    await waitFor(() => expect(history.stored).toHaveLength(CAPS.free.checks + 1));
  });
});
