import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from './auth';
import { GarageFullError, useGarageBackend } from './garage';
import type { GarageBackend } from './garage';
import { nicknameKey } from './nickname';
import type { Plan } from './plan';
import { usePlan } from './plan';
import { loadRecentRigs } from './recentRigs';
import type { RecentRig } from './types';

// Offers a signed-in user the Rigs they saved in this browser before signing in (#91). The
// browser-local Garage is hidden while signed in (ADR-0005), so without this they would be stranded.
// Never automatic: the user says yes or no, once per account on this browser. The browser's own
// Rigs are never changed or removed, whichever way they answer.

export interface ImportResult {
  imported: string[];
  // Nicknames the account already had, left as they are (adding would have overwritten that Rig).
  alreadyThere: string[];
  // Nicknames the Garage had no room for, and the cap that refused them when the server named one.
  notFit: string[];
  cap: number | null;
  // The plan the import ran under (null when it could not be read), which is whose cap `cap` is.
  plan: Plan | null;
  // True when the import stopped on an error before every Rig was dealt with.
  interrupted: boolean;
}

type ImportPhase =
  | { kind: 'none' }
  | { kind: 'offer'; rigs: RecentRig[] }
  | { kind: 'importing'; rigs: RecentRig[] }
  | { kind: 'interrupted'; rigs: RecentRig[] }
  | { kind: 'done'; result: ImportResult };

const answeredKey = (accountId: string) => `rigcheck:garageImportAnswered:${accountId}`;
const keysKey = (accountId: string) => `rigcheck:garageImportKeys:${accountId}`;

// Keyed by nicknameKey (trimmed, lower-cased). A key exists once a Rig's add has been tried, and stays until the
// import finishes, so a retry of an interrupted import sends the same key and cannot add it twice.
type Keys = Record<string, string>;

function readKeys(accountId: string): Keys {
  try {
    const parsed = JSON.parse(localStorage.getItem(keysKey(accountId)) ?? '{}');
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function writeStorage(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    // Storage unavailable: the choice still holds for this page, it just won't be remembered.
  }
}

function wasAnswered(accountId: string): boolean {
  try {
    return localStorage.getItem(answeredKey(accountId)) !== null;
  } catch {
    return false;
  }
}

// The browser's Rigs that the account could accept, most recently used first. The browser's list is
// whatever was stored, so skip entries the account would refuse (the table limits a nickname to 80
// characters). loadRecentRigs has already trimmed the names and dropped repeats of one nickname,
// which the account would see as one Rig.
function loadBrowserRigs(): RecentRig[] {
  return loadRecentRigs().filter((r) => r.nickname.length > 0 && r.nickname.length <= 80);
}

// `stillSignedIn` is checked before every add, so signing out (or switching accounts) part-way
// stops the import instead of carrying on into whichever account is signed in next.
async function importRigs(
  backend: GarageBackend,
  rigs: RecentRig[],
  keys: Keys,
  persistKeys: () => void,
  stillSignedIn: () => boolean,
  plan: Plan | null,
): Promise<ImportResult> {
  const result: ImportResult = { imported: [], alreadyThere: [], notFit: [], cap: null, plan, interrupted: false };
  let inAccount: RecentRig[];
  try {
    inAccount = await backend.list();
  } catch {
    return { ...result, interrupted: true };
  }
  for (const rig of rigs) {
    if (!stillSignedIn()) return { ...result, interrupted: true };
    const slot = nicknameKey(rig.nickname);
    // A Rig whose add was already tried keeps its key even if it now shows up in the account:
    // that is this import's own earlier add, and the same key makes the server answer it again
    // instead of adding it twice. Any other Rig of that name is the account's own.
    if (!keys[slot] && inAccount.some((r) => nicknameKey(r.nickname) === slot)) {
      result.alreadyThere.push(rig.nickname);
      continue;
    }
    keys[slot] ??= crypto.randomUUID();
    persistKeys();
    try {
      await backend.addRig(keys[slot], { nickname: rig.nickname, truck: rig.truck, trailer: rig.trailer }, plan);
      result.imported.push(rig.nickname);
    } catch (err) {
      if (!(err instanceof GarageFullError)) return { ...result, interrupted: true };
      result.notFit.push(rig.nickname);
      result.cap = err.cap;
    }
  }
  return result;
}

export interface RigImport {
  phase: ImportPhase;
  accept(): Promise<void>;
  decline(): void;
  dismiss(): void;
}

export function useRigImport(onImported: () => void): RigImport {
  const { user } = useAuth();
  const backend = useGarageBackend();
  const plan = usePlan();
  const accountId = user?.id ?? null;
  const remote = accountId !== null ? backend : null;
  const [phase, setPhase] = useState<ImportPhase>({ kind: 'none' });
  // The account an answer belongs to, so one that lands after a sign-out is dropped.
  const current = useRef<string | null>(null);
  current.current = remote ? accountId : null;

  useEffect(() => {
    if (!remote || !accountId || wasAnswered(accountId)) {
      setPhase({ kind: 'none' });
      return;
    }
    const rigs = loadBrowserRigs();
    setPhase(rigs.length > 0 ? { kind: 'offer', rigs } : { kind: 'none' });
  }, [remote, accountId]);

  const accept = useCallback(async () => {
    if (!remote || !accountId || (phase.kind !== 'offer' && phase.kind !== 'interrupted')) return;
    const { rigs } = phase;
    setPhase({ kind: 'importing', rigs });
    const keys = readKeys(accountId);
    const stillSignedIn = () => current.current === accountId;
    const result = await importRigs(remote, rigs, keys, () => writeStorage(keysKey(accountId), JSON.stringify(keys)), stillSignedIn, plan);
    if (!stillSignedIn()) return;
    if (result.interrupted) {
      setPhase({ kind: 'interrupted', rigs });
    } else {
      writeStorage(answeredKey(accountId), new Date().toISOString());
      writeStorage(keysKey(accountId), null);
      setPhase({ kind: 'done', result });
    }
    onImported();
  }, [remote, accountId, phase, onImported, plan]);

  const decline = useCallback(() => {
    if (accountId) writeStorage(answeredKey(accountId), new Date().toISOString());
    setPhase({ kind: 'none' });
  }, [accountId]);

  const dismiss = useCallback(() => setPhase({ kind: 'none' }), []);

  return { phase, accept, decline, dismiss };
}
