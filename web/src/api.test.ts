import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { extractScaleTicket, extractTrailerTag, extractTruckTag } from './api';
import { ScanError } from './scanError';
import type { ScanErrorCode } from './scanError';

// The scan call is the wire contract with the shared Scan service (workers/scan-proxy): one POST of JSON
// with the account token as a bearer header. What the service charges, refunds and dedupes is proven in
// the Worker's own tests; these prove this client sends what that contract needs and reports each answer.

const SERVICE = 'https://scan.example.com';
const CONTEXT = { accessToken: 'token-pat', clientRequestId: 'req-1' };
const JPEG = () => new File(['hello'], 'tag.jpg', { type: 'image/jpeg' });

let fetchMock: ReturnType<typeof vi.fn>;

function answer(status: number, body: unknown) {
  fetchMock.mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => {
      if (body === undefined) throw new Error('not json');
      return body;
    },
  });
}

async function failure(call: Promise<unknown>): Promise<ScanError> {
  try {
    await call;
  } catch (err) {
    expect(err).toBeInstanceOf(ScanError);
    return err as ScanError;
  }
  throw new Error('expected the scan to fail');
}

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
  vi.stubEnv('VITE_SCAN_SERVICE_URL', SERVICE);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('a scan request', () => {
  it('posts the photo as JSON to /v1/scan with the account token and the request id', async () => {
    answer(200, { ok: true, doc_type: 'truck_tag', fields: { manufacturer: 'Ford' } });

    const result = await extractTruckTag(JPEG(), CONTEXT);

    expect(result).toEqual({ manufacturer: 'Ford' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe(`${SERVICE}/v1/scan`);
    expect(options.method).toBe('POST');
    expect(options.headers.Authorization).toBe('Bearer token-pat');
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(options.body)).toEqual({
      doc_type: 'truck_tag',
      image_base64: btoa('hello'),
      media_type: 'image/jpeg',
      client_request_id: 'req-1',
    });
  });

  it('names the document type for each kind of document', async () => {
    answer(200, { ok: true, doc_type: 'x', fields: {} });

    await extractTrailerTag(JPEG(), CONTEXT);
    await extractScaleTicket(JPEG(), CONTEXT);

    const types = fetchMock.mock.calls.map(([, options]) => JSON.parse(options.body).doc_type);
    expect(types).toEqual(['trailer_tag', 'scale_ticket']);
  });

  it('ignores a trailing slash on the service address', async () => {
    vi.stubEnv('VITE_SCAN_SERVICE_URL', `${SERVICE}/`);
    answer(200, { ok: true, doc_type: 'truck_tag', fields: {} });

    await extractTruckTag(JPEG(), CONTEXT);

    expect(fetchMock.mock.calls[0][0]).toBe(`${SERVICE}/v1/scan`);
  });

  it('does not send anything when this build has no scan service address', async () => {
    vi.stubEnv('VITE_SCAN_SERVICE_URL', '');

    const err = await failure(extractTruckTag(JPEG(), CONTEXT));

    expect(err.code).toBe('unavailable');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('refuses a photo the service cannot read before sending anything', async () => {
    const err = await failure(extractTruckTag(new File(['x'], 'tag.heic', { type: 'image/heic' }), CONTEXT));

    expect(err.code).toBe('bad_photo');
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('what the user is told when a scan does not deliver', () => {
  const cases: Array<{
    name: string;
    status: number;
    body: unknown;
    code: ScanErrorCode;
    lostResponse: boolean;
    message: RegExp;
  }> = [
    {
      name: 'no scans left',
      status: 402,
      body: { ok: false, code: 'insufficient_credits', message: 'x' },
      code: 'insufficient_credits',
      lostResponse: false,
      message: /out of scans/i,
    },
    {
      name: 'a token the service refuses',
      status: 401,
      body: { ok: false, code: 'unauthorized', message: 'x' },
      code: 'unauthorized',
      lostResponse: false,
      message: /sign in again/i,
    },
    {
      name: 'the service unable to verify the account',
      status: 503,
      body: { ok: false, code: 'auth_unavailable', message: 'x' },
      code: 'auth_unavailable',
      lostResponse: false,
      message: /not charged/i,
    },
    {
      name: 'an extraction that failed and was refunded',
      status: 502,
      body: { ok: false, code: 'extraction_failed', message: 'x' },
      code: 'extraction_failed',
      lostResponse: false,
      message: /refunded/i,
    },
    {
      // The service charged, could not read the photo and could not refund. The same request id on the retry
      // is not charged again, so the id is kept.
      name: 'an extraction that failed and could not be refunded',
      status: 502,
      body: { ok: false, code: 'extraction_failed_no_refund', message: 'x' },
      code: 'extraction_failed_no_refund',
      lostResponse: true,
      message: /contact support/i,
    },
    {
      name: 'the payment service being unreachable',
      status: 502,
      body: { ok: false, code: 'billing_error', message: 'x' },
      code: 'billing_error',
      lostResponse: false,
      message: /not charged/i,
    },
    {
      name: 'a request the service rejects',
      status: 400,
      body: { ok: false, code: 'bad_request', message: 'media_type must be image/jpeg' },
      code: 'bad_request',
      lostResponse: false,
      message: /media_type must be image\/jpeg/,
    },
    {
      name: 'an error page from the edge instead of the service',
      status: 520,
      body: undefined,
      code: 'unknown',
      lostResponse: true,
      message: /try again/i,
    },
    {
      name: 'a success that cannot be read',
      status: 200,
      body: { nothing: 'useful' },
      code: 'unknown',
      lostResponse: true,
      message: /try again/i,
    },
  ];

  for (const c of cases) {
    it(`reports ${c.name}`, async () => {
      answer(c.status, c.body);

      const err = await failure(extractTruckTag(JPEG(), CONTEXT));

      expect(err.code).toBe(c.code);
      expect(err.lostResponse).toBe(c.lostResponse);
      expect(err.message).toMatch(c.message);
    });
  }

  it('reports no connection as a lost response, so a retry may reuse the same request id', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));

    const err = await failure(extractTruckTag(JPEG(), CONTEXT));

    expect(err.code).toBe('network');
    expect(err.lostResponse).toBe(true);
    expect(err.message).toMatch(/connection/i);
  });
});
