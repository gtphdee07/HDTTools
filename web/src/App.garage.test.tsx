import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { AuthProvider } from './auth';
import type { AuthClient, AuthSession } from './auth';
import { GarageFullError, GarageProvider } from './garage';
import type { GarageBackend } from './garage';
import type { RecentRig } from './types';

// Interaction tests for the account-synced Garage (#28): the real screens, a fake Supabase auth
// client and an in-memory Garage backend standing in for the account's table. The server's own
// rules (row-level security, the atomic cap, idempotent retry) are tested at the service boundary
// in garageSchema.test.ts and the live External suite; here the question is what the user sees.

const CAP = 2;

function makeFakeAccountGarage() {
  const stored = new Map<string, RecentRig & { key: string }>();
  const backend = {
    list: vi.fn(async (): Promise<RecentRig[]> =>
      [...stored.values()]
        .map(({ key: _key, ...rig }) => rig)
        .sort((a, b) => b.lastUsedAt.localeCompare(a.lastUsedAt)),
    ),
    addRig: vi.fn(async (key: string, rig: Pick<RecentRig, 'nickname' | 'truck' | 'trailer'>) => {
      if ([...stored.values()].some((r) => r.key === key)) return;
      if (stored.size >= CAP) throw new GarageFullError(CAP);
      stored.set(rig.nickname, { ...rig, id: `rig-${stored.size + 1}`, key, lastUsedAt: new Date().toISOString() });
    }),
    updateRig: vi.fn(async (rig: RecentRig) => {
      const current = stored.get(rig.nickname);
      if (current) stored.set(rig.nickname, { ...current, ...rig });
    }),
  } satisfies GarageBackend;
  return { backend, stored };
}

function signedInClient(email: string): AuthClient {
  let session: AuthSession | null = { access_token: `token-${email}`, user: { id: `id-${email}`, email } };
  const listeners = new Set<(event: string, s: AuthSession | null) => void>();
  return {
    getSession: vi.fn(async () => ({ data: { session }, error: null })),
    onAuthStateChange: vi.fn((cb: (event: string, s: AuthSession | null) => void) => {
      listeners.add(cb);
      return { data: { subscription: { unsubscribe: () => listeners.delete(cb) } } };
    }),
    signUp: vi.fn(),
    signInWithPassword: vi.fn(),
    signOut: vi.fn(async () => {
      session = null;
      listeners.forEach((l) => l('SIGNED_OUT', null));
      return { error: null };
    }),
    resetPasswordForEmail: vi.fn(),
    updateUser: vi.fn(),
  } as unknown as AuthClient;
}

function renderDevice(backend: GarageBackend, auth: AuthClient | null = signedInClient('a@example.com')) {
  render(
    <AuthProvider client={auth}>
      <GarageProvider backend={backend}>
        <App />
      </GarageProvider>
    </AuthProvider>,
  );
  return userEvent.setup();
}

async function finishCheckForNewRig(user: ReturnType<typeof userEvent.setup>, nickname: string) {
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

async function acknowledgeDisclaimer(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: 'I Understand — Continue' }));
}

