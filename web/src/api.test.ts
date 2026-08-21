import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createBreakdown, extractScaleTicket, extractTrailerTag, extractTruckTag } from './api';
import CONTRACT from '../../test-vectors/pin_weight_pct_contract.json';

let fetchMock: ReturnType<typeof vi.fn>;

function mockFetchOk(body: unknown) {
  fetchMock.mockResolvedValue({ ok: true, json: async () => body });
}

function mockFetchError(status: number, body: unknown) {
  fetchMock.mockResolvedValue({ ok: false, status, json: async () => body });
}

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('createBreakdown', () => {
  it('sends the truck/trailer/scale payloads through unchanged', async () => {
    mockFetchOk({});
    const truck = { gvwr_lb: 14000 };
    const trailer = { gvwr_lb: 12500 };
    const scale = { steer_axle_lb: 5620 };

    await createBreakdown(truck, trailer, scale, 20);

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('http://localhost:8000/api/breakdown');
    expect(options.method).toBe('POST');
    const body = JSON.parse(options.body as string);
    expect(body.truck).toEqual(truck);
    expect(body.trailer).toEqual(trailer);
    expect(body.scale).toEqual(scale);
  });

  it('resolves with the parsed response on success', async () => {
    const result = { date: '2026-08-21', verdict: 'pass' };
    mockFetchOk(result);

    await expect(createBreakdown({}, {}, {}, 20)).resolves.toEqual(result);
  });

  it('rejects with the server-provided detail message on failure', async () => {
    mockFetchError(422, { detail: 'trailer.gvwr_lb must be positive' });

    await expect(createBreakdown({}, {}, {}, 20)).rejects.toThrow('trailer.gvwr_lb must be positive');
  });

  it('falls back to a generic message when the error body has no detail (or is not JSON)', async () => {
    mockFetchError(500, null);

    await expect(createBreakdown({}, {}, {}, 20)).rejects.toThrow('Request failed (500)');
  });

  // Interface-contract test, paired with tests/test_api.py's matching
  // case via the shared test-vectors/pin_weight_pct_contract.json
  // fixture. The UI (this file's callers: Web's ReviewStep slider,
  // Android's TruckTagEntryScreen slider) works in whole percentage
  // points (15-25); compute_breakdown/computeBreakdown and the
  // /api/breakdown request body work in the equivalent 0.15-0.25
  // fraction. This is the one place in web/ that does that conversion
  // (pin_weight_pct: pinWeightPct / 100) - a change to that line breaks
  // this test, not just a UI slider.
  it('sends pin_weight_pct as the fraction the UI whole-number percentage converts to', async () => {
    mockFetchOk({});

    await createBreakdown({}, {}, {}, CONTRACT.ui_percent);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(options.body as string);
    expect(body.pin_weight_pct).toBeCloseTo(CONTRACT.api_fraction);
  });
});

// extractTruckTag/extractTrailerTag/extractScaleTicket are thin wrappers
// over the same postFile helper - one function (extractTruckTag) gets
// full success/error coverage, the other two only confirm they hit their
// own distinct endpoint (the one thing that actually varies between
// them; a copy-paste bug pointing two of them at the same path would
// otherwise go uncaught by any single-function test).

describe('extractTruckTag', () => {
  it('posts the file as multipart form data to /api/extract/truck-tag', async () => {
    mockFetchOk({ manufacturer: 'Ford' });
    const file = new File(['x'], 'truck.jpg', { type: 'image/jpeg' });

    const result = await extractTruckTag(file);

    expect(result).toEqual({ manufacturer: 'Ford' });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('http://localhost:8000/api/extract/truck-tag');
    expect(options.method).toBe('POST');
    expect(options.body).toBeInstanceOf(FormData);
    expect((options.body as FormData).get('file')).toBe(file);
  });

  it('rejects with the server-provided detail message on failure', async () => {
    mockFetchError(400, { detail: "That doesn't look like a truck tag." });

    await expect(extractTruckTag(new File(['x'], 'x.jpg'))).rejects.toThrow("That doesn't look like a truck tag.");
  });

  it('falls back to a generic message when the error body has no detail (or is not JSON)', async () => {
    mockFetchError(500, null);

    await expect(extractTruckTag(new File(['x'], 'x.jpg'))).rejects.toThrow('Request failed (500)');
  });
});

describe('extractTrailerTag', () => {
  it('posts to /api/extract/trailer-tag', async () => {
    mockFetchOk({ gvwr_lb: 12500 });

    await extractTrailerTag(new File(['x'], 'trailer.jpg'));

    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/api/extract/trailer-tag');
  });
});

describe('extractScaleTicket', () => {
  it('posts to /api/extract/scale-ticket', async () => {
    mockFetchOk({ steer_axle_lb: 5620 });

    await extractScaleTicket(new File(['x'], 'ticket.jpg'));

    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/api/extract/scale-ticket');
  });
});
