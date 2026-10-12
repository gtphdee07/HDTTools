import { afterEach, describe, expect, it, vi } from 'vitest';
import { MAX_IMAGE_BYTES, prepareImage } from './scanImage';
import { ScanError } from './scanError';

// The Scan service takes JPEG, PNG, WebP or GIF, and Claude rejects an image over about 5 MB once encoded.
// A phone photo is often bigger than that or a format the service cannot read, so it is shrunk in the
// browser when possible; what cannot be sent is refused with a clear message before anything is charged.

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const fileOfSize = (bytes: number, type: string) => new File([new Uint8Array(bytes)], 'photo', { type });

describe('prepareImage', () => {
  it('sends a small supported photo as it is', async () => {
    const image = await prepareImage(new File(['hello'], 'tag.png', { type: 'image/png' }));

    expect(image).toEqual({ base64: btoa('hello'), mediaType: 'image/png' });
  });

  it('refuses a format the service cannot read when it cannot be converted', async () => {
    const err = await prepareImage(fileOfSize(10, 'image/heic')).catch((e) => e);

    expect(err).toBeInstanceOf(ScanError);
    expect(err.code).toBe('bad_photo');
  });

  it('refuses an oversize photo when it cannot be shrunk', async () => {
    const err = await prepareImage(fileOfSize(MAX_IMAGE_BYTES + 1, 'image/jpeg')).catch((e) => e);

    expect(err).toBeInstanceOf(ScanError);
    expect(err.code).toBe('bad_photo');
    expect(err.message).toMatch(/too large/i);
  });

  it('shrinks an oversize photo to a JPEG that fits', async () => {
    const drawn: Array<[number, number]> = [];
    vi.stubGlobal('createImageBitmap', async () => ({ width: 4000, height: 3000, close: () => {} }));
    const canvas = {
      width: 0,
      height: 0,
      getContext: () => ({ drawImage: (_i: unknown, _x: number, _y: number, w: number, h: number) => drawn.push([w, h]) }),
      toBlob: (cb: (b: Blob | null) => void, type: string) => cb(new Blob(['small'], { type })),
    };
    const real = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) =>
      tag === 'canvas' ? (canvas as unknown as HTMLCanvasElement) : real(tag),
    );

    const image = await prepareImage(fileOfSize(MAX_IMAGE_BYTES + 1, 'image/jpeg'));

    expect(image).toEqual({ base64: btoa('small'), mediaType: 'image/jpeg' });
    expect(Math.max(...drawn[0])).toBeLessThanOrEqual(2000);
    expect(drawn[0][0] / drawn[0][1]).toBeCloseTo(4000 / 3000);
  });

  it('converts a format the service cannot read when the browser can decode it', async () => {
    vi.stubGlobal('createImageBitmap', async () => ({ width: 800, height: 600, close: () => {} }));
    const canvas = {
      width: 0,
      height: 0,
      getContext: () => ({ drawImage: () => {} }),
      toBlob: (cb: (b: Blob | null) => void, type: string) => cb(new Blob(['converted'], { type })),
    };
    const real = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) =>
      tag === 'canvas' ? (canvas as unknown as HTMLCanvasElement) : real(tag),
    );

    const image = await prepareImage(fileOfSize(10, 'image/heic'));

    expect(image).toEqual({ base64: btoa('converted'), mediaType: 'image/jpeg' });
  });
});
