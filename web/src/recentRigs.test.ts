import { beforeEach, describe, expect, it, vi } from 'vitest';
import { loadRecentRigs, saveRecentRig } from './recentRigs';
import type { TrailerTagData, TruckTagData } from './types';

const STORAGE_KEY = 'rigcheck:recentRigs';
const TRUCK: TruckTagData = { manufacturer: 'Ford' };
const TRAILER: TrailerTagData = { manufacturer: 'Forest River' };

beforeEach(() => {
  localStorage.clear();
});

describe('loadRecentRigs', () => {
  it('returns an empty array when nothing is stored', () => {
    expect(loadRecentRigs()).toEqual([]);
  });

  it('returns the stored array when it is valid JSON', () => {
    const rigs = [{ nickname: 'Big Blue', truck: TRUCK, trailer: TRAILER, lastUsedAt: '2026-08-21T00:00:00.000Z' }];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(rigs));
    expect(loadRecentRigs()).toEqual(rigs);
  });

  it('returns an empty array instead of throwing on corrupt JSON', () => {
    localStorage.setItem(STORAGE_KEY, '{not valid json');
    expect(loadRecentRigs()).toEqual([]);
  });

  it('returns an empty array when the stored value parses but is not an array', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ nickname: 'Big Blue' }));
    expect(loadRecentRigs()).toEqual([]);
  });
});

describe('saveRecentRig', () => {
  it('adds a new rig to the front of the list and persists it', () => {
    const result = saveRecentRig('Big Blue', TRUCK, TRAILER);

    expect(result).toHaveLength(1);
    expect(result[0].nickname).toBe('Big Blue');
    expect(result[0].truck).toEqual(TRUCK);
    expect(result[0].trailer).toEqual(TRAILER);
    expect(loadRecentRigs()).toEqual(result);
  });

  it('replaces an existing rig with the same nickname, case-insensitively, instead of duplicating it', () => {
    saveRecentRig('Big Blue', TRUCK, TRAILER);
    const updatedTruck: TruckTagData = { manufacturer: 'Ram' };

    const result = saveRecentRig('big blue', updatedTruck, TRAILER);

    expect(result).toHaveLength(1);
    expect(result[0].truck).toEqual(updatedTruck);
  });

  it('moves a re-saved rig to the front, ahead of rigs saved after it originally', () => {
    saveRecentRig('Big Blue', TRUCK, TRAILER);
    saveRecentRig('Red Rocket', TRUCK, TRAILER);

    const result = saveRecentRig('Big Blue', TRUCK, TRAILER);

    expect(result.map((r) => r.nickname)).toEqual(['Big Blue', 'Red Rocket']);
  });

  it('caps the list at 5 rigs, dropping the oldest', () => {
    for (const nickname of ['Rig 1', 'Rig 2', 'Rig 3', 'Rig 4', 'Rig 5']) {
      saveRecentRig(nickname, TRUCK, TRAILER);
    }

    const result = saveRecentRig('Rig 6', TRUCK, TRAILER);

    expect(result).toHaveLength(5);
    expect(result.map((r) => r.nickname)).toEqual(['Rig 6', 'Rig 5', 'Rig 4', 'Rig 3', 'Rig 2']);
    expect(result.some((r) => r.nickname === 'Rig 1')).toBe(false);
  });

  it('still returns the computed list even if localStorage.setItem throws', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });

    const result = saveRecentRig('Big Blue', TRUCK, TRAILER);

    expect(result).toHaveLength(1);
    expect(result[0].nickname).toBe('Big Blue');
    setItemSpy.mockRestore();
  });
});

describe('nickname rule (trim and ignore case, as the account Garage does)', () => {
  it('saves " truck a " over an existing "Truck A" instead of adding another', () => {
    saveRecentRig('Truck A', TRUCK, TRAILER);
    const updatedTruck: TruckTagData = { manufacturer: 'Ram' };

    const result = saveRecentRig(' truck a ', updatedTruck, TRAILER);

    expect(result).toHaveLength(1);
    expect(result[0].truck).toEqual(updatedTruck);
    expect(loadRecentRigs()).toHaveLength(1);
  });

  it('keeps the existing Rig’s spelling when a save refreshes it, as the account Garage does', () => {
    saveRecentRig('Truck A', TRUCK, TRAILER);

    const result = saveRecentRig(' truck a ', TRUCK, TRAILER);

    expect(result.map((r) => r.nickname)).toEqual(['Truck A']);
  });

  it('stores the nickname without its surrounding spaces', () => {
    const result = saveRecentRig('  Truck A ', TRUCK, TRAILER);

    expect(result[0].nickname).toBe('Truck A');
  });

  it('matches a Rig saved earlier with an untrimmed name', () => {
    const old = [{ nickname: 'Truck A  ', truck: TRUCK, trailer: TRAILER, lastUsedAt: '2026-08-21T00:00:00.000Z' }];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(old));

    const result = saveRecentRig('truck a', { manufacturer: 'Ram' }, TRAILER);

    expect(result).toHaveLength(1);
    expect(result[0].truck).toEqual({ manufacturer: 'Ram' });
  });

  it('still loads a Rig saved with an untrimmed name, shown without the stray spaces', () => {
    const old = [{ nickname: '  Truck A ', truck: TRUCK, trailer: TRAILER, lastUsedAt: '2026-08-21T00:00:00.000Z' }];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(old));

    expect(loadRecentRigs().map((r) => r.nickname)).toEqual(['Truck A']);
  });

  it('lists once a Rig that earlier saves stored twice under spellings of the same name', () => {
    const old = [
      { nickname: 'Truck A', truck: { manufacturer: 'Ram' }, trailer: TRAILER, lastUsedAt: '2026-08-22T00:00:00.000Z' },
      { nickname: 'truck a ', truck: TRUCK, trailer: TRAILER, lastUsedAt: '2026-08-21T00:00:00.000Z' },
    ];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(old));

    const loaded = loadRecentRigs();

    expect(loaded).toHaveLength(1);
    expect(loaded[0].truck).toEqual({ manufacturer: 'Ram' });
  });
});
