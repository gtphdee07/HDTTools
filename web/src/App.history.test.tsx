import { act, render, renderHook, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { AuthProvider } from './auth';
import type { AuthClient, AuthSession } from './auth';
import { HistoryProvider, useHistory } from './history';
import type { HistoryBackend } from './history';
import type { HistoryEntry } from './types';

// Interaction tests for the account-synced History (#29): the real screens, a fake Supabase auth
// client and an in-memory History backend standing in for the account's table. The server's own rules
// (row-level security, the count cap with oldest-entry pruning, idempotent retry) are tested at the
// service boundary in historySchema.test.ts and the live External suite; here the question is what the
// user sees.

function makeFakeAccountHistory() {
  const stored: Array<HistoryEntry & { key: string }> = [];
  const backend = {
    list: vi.fn(async (): Promise<HistoryEntry[]> => stored.map(({ key: _key, ...entry }) => entry)),
    addEntry: vi.fn(async (key: string, entry: Pick<HistoryEntry, 'rigNickname' | 'verdict'>) => {
      if (stored.some((e) => e.key === key)) return;
      stored.unshift({ id: `h-${stored.length + 1}`, date: 'Oct 22, 2026', ...entry, key });
    }),
  } satisfies HistoryBackend;
  return { backend, stored };
}

// A fake auth client that starts signed in (or out), and can sign in later like a visitor completing the form.
function fakeAuth(email: string | null) {
  let session: AuthSession | null = email ? { access_token: `token-${email}`, user: { id: `id-${email}`, email } } : null;
  const listeners = new Set<(event: string, s: AuthSession | null) => void>();
  const client = {
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
  const signIn = (as: string) =>
    act(() => {
      session = { access_token: `token-${as}`, user: { id: `id-${as}`, email: as } };
      listeners.forEach((l) => l('SIGNED_IN', session));
    });
  return { client, signIn };
}

function renderDevice(backend: HistoryBackend, auth: AuthClient | null) {
  render(
    <AuthProvider client={auth}>
      <HistoryProvider backend={backend}>
        <App />
      </HistoryProvider>
    </AuthProvider>,
  );
  return userEvent.setup();
}

type User = ReturnType<typeof userEvent.setup>;

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
const goHome = (user: User) => user.click(screen.getByRole('button', { name: 'Back to Dashboard' }));
const goHistory = (user: User) => user.click(screen.getAllByRole('button', { name: 'History' })[0]);

// A check's Rig shows twice on the History screen, as a filter pill (a button) and in its row; this is the row.
async function findHistoryRow(nickname: string) {
  const matches = await screen.findAllByText(nickname);
  const row = matches.find((el) => el.tagName !== 'BUTTON');
  expect(row, `${nickname} should have a row on the History screen`).toBeDefined();
  return row!;
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe('signed-in History', () => {
  it('saves a finished check to the account and lists it on the History screen', async () => {
    const { backend, stored } = makeFakeAccountHistory();
    const user = renderDevice(backend, fakeAuth('a@example.com').client);

    await finishCheckForNewRig(user, 'Big Blue');
    await acknowledgeDisclaimer(user);
    await waitFor(() => expect(stored.map((e) => e.rigNickname)).toEqual(['Big Blue']));
    await goHome(user);
    await goHistory(user);

    expect(await findHistoryRow('Big Blue')).toBeInTheDocument();
    expect(screen.getByText('Not Enough Info')).toBeInTheDocument();
    expect(stored[0].verdict).toBe('insufficient');
  });

  it('shows a check made on one device in History on another signed-in device', async () => {
    const { backend } = makeFakeAccountHistory();
    const phone = renderDevice(backend, fakeAuth('a@example.com').client);
    await finishCheckForNewRig(phone, 'Big Blue');
    await acknowledgeDisclaimer(phone);
    await waitFor(() => expect(backend.addEntry).toHaveBeenCalled());
    document.body.innerHTML = '';

    const laptop = renderDevice(backend, fakeAuth('a@example.com').client);
    await goHistory(laptop);

    expect(await findHistoryRow('Big Blue')).toBeInTheDocument();
  });

  it('picks up a check made on another device when History is opened', async () => {
    const { backend, stored } = makeFakeAccountHistory();
    const user = renderDevice(backend, fakeAuth('a@example.com').client);
    await waitFor(() => expect(backend.list).toHaveBeenCalled());

    stored.unshift({ id: 'h-elsewhere', date: 'Oct 21, 2026', rigNickname: 'Elsewhere Rig', verdict: 'pass', key: 'k' });
    await goHistory(user);

    expect(await findHistoryRow('Elsewhere Rig')).toBeInTheDocument();
  });

  it('retries a failed save with the same idempotency key and ends with one entry', async () => {
    const { backend, stored } = makeFakeAccountHistory();
    const realAdd = backend.addEntry.getMockImplementation()!;
    backend.addEntry.mockRejectedValueOnce(new Error('network down'));
    backend.addEntry.mockImplementation(realAdd);
    const user = renderDevice(backend, fakeAuth('a@example.com').client);

    await finishCheckForNewRig(user, 'Big Blue');
    await acknowledgeDisclaimer(user);

    await waitFor(() => expect(stored).toHaveLength(1));
    expect(backend.addEntry).toHaveBeenCalledTimes(2);
    expect(backend.addEntry.mock.calls[1][0]).toBe(backend.addEntry.mock.calls[0][0]);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('says so, and still shows the check, when it cannot be saved to the account', async () => {
    const { backend, stored } = makeFakeAccountHistory();
    backend.addEntry.mockRejectedValue(new Error('network down'));
    const user = renderDevice(backend, fakeAuth('a@example.com').client);

    await finishCheckForNewRig(user, 'Big Blue');
    await acknowledgeDisclaimer(user);

    expect(await screen.findByRole('status')).toHaveTextContent(/couldn.t save this check to your History/i);
    expect(screen.getByText('Not Enough Information')).toBeInTheDocument();
    expect(stored).toHaveLength(0);
  });
});

describe('signed-out History', () => {
  it('keeps this visit’s checks on the History screen and never calls the account store', async () => {
    const { backend } = makeFakeAccountHistory();
    const user = renderDevice(backend, fakeAuth(null).client);

    await finishCheckForNewRig(user, 'Big Blue');
    await acknowledgeDisclaimer(user);
    await goHome(user);
    await goHistory(user);

    expect(await findHistoryRow('Big Blue')).toBeInTheDocument();
    expect(backend.addEntry).not.toHaveBeenCalled();
    expect(backend.list).not.toHaveBeenCalled();
  });

  it('leaves checks made before signing in out of the account, and shows the account’s own History', async () => {
    const { backend, stored } = makeFakeAccountHistory();
    stored.unshift({ id: 'h-1', date: 'Oct 20, 2026', rigNickname: 'Account Rig', verdict: 'pass', key: 'k' });
    const auth = fakeAuth(null);
    const user = renderDevice(backend, auth.client);
    await finishCheckForNewRig(user, 'Visit Rig');
    await acknowledgeDisclaimer(user);
    await goHome(user);

    await auth.signIn('a@example.com');
    await goHistory(user);

    expect(await findHistoryRow('Account Rig')).toBeInTheDocument();
    expect(screen.queryByText('Visit Rig')).not.toBeInTheDocument();
    expect(backend.addEntry).not.toHaveBeenCalled();

    await act(async () => {
      await auth.client.signOut();
    });
    await goHistory(user);

    expect(await findHistoryRow('Visit Rig')).toBeInTheDocument();
    expect(screen.queryByText('Account Rig')).not.toBeInTheDocument();
  });
});

// Replies can arrive out of order, or after the account changed. The hook drops a stale one, so the screen never
// shows an older list over a newer one, or one account's History to another (history.tsx).
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

const entryFor = (id: string, rigNickname: string): HistoryEntry => ({ id, date: 'Oct 22, 2026', rigNickname, verdict: 'pass' });

function renderHistoryHook(backend: HistoryBackend, auth: AuthClient) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <AuthProvider client={auth}>
      <HistoryProvider backend={backend}>{children}</HistoryProvider>
    </AuthProvider>
  );
  return renderHook(() => useHistory(), { wrapper });
}

describe('History replies that arrive late', () => {
  it('keeps the newest list when an older refresh answers after a newer one', async () => {
    const slow = deferred<HistoryEntry[]>();
    const list = vi
      .fn<() => Promise<HistoryEntry[]>>()
      .mockReturnValueOnce(slow.promise)
      .mockResolvedValue([entryFor('2', 'Newer'), entryFor('1', 'Older')]);
    const backend: HistoryBackend = { list, addEntry: vi.fn(async () => {}) };
    const { result } = renderHistoryHook(backend, fakeAuth('a@example.com').client);
    await waitFor(() => expect(list).toHaveBeenCalledTimes(1));

    act(() => result.current.refresh());
    await waitFor(() => expect(result.current.history.map((e) => e.rigNickname)).toEqual(['Newer', 'Older']));
    await act(async () => {
      slow.resolve([entryFor('1', 'Older')]);
    });

    expect(result.current.history.map((e) => e.rigNickname)).toEqual(['Newer', 'Older']);
  });

  it('does not show one account’s History to the account that signed in after it', async () => {
    const slowForA = deferred<HistoryEntry[]>();
    const list = vi
      .fn<() => Promise<HistoryEntry[]>>()
      .mockReturnValueOnce(slowForA.promise)
      .mockResolvedValue([entryFor('b1', 'B Rig')]);
    const backend: HistoryBackend = { list, addEntry: vi.fn(async () => {}) };
    const auth = fakeAuth('a@example.com');
    const { result } = renderHistoryHook(backend, auth.client);
    await waitFor(() => expect(list).toHaveBeenCalledTimes(1));

    await auth.signIn('b@example.com');
    await waitFor(() => expect(result.current.history.map((e) => e.rigNickname)).toEqual(['B Rig']));
    await act(async () => {
      slowForA.resolve([entryFor('a1', 'A Rig')]);
    });

    expect(result.current.history.map((e) => e.rigNickname)).toEqual(['B Rig']);
  });
});
