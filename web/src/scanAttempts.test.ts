import { describe, expect, it } from 'vitest';
import { ScanAttempts } from './scanAttempts';
import { ScanError } from './scanError';

const photo = (name: string) => new File([name], `${name}.jpg`, { type: 'image/jpeg' });

async function idsOf(attempts: ScanAttempts, photoFile: File, outcomes: Array<'ok' | ScanError>) {
  const ids: string[] = [];
  for (const outcome of outcomes) {
    await attempts
      .run(photoFile, async (id) => {
        ids.push(id);
        if (outcome !== 'ok') throw outcome;
      })
      .catch(() => {});
  }
  return ids;
}

describe('ScanAttempts', () => {
  it('reuses the request id for the same photo while the last answer was lost', async () => {
    const lost = new ScanError('network', 'offline', true);

    const [first, second, third] = await idsOf(new ScanAttempts(), photo('a'), [lost, lost, 'ok']);

    expect(second).toBe(first);
    expect(third).toBe(first);
  });

  it('starts a fresh id after the service answered, whether it delivered or named a failure', async () => {
    const refunded = new ScanError('extraction_failed', 'refunded');

    const afterFailure = await idsOf(new ScanAttempts(), photo('a'), [refunded, 'ok']);
    const afterSuccess = await idsOf(new ScanAttempts(), photo('a'), ['ok', 'ok']);

    expect(afterFailure[1]).not.toBe(afterFailure[0]);
    expect(afterSuccess[1]).not.toBe(afterSuccess[0]);
  });

  it('starts a fresh id for a different photo even if the last answer was lost', async () => {
    const attempts = new ScanAttempts();
    const lost = new ScanError('network', 'offline', true);

    const [first] = await idsOf(attempts, photo('a'), [lost]);
    const [second] = await idsOf(attempts, photo('b'), ['ok']);

    expect(second).not.toBe(first);
  });
});
