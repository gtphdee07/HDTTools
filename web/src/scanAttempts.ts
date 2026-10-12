import { ScanError } from './scanError';

// Gives each scan of a photo the request id the Scan service dedupes charges on. The id stays the same
// for as long as the answer to a photo's last request is unknown (the connection dropped, or the reply was
// not the service's), so the retry is the same logical scan and is charged once. Any answer from the
// service settles the attempt, and the next scan of that photo, or of another, starts a fresh id.
export class ScanAttempts {
  private open: { photo: File; id: string } | null = null;

  async run<T>(photo: File, scan: (clientRequestId: string) => Promise<T>): Promise<T> {
    const id = this.open?.photo === photo ? this.open.id : crypto.randomUUID();
    this.open = { photo, id };
    try {
      const result = await scan(id);
      this.open = null;
      return result;
    } catch (err) {
      if (!(err instanceof ScanError && err.lostResponse)) this.open = null;
      throw err;
    }
  }
}
