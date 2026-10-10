import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useAuth } from './auth';
import { loadRecentRigs, saveRecentRig } from './recentRigs';
import type { RecentRig, TrailerTagData, TruckTagData } from './types';

// The Garage: the signed-in user's saved Rigs live in the account (ADR-0005), so every device sees the
// same ones and the server enforces the plan's cap. A signed-out visitor keeps the browser-local
// Garage (recentRigs.ts), so the free flow is never gated.

export class GarageFullError extends Error {
  readonly cap: number | null;
  constructor(cap: number | null) {
    super('garage_full');
    this.cap = cap;
  }
}

type NewRig = Pick<RecentRig, 'nickname' | 'truck' | 'trailer'>;

// The account's Garage store. Kept narrow so tests can fake it (the real one is supabaseGarage.ts).
export interface GarageBackend {
  // The account's Rigs, most recently used first.
  list(): Promise<RecentRig[]>;
  // Adds a Rig. Rejects with GarageFullError at the cap. The same key sent twice creates one Rig.
  addRig(idempotencyKey: string, rig: NewRig): Promise<void>;
  // Rewrites an existing Rig (its tags and last-used time). Uses no capacity.
  updateRig(rig: RecentRig & { id: string }): Promise<void>;
}

export type SaveRigOutcome = { status: 'saved' } | { status: 'full'; cap: number | null } | { status: 'failed' };

export interface Garage {
  rigs: RecentRig[];
  saveRig(nickname: string, truck: TruckTagData, trailer: TrailerTagData): Promise<SaveRigOutcome>;
  // Re-reads the account's Rigs, to pick up changes made on another device.
  refresh(): void;
}

const GarageBackendContext = createContext<GarageBackend | null>(null);

export function GarageProvider({ backend, children }: { backend: GarageBackend | null; children: ReactNode }) {
  return <GarageBackendContext.Provider value={backend}>{children}</GarageBackendContext.Provider>;
}

const sameNickname = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase();

// False if the update failed. The Rig may have been removed on another device since the list was
// read; the caller then adds it, which refreshes a Rig of that name if one is still there.
async function tryUpdate(backend: GarageBackend, rig: RecentRig & { id: string }): Promise<boolean> {
  try {
    await backend.updateRig({ ...rig, lastUsedAt: new Date().toISOString() });
    return true;
  } catch {
    return false;
  }
}

// One key per save, reused on the retry, so a request that did land but whose reply was lost is
// recognised by the server instead of counted twice. A full Garage is an answer, not a failure, so
// it is not retried.
async function addWithOneRetry(backend: GarageBackend, rig: NewRig): Promise<void> {
  const key = crypto.randomUUID();
  try {
    await backend.addRig(key, rig);
  } catch (err) {
    if (err instanceof GarageFullError) throw err;
    await backend.addRig(key, rig);
  }
}

export function useGarage(): Garage {
  const { user } = useAuth();
  const backend = useContext(GarageBackendContext);
  const accountId = user?.id ?? null;
  const remote = accountId !== null ? backend : null;

  const [rigs, setRigs] = useState<RecentRig[]>(() => loadRecentRigs());
  // Identifies the signed-in account a response belongs to, so a slow reply that lands after a
  // sign-out (or an account switch) is dropped instead of showing the wrong Garage.
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
      if (current.current === forAccount && latestLoad.current === thisLoad) setRigs(fetched);
    } catch {
      // Keep what is shown; the next refresh tries again.
    }
  }, [remote, accountId]);

  useEffect(() => {
    if (!remote) {
      setRigs(loadRecentRigs());
      return;
    }
    setRigs([]);
    void load();
  }, [remote, load]);

  useEffect(() => {
    if (!remote) return;
    const onVisible = () => {
      if (document.visibilityState === 'visible') void load();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [remote, load]);

  const saveRig = useCallback(
    async (nickname: string, truck: TruckTagData, trailer: TrailerTagData): Promise<SaveRigOutcome> => {
      if (!remote) {
        setRigs(saveRecentRig(nickname, truck, trailer));
        return { status: 'saved' };
      }
      try {
        const existing = rigs.find((r) => sameNickname(r.nickname, nickname));
        const updated = existing?.id ? await tryUpdate(remote, { ...existing, id: existing.id, truck, trailer }) : false;
        if (!updated) await addWithOneRetry(remote, { nickname, truck, trailer });
      } catch (err) {
        return err instanceof GarageFullError ? { status: 'full', cap: err.cap } : { status: 'failed' };
      }
      await load();
      return { status: 'saved' };
    },
    [remote, rigs, load],
  );

  return { rigs, saveRig, refresh: () => void load() };
}
