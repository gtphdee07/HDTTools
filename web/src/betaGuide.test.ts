// @vitest-environment node
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { FEEDBACK_EMAIL, WEB_ADDRESS } from './betaKit';

// The tester guide (#181) is read as a plain file: the two addresses a tester copies from it must be
// the ones the Web app uses, and each thing a tester needs must still have a section.
const guide = readFileSync(new URL('../../docs/BETA_TESTER_GUIDE.md', import.meta.url), 'utf8');

describe('docs/BETA_TESTER_GUIDE.md', () => {
  it('names the Web address and the feedback address the Web app uses', () => {
    expect(guide).toContain(WEB_ADDRESS);
    expect(guide).toContain(FEEDBACK_EMAIL);
  });

  it('keeps a section for each thing a tester needs', () => {
    const headings = [...guide.matchAll(/^## (.+)$/gm)].map((m) => m[1]);
    expect(headings).toEqual(
      expect.arrayContaining([
        'Where to find it',
        'Installing the Android app',
        'Making an account',
        'What is fake',
        'What RigCheck is not',
        'What is not in this test yet',
        'Privacy',
        'What to try',
        'How to report a problem',
      ]),
    );
  });
});
