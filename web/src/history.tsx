import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useAuth } from './auth';
import type { Plan } from './plan';
import { usePlan } from './plan';
import type { HistoryEntry, Verdict } from './types';

// History: a signed-in user's past checks live in the account (ADR-0005), so every device sees the same
// ones, and the server keeps only the newest few (the plan's cap), dropping the oldest. A signed-out
// visitor's checks last only for the visit, as before, so the free flow is never gated. Checks made while
// signed out are not carried into the account: they were never saved anywhere, and signing in switches to
// the account's own list (signing out switches back).

type NewEntry = Pick<HistoryEntry, 'rigNickname' | 'verdict'>;

// The account's History store. Kept narrow so tests can fake it (the real one is supabaseHistory.ts).
export interface HistoryBackend {
  // The account's checks, newest first.
  list(): Promise<HistoryEntry[]>;
  // Adds a check; the server drops the oldest past the cap, which `plan` (null when it could not be read)
  // picks. The same key sent twice creates one entry.
  addEntry(idempotencyKey: string, entry: NewEntry, plan: Plan | null): Promise<void>;
  // How many checks each plan keeps, as the server counts them.
  caps(): Promise<Record<Plan, number>>;
}

export interface History {
  history: HistoryEntry[];
  // How many checks each plan keeps; null while signed out or until the account's caps have been read
  // (a failed read leaves it null, and the History screen then says nothing about the cap).
  caps: Record<Plan, number> | null;
  // Records a finished check. `date` is the check's own display date, used for a visit-only entry; an
  // account entry takes its date from the server's timestamp. False if the account could not save it.
  recordCheck(rigNickname: string, verdict: Verdict, date: string): Promise<boolean>;
  // Re-reads the account's checks, to pick up checks made on another device.
  refresh(): void;
}

const HistoryBackendContext = createContext<HistoryBackend | null>(null);

export function HistoryProvider({ backend, children }: { backend: HistoryBackend | null; children: ReactNode }) {
  return <HistoryBackendContext.Provider value={backend}>{children}</HistoryBackendContext.Provider>;
}

// One key per check, reused on the retry, so a request that did land but whose reply was lost is
// recognised by the server instead of recorded twice.
async function addWithOneRetry(backend: HistoryBackend, entry: NewEntry, plan: Plan | null): Promise<void> {
  const key = crypto.randomUUID();
  try {
    await backend.addEntry(key, entry, plan);
  } catch {
    await backend.addEntry(key, entry, plan);
  }
}

export function useHistory(): History {
  const { user } = useAuth();
  const backend = useContext(HistoryBackendContext);
  const plan = usePlan();
  const accountId = user?.id ?? null;
  const remote = accountId !== null ? backend : null;

  // This visit's checks, shown while nobody is signed in.
  const [visitEntries, setVisitEntries] = useState<HistoryEntry[]>([]);
  const [accountEntries, setAccountEntries] = useState<HistoryEntry[]>([]);
  const [caps, setCaps] = useState<Record<Plan, number> | null>(null);
  // Identifies the signed-in account a response belongs to, so a slow reply that lands after a
  // sign-out (or an account switch) is dropped instead of showing the wrong History.
  const current = useRef<string | null>(null);
  current.current = remote ? accountId : null;
  // Numbers each refresh so an older one answering late can't overwrite a newer list.
  const latestLoad = useRef(0);

  const load = useCallback(async () => {
    if (!remote) return;
    const forAccount = accountId;
    const thisLoad = ++latestLoad.current;
    try {
      const fetched = await remote.list();
      if (current.current === forAccount && latestLoad.current === thisLoad) setAccountEntries(fetched);
    } catch {
      // Keep what is shown; the next refresh tries again.
    }
  }, [remote, accountId]);

  useEffect(() => {
    setAccountEntries([]);
    void load();
  }, [load]);

  // The caps are read once per account; they only change when the owner edits them.
  useEffect(() => {
    setCaps(null);
    if (!remote) return;
    let stale = false;
    remote.caps().then(
      (read) => {
        if (!stale) setCaps(read);
      },
      () => {
        // Without them the History screen just says nothing about the cap.
      },
    );
    return () => {
      stale = true;
    };
  }, [remote]);

  useEffect(() => {
    if (!remote) return;
    const onVisible = () => {
      if (document.visibilityState === 'visible') void load();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [remote, load]);

  const recordCheck = useCallback(
    async (rigNickname: string, verdict: Verdict, date: string): Promise<boolean> => {
      if (!remote) {
        setVisitEntries((entries) => [{ id: crypto.randomUUID(), date, rigNickname, verdict }, ...entries]);
        return true;
      }
      try {
        await addWithOneRetry(remote, { rigNickname, verdict }, plan);
      } catch {
        return false;
      }
      await load();
      return true;
    },
    [remote, load, plan],
  );

  return { history: remote ? accountEntries : visitEntries, caps, recordCheck, refresh: () => void load() };
}
