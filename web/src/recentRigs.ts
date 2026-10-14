import { nicknameKey, sameNickname } from './nickname';
import type { RecentRig, TrailerTagData, TruckTagData } from './types';

const STORAGE_KEY = 'rigcheck:recentRigs';
const MAX_RECENT_RIGS = 5;

// Rigs saved before the nickname rule (nickname.ts) may carry stray spaces, or sit twice under
// spellings of one name. Show them trimmed and keep the first (most recent) of each name. An entry
// with no text nickname cannot be shown or matched, so it is left out.
function tidy(parsed: unknown[]): RecentRig[] {
  const seen = new Set<string>();
  const rigs: RecentRig[] = [];
  for (const entry of parsed) {
    const rig = entry as RecentRig;
    if (typeof rig?.nickname !== 'string') continue;
    const slot = nicknameKey(rig.nickname);
    if (seen.has(slot)) continue;
    seen.add(slot);
    rigs.push({ ...rig, nickname: rig.nickname.trim() });
  }
  return rigs;
}

export function loadRecentRigs(): RecentRig[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? tidy(parsed) : [];
  } catch {
    return [];
  }
}

export function saveRecentRig(nickname: string, truck: TruckTagData, trailer: TrailerTagData): RecentRig[] {
  const existing = loadRecentRigs().filter((r) => !sameNickname(r.nickname, nickname));
  const updated: RecentRig = { nickname: nickname.trim(), truck, trailer, lastUsedAt: new Date().toISOString() };
  const next = [updated, ...existing].slice(0, MAX_RECENT_RIGS);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // localStorage unavailable (e.g. private browsing quota) - the in-memory
    // state for this session still works, it just won't persist.
  }
  return next;
}
