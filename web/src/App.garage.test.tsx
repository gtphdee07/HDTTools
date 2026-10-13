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
    deleteRig: vi.fn(async (id: string) => {
      for (const [nickname, rig] of stored) if (rig.id === id) stored.delete(nickname);
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
  await finishCheckFromRigStep(user, nickname);
}

// From the Rig list: name a new Rig and run the check through to the results.
async function finishCheckFromRigStep(user: ReturnType<typeof userEvent.setup>, nickname: string) {
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

describe('signed-in Garage, changed elsewhere', () => {
  it('adds the Rig instead of failing when the one it meant to update was removed on another device', async () => {
    const { backend, stored } = makeFakeAccountGarage();
    stored.set('Rig One', { nickname: 'Rig One', truck: {}, trailer: {}, lastUsedAt: '2026-01-01T00:00:00.000Z', id: 'r1', key: 'k' });
    const user = renderDevice(backend);
    await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
    await user.click(await screen.findByText('Rig One'));
    stored.clear();
    backend.updateRig.mockRejectedValueOnce(new Error('rig_not_found'));
    await user.click(screen.getByRole('button', { name: 'No Image / Enter Weight Manually' }));
    await user.click(screen.getByRole('button', { name: 'See My Results' }));
    await acknowledgeDisclaimer(user);

    await waitFor(() => expect([...stored.keys()]).toEqual(['Rig One']));
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('keeps the newest Garage when an older refresh answers late', async () => {
    const { backend } = makeFakeAccountGarage();
    const realList = backend.list.getMockImplementation()!;
    // jsdom reports every document as "prerender"; the app only refreshes a visible one.
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
    const user = renderDevice(backend);
    await waitFor(() => expect(backend.list).toHaveBeenCalled());

    let answerLate!: (rigs: RecentRig[]) => void;
    backend.list.mockImplementationOnce(() => new Promise<RecentRig[]>((resolve) => (answerLate = resolve)));
    document.dispatchEvent(new Event('visibilitychange'));
    backend.list.mockImplementation(realList);

    await finishCheckForNewRig(user, 'Big Blue');
    await acknowledgeDisclaimer(user);
    await goHome(user);
    expect((await screen.findAllByText('Big Blue')).length).toBeGreaterThan(0);

    answerLate([]);
    await new Promise((r) => setTimeout(r, 20));
    // once as the Rig card, once as the check in Recent Checks
    expect(screen.getAllByText('Big Blue')).toHaveLength(2);
  });
});

function seedRigs(stored: Map<string, RecentRig & { key: string }>, ...names: string[]) {
  for (const name of names) {
    stored.set(name, { nickname: name, truck: {}, trailer: {}, lastUsedAt: '2026-01-01T00:00:00.000Z', id: `id-${name}`, key: name });
  }
}

async function openRigList(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
}

async function deleteRig(user: ReturnType<typeof userEvent.setup>, nickname: string) {
  await user.click(await screen.findByRole('button', { name: `Delete ${nickname}` }));
  await user.click(screen.getByRole('button', { name: 'Yes, delete' }));
}

describe('deleting a Rig from the signed-in Garage', () => {
  it('removes the Rig from the account after the user confirms, and from the list', async () => {
    const { backend, stored } = makeFakeAccountGarage();
    seedRigs(stored, 'Rig One', 'Rig Two');
    const user = renderDevice(backend);
    await openRigList(user);

    await deleteRig(user, 'Rig One');

    await waitFor(() => expect(screen.queryByText('Rig One')).not.toBeInTheDocument());
    expect([...stored.keys()]).toEqual(['Rig Two']);
    expect(screen.getByText('Rig Two')).toBeInTheDocument();
  });

  it('still shows the freed slot when the list cannot be re-read right after the delete', async () => {
    const { backend, stored } = makeFakeAccountGarage();
    seedRigs(stored, 'Rig One', 'Rig Two');
    const user = renderDevice(backend);
    await openRigList(user);
    await screen.findByText('Rig One');
    backend.list.mockRejectedValue(new Error('offline'));

    await deleteRig(user, 'Rig One');

    await waitFor(() => expect(screen.queryByText('Rig One')).not.toBeInTheDocument());
    expect(screen.getByText('Rig Two')).toBeInTheDocument();
  });

  it('is gone on another signed-in device after it refreshes', async () => {
    const { backend, stored } = makeFakeAccountGarage();
    seedRigs(stored, 'Rig One', 'Rig Two');
    const phone = renderDevice(backend);
    await openRigList(phone);
    await deleteRig(phone, 'Rig One');
    await waitFor(() => expect(backend.deleteRig).toHaveBeenCalled());
    document.body.innerHTML = '';

    renderDevice(backend);

    expect(await screen.findByText('Rig Two')).toBeInTheDocument();
    expect(screen.queryByText('Rig One')).not.toBeInTheDocument();
  });

  it('lets the user save a new Rig after deleting one from a full Garage', async () => {
    const { backend, stored } = makeFakeAccountGarage();
    seedRigs(stored, 'Rig One', 'Rig Two');
    const user = renderDevice(backend);
    await openRigList(user);
    await deleteRig(user, 'Rig One');
    await waitFor(() => expect(screen.queryByText('Rig One')).not.toBeInTheDocument());

    await finishCheckFromRigStep(user, 'Rig Three');
    await acknowledgeDisclaimer(user);

    await waitFor(() => expect([...stored.keys()].sort()).toEqual(['Rig Three', 'Rig Two']));
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('deletes nothing when the user cancels the confirmation', async () => {
    const { backend, stored } = makeFakeAccountGarage();
    seedRigs(stored, 'Rig One');
    const user = renderDevice(backend);
    await openRigList(user);

    await user.click(await screen.findByRole('button', { name: 'Delete Rig One' }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(backend.deleteRig).not.toHaveBeenCalled();
    expect(screen.getByText('Rig One')).toBeInTheDocument();
    expect([...stored.keys()]).toEqual(['Rig One']);
  });

  it('shows an error and keeps the Rig when the delete fails', async () => {
    const { backend, stored } = makeFakeAccountGarage();
    seedRigs(stored, 'Rig One');
    backend.deleteRig.mockRejectedValue(new Error('network down'));
    const user = renderDevice(backend);
    await openRigList(user);

    await deleteRig(user, 'Rig One');

    expect(await screen.findByRole('alert')).toHaveTextContent(/couldn.t delete.*Rig One/i);
    expect(screen.getByText('Rig One')).toBeInTheDocument();
    expect([...stored.keys()]).toEqual(['Rig One']);
  });

  it('only ever asks the backend to delete the chosen Rig, by id', async () => {
    const { backend, stored } = makeFakeAccountGarage();
    seedRigs(stored, 'Rig One', 'Rig Two');
    const user = renderDevice(backend);
    await openRigList(user);

    await deleteRig(user, 'Rig Two');

    await waitFor(() => expect(backend.deleteRig).toHaveBeenCalledTimes(1));
    expect(backend.deleteRig).toHaveBeenCalledWith('id-Rig Two');
  });
});

describe('the signed-out Garage', () => {
  it('offers no way to delete a Rig, and leaves the browser’s own list alone', async () => {
    localStorage.setItem(
      'rigcheck:recentRigs',
      JSON.stringify([
        { nickname: 'Browser One', truck: {}, trailer: {}, lastUsedAt: '2026-01-02T00:00:00.000Z' },
        { nickname: 'Browser Two', truck: {}, trailer: {}, lastUsedAt: '2026-01-01T00:00:00.000Z' },
      ]),
    );
    const { backend } = makeFakeAccountGarage();
    const user = renderDevice(backend, null);
    await openRigList(user);

    expect(await screen.findByText('Browser One')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Delete / })).not.toBeInTheDocument();
    const kept: RecentRig[] = JSON.parse(localStorage.getItem('rigcheck:recentRigs') ?? '[]');
    expect(kept.map((r) => r.nickname)).toEqual(['Browser One', 'Browser Two']);
    expect(backend.deleteRig).not.toHaveBeenCalled();
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

// Rigs a visitor saved in this browser before signing in (#91): offered for import on first
// sign-in, never forced, and never duplicated by a retry.

const LOCAL_KEY = 'rigcheck:recentRigs';

function seedBrowserRigs(...names: string[]) {
  localStorage.setItem(
    LOCAL_KEY,
    JSON.stringify(
      names.map((nickname, i) => ({
        nickname,
        truck: { manufacturer: `Truck ${nickname}` },
        trailer: {},
        lastUsedAt: new Date(Date.UTC(2026, 0, 10 - i)).toISOString(),
      })),
    ),
  );
}

const browserRigNames = (): string[] =>
  (JSON.parse(localStorage.getItem(LOCAL_KEY) ?? '[]') as RecentRig[]).map((r) => r.nickname);

// A visitor who is signed out until they sign in with this email (any password).
function signableClient(email: string): AuthClient {
  let session: AuthSession | null = null;
  const listeners = new Set<(event: string, s: AuthSession | null) => void>();
  const emit = (event: string, s: AuthSession | null) => {
    session = s;
    listeners.forEach((l) => l(event, s));
  };
  return {
    getSession: vi.fn(async () => ({ data: { session }, error: null })),
    onAuthStateChange: vi.fn((cb: (event: string, s: AuthSession | null) => void) => {
      listeners.add(cb);
      return { data: { subscription: { unsubscribe: () => listeners.delete(cb) } } };
    }),
    signUp: vi.fn(),
    signInWithPassword: vi.fn(async () => {
      emit('SIGNED_IN', { access_token: `token-${email}`, user: { id: `id-${email}`, email } });
      return { data: null, error: null };
    }),
    signOut: vi.fn(async () => {
      emit('SIGNED_OUT', null);
      return { error: null };
    }),
    resetPasswordForEmail: vi.fn(),
    updateUser: vi.fn(),
  } as unknown as AuthClient;
}

async function signInThroughAccount(user: ReturnType<typeof userEvent.setup>, email: string) {
  await user.click(screen.getAllByRole('button', { name: 'Sign in' })[0]);
  await user.type(screen.getByLabelText('Email'), email);
  await user.type(screen.getByLabelText('Password'), 'correct horse');
  await user.click(screen.getAllByRole('button', { name: 'Sign in' }).at(-1)!);
}

const importOffer = () => screen.queryByRole('region', { name: 'Import browser Rigs' });
const clickImport = async (user: ReturnType<typeof userEvent.setup>) =>
  user.click(await screen.findByRole('button', { name: 'Import to my Garage' }));

describe('importing browser-saved Rigs on first sign-in', () => {
  it('offers on first sign-in, adds nothing until the user accepts, then adds the Rigs to the account', async () => {
    seedBrowserRigs('Big Blue', 'Little Red');
    const { backend, stored } = makeFakeAccountGarage();
    const user = renderDevice(backend, signableClient('a@example.com'));
    expect(importOffer()).not.toBeInTheDocument();

    await signInThroughAccount(user, 'a@example.com');

    const offer = await screen.findByRole('region', { name: 'Import browser Rigs' });
    expect(offer).toHaveTextContent(/2 Rigs/);
    expect(backend.addRig).not.toHaveBeenCalled();

    await clickImport(user);

    expect(await screen.findByRole('status')).toHaveTextContent(/imported 2 rigs/i);
    expect([...stored.keys()].sort()).toEqual(['Big Blue', 'Little Red']);
    expect(stored.get('Big Blue')!.truck).toEqual({ manufacturer: 'Truck Big Blue' });
    expect(importOffer()).not.toBeInTheDocument();
  });

  it('sends each Rig under its own idempotency key', async () => {
    seedBrowserRigs('Big Blue', 'Little Red');
    const { backend } = makeFakeAccountGarage();
    const user = renderDevice(backend);

    await clickImport(user);
    await screen.findByRole('status');

    const keys = backend.addRig.mock.calls.map(([key]) => key);
    expect(keys).toHaveLength(2);
    expect(new Set(keys).size).toBe(2);
  });

  it('leaves the browser’s own Rigs in place after importing them', async () => {
    seedBrowserRigs('Big Blue', 'Little Red');
    const { backend } = makeFakeAccountGarage();
    const user = renderDevice(backend);

    await clickImport(user);
    await screen.findByRole('status');

    expect(browserRigNames()).toEqual(['Big Blue', 'Little Red']);
  });

  it('does not import Rigs that would exceed the Free cap, and names the ones left out', async () => {
    seedBrowserRigs('Rig One', 'Rig Two', 'Rig Three', 'Rig Four');
    const { backend, stored } = makeFakeAccountGarage();
    const user = renderDevice(backend);

    await clickImport(user);

    const result = await screen.findByRole('status');
    expect(result).toHaveTextContent(/imported 2 rigs/i);
    expect(result).toHaveTextContent(/garage is full/i);
    expect(result).toHaveTextContent(String(CAP));
    expect(result).toHaveTextContent('Rig Three');
    expect(result).toHaveTextContent('Rig Four');
    expect(result).not.toHaveTextContent('Rig One');
    expect([...stored.keys()].sort()).toEqual(['Rig One', 'Rig Two']);
    expect(browserRigNames()).toEqual(['Rig One', 'Rig Two', 'Rig Three', 'Rig Four']);
  });

  it('counts the Rigs already in the account against the cap', async () => {
    seedBrowserRigs('Browser One', 'Browser Two');
    const { backend, stored } = makeFakeAccountGarage();
    seedRigs(stored, 'Account Rig');
    const user = renderDevice(backend);

    await clickImport(user);

    const result = await screen.findByRole('status');
    expect(result).toHaveTextContent(/imported 1 rig\b/i);
    expect(result).toHaveTextContent('Browser Two');
    expect([...stored.keys()].sort()).toEqual(['Account Rig', 'Browser One']);
  });

  it('leaves a Rig already in the account under the same nickname as it is, and says so', async () => {
    seedBrowserRigs('Big Blue');
    const { backend, stored } = makeFakeAccountGarage();
    seedRigs(stored, 'big blue');
    const user = renderDevice(backend);

    await clickImport(user);

    const result = await screen.findByRole('status');
    expect(result).toHaveTextContent(/already in your garage/i);
    expect(result).toHaveTextContent('Big Blue');
    expect(backend.addRig).not.toHaveBeenCalled();
    expect(backend.updateRig).not.toHaveBeenCalled();
    expect(stored.get('big blue')!.truck).toEqual({});
  });

  it('keeps the offer open after an interruption, and a retry creates no duplicates', async () => {
    seedBrowserRigs('Big Blue', 'Little Red');
    const { backend, stored } = makeFakeAccountGarage();
    const realAdd = backend.addRig.getMockImplementation()!;
    // The second Rig's request lands on the server but its reply is lost.
    backend.addRig.mockImplementationOnce(realAdd);
    backend.addRig.mockImplementationOnce(async (key, rig) => {
      await realAdd(key, rig);
      throw new Error('network down');
    });
    backend.addRig.mockImplementation(realAdd);
    const user = renderDevice(backend);

    await clickImport(user);

    expect(await screen.findByRole('alert')).toHaveTextContent(/didn.t finish/i);
    await user.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('status')).toHaveTextContent(/imported/i);
    expect([...stored.keys()].sort()).toEqual(['Big Blue', 'Little Red']);
    const littleRedKeys = backend.addRig.mock.calls.filter(([, rig]) => rig.nickname === 'Little Red').map(([key]) => key);
    expect(littleRedKeys).toHaveLength(2);
    expect(littleRedKeys[1]).toBe(littleRedKeys[0]);
  });

  it('offers again on the next visit when the import never finished', async () => {
    seedBrowserRigs('Big Blue');
    const { backend } = makeFakeAccountGarage();
    backend.addRig.mockRejectedValueOnce(new Error('network down'));
    const user = renderDevice(backend);
    await clickImport(user);
    await screen.findByRole('alert');
    document.body.innerHTML = '';

    renderDevice(backend);

    expect(await screen.findByRole('region', { name: 'Import browser Rigs' })).toBeInTheDocument();
  });

  it('keeps the browser’s Rigs and does not offer again when the user declines', async () => {
    seedBrowserRigs('Big Blue');
    const { backend, stored } = makeFakeAccountGarage();
    const user = renderDevice(backend);

    await user.click(await screen.findByRole('button', { name: 'No thanks' }));

    expect(importOffer()).not.toBeInTheDocument();
    expect(browserRigNames()).toEqual(['Big Blue']);
    document.body.innerHTML = '';
    renderDevice(backend);
    await waitFor(() => expect(backend.list).toHaveBeenCalledTimes(2));
    expect(importOffer()).not.toBeInTheDocument();
    expect(backend.addRig).not.toHaveBeenCalled();
    expect(stored.size).toBe(0);
  });

  it('does not offer again after an import, even on a later visit', async () => {
    seedBrowserRigs('Big Blue');
    const { backend } = makeFakeAccountGarage();
    const user = renderDevice(backend);
    await clickImport(user);
    await screen.findByRole('status');
    document.body.innerHTML = '';
    backend.list.mockClear();

    renderDevice(backend);

    await waitFor(() => expect(backend.list).toHaveBeenCalled());
    expect(importOffer()).not.toBeInTheDocument();
  });

  it('makes its own offer to a different account on the same browser', async () => {
    seedBrowserRigs('Big Blue');
    const { backend } = makeFakeAccountGarage();
    const first = renderDevice(backend, signedInClient('a@example.com'));
    await first.click(await screen.findByRole('button', { name: 'No thanks' }));
    document.body.innerHTML = '';

    renderDevice(backend, signedInClient('b@example.com'));

    expect(await screen.findByRole('region', { name: 'Import browser Rigs' })).toBeInTheDocument();
  });

  it('makes no offer when the browser holds no Rigs, or when signed out', async () => {
    const { backend } = makeFakeAccountGarage();
    renderDevice(backend);
    await waitFor(() => expect(backend.list).toHaveBeenCalled());
    expect(importOffer()).not.toBeInTheDocument();
    document.body.innerHTML = '';

    seedBrowserRigs('Big Blue');
    renderDevice(backend, null);
    expect(importOffer()).not.toBeInTheDocument();
  });

  it('shows the imported Rigs in the Rig list straight away', async () => {
    seedBrowserRigs('Big Blue');
    const { backend } = makeFakeAccountGarage();
    const user = renderDevice(backend);

    await clickImport(user);
    await screen.findByRole('status');
    await openRigList(user);

    expect(await screen.findByText('Big Blue')).toBeInTheDocument();
  });
});
