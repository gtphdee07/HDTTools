import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import FIXTURE from '../../test-vectors/scan_outcomes.json';
import { SCAN_TIMEOUT_MS, extractTruckTag } from './api';
import { MODULES } from './mockData';
import { ScanAttempts } from './scanAttempts';
import { NO_WEIGHT_MESSAGE, ScanError } from './scanError';
import { scanNoticeFor, scanNoticeText } from './scanNotice';

// Web against the shared Scan outcomes (test-vectors/scan_outcomes.json, written up as "Scan outcomes" in
// workers/scan-proxy/CONTEXT.md). Every row is produced the way the app produces it: the real Scan call
// against a fake fetch, the real request-id bookkeeping, the real notice. A row that disagrees with what
// the app does fails here, and so does a client change the row does not allow. Android runs the same file
// (ScanOutcomesFixtureTest.kt). What the Worker charges and refunds is the Worker's own tests; this is only
// what the user is told and how a retry behaves.

type Pending = Partial<Record<'web' | 'android', Partial<Record<Checked, string>>>>;
// nextStep is checked by Android only (see the fixture's _readme), but either client may be marked pending on it.
type Checked = 'messageContains' | 'retryKeepsRequestId' | 'offersTryAgain' | 'nextStep';
interface Row {
  id: string;
  appliesTo: string[];
  trigger: { kind: string; status?: number; code?: string; fieldsRead?: 'none' | 'some' | 'all' };
  retryKeepsRequestId: boolean;
  offersTryAgain: boolean;
  nextStep: string[];
  messageContains: string[];
  pending: Pending;
}

const ROWS = (FIXTURE.cases as Row[]).filter((row) => row.appliesTo.includes('web'));
const CHECKED: Checked[] = ['messageContains', 'retryKeepsRequestId', 'offersTryAgain', 'nextStep'];

const SERVICE = 'https://scan.example.com';
const JPEG = () => new File(['hello'], 'tag.jpg', { type: 'image/jpeg' });
const HEIC = () => new File(['x'], 'tag.heic', { type: 'image/heic' });

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
  vi.stubEnv('VITE_SCAN_SERVICE_URL', SERVICE);
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

// What one Scan attempt ended in, and the request id it was sent with.
interface Attempt {
  id: string;
  error: ScanError | null;
}

async function requestSent(calls: number) {
  while (fetchMock.mock.calls.length < calls) await new Promise((resolve) => setImmediate(resolve));
}

// One Scan of `photo`, made the way the wizard makes it (through ScanAttempts), ending the way the row says.
async function attempt(row: Row, attempts: ScanAttempts, photo: File): Promise<Attempt> {
  const { trigger } = row;
  let id = '';
  const scan = (clientRequestId: string) => {
    id = clientRequestId;
    if (trigger.kind === 'delivered') return Promise.resolve({});
    if (trigger.kind === 'delivered_no_weight') return Promise.reject(new ScanError('no_weight', NO_WEIGHT_MESSAGE));
    return extractTruckTag(photo, { accessToken: 'token', clientRequestId });
  };

  switch (trigger.kind) {
    case 'worker_error':
      fetchMock.mockResolvedValue({
        ok: false,
        status: trigger.status,
        json: async () => ({ ok: false, code: trigger.code, message: 'the Worker, for developers' }),
      });
      break;
    case 'no_connection':
      fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
      break;
    case 'unreadable_reply':
      fetchMock.mockResolvedValue({
        ok: false,
        status: 502,
        json: async () => {
          throw new Error('an edge error page, not JSON');
        },
      });
      break;
    case 'no_answer_in_time':
      fetchMock.mockImplementation(
        (_url: string, init: RequestInit) =>
          new Promise((_resolve, reject) => {
            init.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
          }),
      );
      break;
    case 'no_service_address':
      vi.stubEnv('VITE_SCAN_SERVICE_URL', '');
      break;
    case 'unsendable_photo':
    case 'delivered':
    case 'delivered_no_weight':
      break;
    default:
      throw new Error(`${row.id}: this test has no way to produce a '${trigger.kind}' trigger`);
  }

  const calls = fetchMock.mock.calls.length;
  const outcome = attempts.run(photo, scan).then(
    () => null,
    (err: unknown) => err,
  );
  if (trigger.kind === 'no_answer_in_time') {
    await requestSent(calls + 1);
    await vi.advanceTimersByTimeAsync(SCAN_TIMEOUT_MS);
  }
  const error = await outcome;
  if (error !== null && !(error instanceof ScanError)) throw error;
  return { id, error };
}

