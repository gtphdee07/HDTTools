import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { extractScaleTicket, extractTrailerTag, extractTruckTag } from './api';

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
