import type { ModuleDef } from './mockData';

// What the review step tells the user after a Scan that was delivered but did not fill every field. The Scan
// was charged all the same (workers/scan-proxy/CONTEXT.md), so this is a notice, not a failure: no error state
// and no Try again (#119).
export type ScanNotice = { kind: 'nothing-read' } | { kind: 'some-unread'; fields: string[] };

const isFilled = (value: unknown) => value != null && value !== '';

// The notice for a Scan that returned `data` for `module`, or null when every field the Scan can read was
// filled. Optional fields are left out of the count: a Truck Tag has no stand-alone weight on it, so a good
// read of the tag would otherwise always look incomplete.
export function scanNoticeFor(module: ModuleDef, data: Record<string, unknown>): ScanNotice | null {
  const expected = module.fields.filter((f) => !f.optional);
  const unread = expected.filter((f) => !isFilled(data[f.name]));
  if (unread.length === 0) return null;
  if (unread.length === expected.length) return { kind: 'nothing-read' };
  return { kind: 'some-unread', fields: unread.map((f) => f.label) };
}

// "A", "A and B", "A, B and C". The same rule as Android's, pinned by test-vectors/scan_outcomes.json.
const joinLabels = (labels: string[]) =>
  labels.length < 2 ? labels.join('') : `${labels.slice(0, -1).join(', ')} and ${labels[labels.length - 1]}`;

export function scanNoticeText(notice: ScanNotice): string {
  if (notice.kind === 'nothing-read') {
    return 'A Scan was used and nothing could be read. Type the numbers in, or go back and choose a different photo.';
  }
  const them = notice.fields.length === 1 ? 'it' : 'them';
  return `A Scan was used, but we couldn't read: ${joinLabels(notice.fields)}. Type ${them} in, or go back and choose a different photo.`;
}
