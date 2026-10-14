// The one rule for telling Rigs apart by nickname: ignore case and surrounding spaces. It follows the
// account Garage's own rule (the `garage_rigs_user_nickname_key` index and `add_rig` compare
// `lower(btrim(nickname))`), so the browser-saved list and the Garage agree on what is one Rig (#92).
// `trim()` also strips tabs and line breaks, which `btrim` leaves; a nickname box cannot produce
// those, and the Garage adapter trims before it sends, so the two never disagree in practice.

export const nicknameKey = (nickname: string): string => nickname.trim().toLowerCase();

export const sameNickname = (a: string, b: string): boolean => nicknameKey(a) === nicknameKey(b);