async function goHome(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'Back to Dashboard' }));
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe('signed-in Garage', () => {
  it('saves a finished check’s Rig to the account, not the browser', async () => {
    const { backend, stored } = makeFakeAccountGarage();
    const user = renderDevice(backend);

    await finishCheckForNewRig(user, 'Big Blue');
    await acknowledgeDisclaimer(user);

    await waitFor(() => expect([...stored.keys()]).toEqual(['Big Blue']));
    expect(localStorage.getItem('rigcheck:recentRigs')).toBeNull();
  });

  it('shows a Rig saved on one device on another signed-in device', async () => {
    const { backend } = makeFakeAccountGarage();
    const phone = renderDevice(backend);
    await finishCheckForNewRig(phone, 'Big Blue');
    await acknowledgeDisclaimer(phone);
    await waitFor(() => expect(backend.addRig).toHaveBeenCalled());
    document.body.innerHTML = '';

    renderDevice(backend);

    expect(await screen.findByText('Big Blue')).toBeInTheDocument();
  });

  it('keeps the Rig list apart from this browser’s own while signed in, and returns to it after sign-out', async () => {
    localStorage.setItem(
      'rigcheck:recentRigs',
      JSON.stringify([{ nickname: 'Browser Rig', truck: {}, trailer: {}, lastUsedAt: new Date().toISOString() }]),
    );
    const { backend, stored } = makeFakeAccountGarage();
    stored.set('Account Rig', { nickname: 'Account Rig', truck: {}, trailer: {}, lastUsedAt: new Date().toISOString(), id: 'r1', key: 'k' });
    const user = renderDevice(backend);

    expect(await screen.findByText('Account Rig')).toBeInTheDocument();
    expect(screen.queryByText('Browser Rig')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Account' }));
    await user.click(await screen.findByRole('button', { name: 'Sign out' }));
    await user.click(screen.getAllByRole('button', { name: 'Dashboard' })[0]);

    expect(await screen.findByText('Browser Rig')).toBeInTheDocument();
    expect(screen.queryByText('Account Rig')).not.toBeInTheDocument();
  });

  it('retries a failed add with the same idempotency key and ends with one Rig', async () => {
    const { backend, stored } = makeFakeAccountGarage();
    const realAdd = backend.addRig.getMockImplementation()!;
    backend.addRig.mockRejectedValueOnce(new Error('network down'));
    backend.addRig.mockImplementation(realAdd);
    const user = renderDevice(backend);

    await finishCheckForNewRig(user, 'Big Blue');
    await acknowledgeDisclaimer(user);

    await waitFor(() => expect([...stored.keys()]).toEqual(['Big Blue']));
    expect(backend.addRig).toHaveBeenCalledTimes(2);
    const [firstKey] = backend.addRig.mock.calls[0];
    const [secondKey] = backend.addRig.mock.calls[1];
    expect(secondKey).toBe(firstKey);
  });

  it('tells the user when the Garage is full, still shows the check, and saves nothing', async () => {
    const { backend, stored } = makeFakeAccountGarage();
    const user = renderDevice(backend);
    await finishCheckForNewRig(user, 'Rig One');
    await acknowledgeDisclaimer(user);
    await goHome(user);
    await finishCheckForNewRig(user, 'Rig Two');
    await goHome(user);
    await finishCheckForNewRig(user, 'Rig Three');

    const notice = await screen.findByRole('status');
    expect(notice).toHaveTextContent(/garage is full/i);
    expect(notice).toHaveTextContent(String(CAP));
    expect(notice).toHaveTextContent('Rig Three');
    expect(screen.getByText('Not Enough Information')).toBeInTheDocument();
    expect([...stored.keys()].sort()).toEqual(['Rig One', 'Rig Two']);
  });

  it('says so, and still shows the check, when saving fails for another reason', async () => {
    const { backend } = makeFakeAccountGarage();
    backend.addRig.mockRejectedValue(new Error('network down'));
    const user = renderDevice(backend);

    await finishCheckForNewRig(user, 'Big Blue');
    await acknowledgeDisclaimer(user);

    const notice = await screen.findByRole('status');
    expect(notice).toHaveTextContent(/couldn.t save/i);
    expect(notice).toHaveTextContent('Big Blue');
    expect(screen.getByText('Not Enough Information')).toBeInTheDocument();
  });

  it('lets a Rig already in a full Garage be used again, updating it instead of adding', async () => {
    const { backend, stored } = makeFakeAccountGarage();
    for (const name of ['Rig One', 'Rig Two']) {
      stored.set(name, { nickname: name, truck: {}, trailer: {}, lastUsedAt: '2026-01-01T00:00:00.000Z', id: name, key: name });
    }
    const user = renderDevice(backend);

    await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
    await user.click(await screen.findByText('Rig One'));
    await user.click(screen.getByRole('button', { name: 'No Image / Enter Weight Manually' }));
    await user.click(screen.getByRole('button', { name: 'See My Results' }));
    await acknowledgeDisclaimer(user);

    await waitFor(() => expect(backend.updateRig).toHaveBeenCalledTimes(1));
    expect(backend.addRig).not.toHaveBeenCalled();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(stored.get('Rig One')!.lastUsedAt > '2026-01-01T00:00:00.000Z').toBe(true);
    expect(stored.size).toBe(CAP);
  });
});

describe('signed-out Garage', () => {
  it('still keeps Rigs in the browser and never touches the account backend', async () => {
    const { backend } = makeFakeAccountGarage();
    const user = renderDevice(backend, null);

    await finishCheckForNewRig(user, 'Big Blue');
    await acknowledgeDisclaimer(user);

    const stored: RecentRig[] = JSON.parse(localStorage.getItem('rigcheck:recentRigs') ?? '[]');
    expect(stored.map((r) => r.nickname)).toEqual(['Big Blue']);
    expect(backend.list).not.toHaveBeenCalled();
    expect(backend.addRig).not.toHaveBeenCalled();
    expect(within(document.body).queryByRole('status')).not.toBeInTheDocument();
  });
});