// The words the user reads for a row: the failure's message, or the notice on the review step.
function wordsFor(row: Row, error: ScanError | null): string | null {
  if (row.trigger.kind !== 'delivered') return error?.message ?? null;
  const module = MODULES[1];
  const expected = module.fields.filter((f) => !f.optional);
  const filled = { none: 0, some: 2, all: expected.length }[row.trigger.fieldsRead!];
  const data = Object.fromEntries(expected.slice(0, filled).map((f) => [f.name, 1]));
  const notice = scanNoticeFor(module, data);
  return notice ? scanNoticeText(notice) : null;
}

const isPending = (row: Row, field: Checked) => row.pending.web?.[field] !== undefined;

describe('the fixture itself', () => {
  it('has a unique id per row, and every row carries the fields the clients check', () => {
    const rows = FIXTURE.cases as Row[];
    expect(new Set(rows.map((row) => row.id)).size).toBe(rows.length);
    for (const row of rows) {
      expect(row.appliesTo.length, row.id).toBeGreaterThan(0);
      expect(typeof row.retryKeepsRequestId, row.id).toBe('boolean');
      expect(typeof row.offersTryAgain, row.id).toBe('boolean');
      expect(Array.isArray(row.nextStep), row.id).toBe(true);
      expect(Array.isArray(row.messageContains), row.id).toBe(true);
    }
  });

  it('only marks as pending a field a client checks, with the ticket that builds it', () => {
    for (const row of FIXTURE.cases as Row[]) {
      for (const [client, fields] of Object.entries(row.pending)) {
        expect(['web', 'android']).toContain(client);
        for (const [field, ticket] of Object.entries(fields as Record<string, string>)) {
          expect(CHECKED, `${row.id}: ${field}`).toContain(field);
          expect(ticket, `${row.id}: ${field}`).toMatch(/^#\d+/);
        }
      }
    }
  });

  it('offers Try again exactly when try_again is one of the next steps', () => {
    for (const row of FIXTURE.cases as Row[]) {
      expect(row.offersTryAgain, row.id).toBe(row.nextStep.includes('try_again'));
    }
  });
});

describe.each(ROWS)('Scan outcome $id', (row) => {
  it.skipIf(isPending(row, 'messageContains'))('tells the user what the fixture says it must', async () => {
    const { error } = await attempt(row, new ScanAttempts(), row.trigger.kind === 'unsendable_photo' ? HEIC() : JPEG());
    const words = wordsFor(row, error);
    if (row.messageContains.length === 0) {
      expect(words, 'no message at all').toBeNull();
      return;
    }
    expect(words, 'a message is shown').not.toBeNull();
    for (const phrase of row.messageContains) {
      expect(words!.toLowerCase(), `"${phrase}"`).toContain(phrase.toLowerCase());
    }
  });

  it.skipIf(isPending(row, 'retryKeepsRequestId'))('keeps or changes the request id on a retry as the fixture says', async () => {
    const attempts = new ScanAttempts();
    const photo = row.trigger.kind === 'unsendable_photo' ? HEIC() : JPEG();
    const first = await attempt(row, attempts, photo);
    const second = await attempt(row, attempts, photo);
    expect(second.id === first.id).toBe(row.retryKeepsRequestId);
  });

  it.skipIf(isPending(row, 'offersTryAgain') || row.trigger.kind === 'delivered')(
    'offers Try again only where the fixture says',
    async () => {
      const { error } = await attempt(row, new ScanAttempts(), row.trigger.kind === 'unsendable_photo' ? HEIC() : JPEG());
      expect(error, 'the Scan did not deliver').not.toBeNull();
      expect(error!.canTryAgain).toBe(row.offersTryAgain);
    },
  );
});

// The one rule for naming the fields a Scan did not read. Web's labels are its own; the rule is shared.
describe('the notice for a Scan that read only some of the fields', () => {
  it.each(FIXTURE.noticeFieldLists)('names $labels the way the fixture does', ({ labels, message }) => {
    expect(scanNoticeText({ kind: 'some-unread', fields: labels })).toBe(message);
  });
});
