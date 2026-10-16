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
  const readable = module.fields.filter((f) => !f.optional);
  const unread = readable.filter((f) => !isFilled(data[f.name]));
  if (unread.length === 0) return null;
  if (unread.length === readable.length) return { kind: 'nothing-read' };
  return { kind: 'some-unread', fields: unread.map((f) => f.label) };
}

export function scanNoticeText(notice: ScanNotice): string {
  return notice.kind === 'nothing-read'
    ? 'A Scan was used and nothing could be read. Type the numbers in, or go back and choose a different photo.'
    : `A Scan was used. We couldn't read: ${notice.fields.join(', ')}. Fill those in yourself.`;
}
