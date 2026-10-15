import { describe, expect, it } from 'vitest';
import { nicknameKey, rigLookup, rigSubtitle, sameNickname } from './nickname';

describe('nickname rule', () => {
  it('treats names that differ only by case or surrounding spaces as the same Rig', () => {
    expect(sameNickname('Truck A', ' truck a ')).toBe(true);
    expect(nicknameKey('  Truck A ')).toBe(nicknameKey('TRUCK A'));
  });

  it('keeps spaces inside a name significant', () => {
    expect(sameNickname('Truck A', 'Truck  A')).toBe(false);
  });

  it('keeps different names different', () => {
    expect(sameNickname('Truck A', 'Truck B')).toBe(false);
  });
});

describe('rigLookup', () => {
  const truckA = { nickname: 'Truck A', id: 1 };
  const truckB = { nickname: 'Truck B', id: 2 };

  it('finds the Rig whose nickname differs only by case or surrounding spaces', () => {
    const find = rigLookup([truckA, truckB]);
    expect(find('Truck A')).toBe(truckA);
    expect(find('  truck a ')).toBe(truckA);
    expect(find('TRUCK B')).toBe(truckB);
  });

  it('returns nothing when no Rig matches', () => {
    const find = rigLookup([truckA]);
    expect(find('Truck B')).toBeUndefined();
    expect(find('Truck  A')).toBeUndefined();
    expect(rigLookup([])('Truck A')).toBeUndefined();
  });
});

describe('rigSubtitle', () => {
  const rig = (truck?: string, trailer?: string) => ({
    truck: { manufacturer: truck },
    trailer: { manufacturer: trailer },
  });

  it('joins the truck and trailer manufacturers with a plus', () => {
    expect(rigSubtitle(rig('Peterbilt', 'Great Dane'))).toBe('Peterbilt + Great Dane');
  });

  it('shows only the truck when the trailer has no manufacturer', () => {
    expect(rigSubtitle(rig('Peterbilt'))).toBe('Peterbilt');
    expect(rigSubtitle(rig('Peterbilt', ''))).toBe('Peterbilt');
  });

  it('shows only the trailer when the truck has no manufacturer', () => {
    expect(rigSubtitle(rig(undefined, 'Great Dane'))).toBe('Great Dane');
  });

  it('is empty when neither has a manufacturer', () => {
    expect(rigSubtitle(rig())).toBe('');
  });
});
