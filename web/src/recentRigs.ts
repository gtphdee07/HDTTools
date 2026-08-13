import type { RecentRig, TrailerTagData, TruckTagData } from './types';

const STORAGE_KEY = 'rigcheck:recentRigs';
const MAX_RECENT_RIGS = 5;

export function loadRecentRigs(): RecentRig[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveRecentRig(nickname: string, truck: TruckTagData, trailer: TrailerTagData): RecentRig[] {
  const existing = loadRecentRigs().filter((r) => r.nickname.toLowerCase() !== nickname.toLowerCase());
  const updated: RecentRig = { nickname, truck, trailer, lastUsedAt: new Date().toISOString() };
  const next = [updated, ...existing].slice(0, MAX_RECENT_RIGS);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // localStorage unavailable (e.g. private browsing quota) - the in-memory
    // state for this session still works, it just won't persist.
  }
  return next;
}
