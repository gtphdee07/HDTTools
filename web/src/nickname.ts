// The one rule for telling Rigs apart by nickname: ignore case and surrounding spaces. It follows the
// account Garage's own rule (the `garage_rigs_user_nickname_key` index and `add_rig` compare
// `lower(btrim(nickname))`), so the browser-saved list and the Garage agree on what is one Rig (#92).
// `trim()` also strips tabs and line breaks, which `btrim` leaves; a nickname box cannot produce
// those, and the Garage adapter trims before it sends, so the two never disagree in practice.

export const nicknameKey = (nickname: string): string => nickname.trim().toLowerCase();

export const sameNickname = (a: string, b: string): boolean => nicknameKey(a) === nicknameKey(b);

// Finds the Rig a past check belongs to, by the check's `rigNickname`. Returns undefined when that Rig is gone.
export function rigLookup<R extends { nickname: string }>(rigs: R[]): (nickname: string) => R | undefined {
  const byKey = new Map(rigs.map((rig) => [nicknameKey(rig.nickname), rig]));
  return (nickname) => byKey.get(nicknameKey(nickname));
}

// The line shown under a Rig: "Peterbilt + Great Dane". Drops whichever manufacturer is empty; empty when both are.
// Each screen keeps its own fallback for a Rig that is gone or has no manufacturers (#109).
export function rigSubtitle(rig: {
  truck: { manufacturer?: string };
  trailer: { manufacturer?: string };
}): string {
  return [rig.truck.manufacturer, rig.trailer.manufacturer].filter(Boolean).join(' + ');
}
