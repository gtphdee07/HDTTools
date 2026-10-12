import { ScanError } from './scanError';

const SUPPORTED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'] as const;
type SupportedType = (typeof SUPPORTED_TYPES)[number];

// Claude rejects an image over about 5 MB once base64-encoded (a third larger than the file), so a file
// over this is shrunk before it is sent.
export const MAX_IMAGE_BYTES = 3.5 * 1024 * 1024;
// Longest side to try, in order. 2000px still reads a printed label; each step is a smaller upload.
const SHRINK_STEPS = [2000, 1400, 1000];

export interface PreparedImage {
  base64: string;
  mediaType: SupportedType;
}

const isSupported = (type: string): type is SupportedType => (SUPPORTED_TYPES as readonly string[]).includes(type);

function toBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).slice(String(reader.result).indexOf(',') + 1));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

// Redraws the photo as a smaller JPEG, or null when this browser cannot decode or redraw it.
async function reencode(file: File): Promise<Blob | null> {
  if (typeof createImageBitmap !== 'function') return null;
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    return null;
  }
  try {
    for (const longestSide of SHRINK_STEPS) {
      const scale = Math.min(1, longestSide / Math.max(bitmap.width, bitmap.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(bitmap.width * scale);
      canvas.height = Math.round(bitmap.height * scale);
      const context = canvas.getContext('2d');
      if (!context) return null;
      context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85));
      if (blob && blob.size <= MAX_IMAGE_BYTES) return blob;
    }
    return null;
  } finally {
    bitmap.close?.();
  }
}

// The photo as the Scan service takes it. Throws a 'bad_photo' ScanError, before anything is sent or
// charged, when the photo cannot be made to fit.
export async function prepareImage(file: File): Promise<PreparedImage> {
  if (isSupported(file.type) && file.size <= MAX_IMAGE_BYTES) {
    return { base64: await toBase64(file), mediaType: file.type };
  }
  const shrunk = await reencode(file);
  if (shrunk) return { base64: await toBase64(shrunk), mediaType: 'image/jpeg' };
  if (!isSupported(file.type)) {
    throw new ScanError(
      'bad_photo',
      "We can't read that kind of photo here. Use a JPEG, PNG, WebP or GIF, or type the numbers in yourself.",
    );
  }
  throw new ScanError('bad_photo', 'That photo is too large to send. Try a smaller photo, or type the numbers in yourself.');
}
