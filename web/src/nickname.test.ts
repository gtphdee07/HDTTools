import { describe, expect, it } from 'vitest';
import { nicknameKey, sameNickname } from './nickname';

describe('nickname rule', () => {
  it('treats names that differ only by case or surrounding spaces as the same Rig', () => {
    expect(sameNickname('Truck A', ' truck a ')).toBe(true);
    expect(nicknameKey(' Truck A\t')).toBe(nicknameKey('TRUCK A'));
  });

  it('keeps spaces inside a name significant', () => {
    expect(sameNickname('Truck A', 'Truck  A')).toBe(false);
  });

  it('keeps different names different', () => {
    expect(sameNickname('Truck A', 'Truck B')).toBe(false);
  });
});
