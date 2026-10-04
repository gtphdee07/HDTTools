import { describe, expect, it } from 'vitest';
import viteConfig from '../../vite.config';

// Guards for the External suite's ground rules (ADR-0008), checked statically so they run in `npm test`.

const externalFiles = import.meta.glob('./*.external.test.ts', { query: '?raw', import: 'default', eager: true }) as Record<
  string,
  string
>;

const globToRegExp = (glob: string) =>
  new RegExp(
    '^' +
      glob
        .replace(/[.+^${}()|[\]\\]/g, '\\$&')
        .replace(/\*\*\//g, '(.*/)?')
        .replace(/\*/g, '[^/]*') +
      '$',
  );

describe('npm test never collects external tests', () => {
  const excludes = (viteConfig as { test?: { exclude?: string[] } }).test?.exclude ?? [];

  it('has external test files to protect', () => {
    expect(Object.keys(externalFiles).length).toBeGreaterThan(0);
  });

  it.each(Object.keys(externalFiles))('excludes %s in the default config', (file) => {
    const path = 'src/external/' + file.replace('./', '');
    expect(excludes.some((glob) => globToRegExp(glob).test(path))).toBe(true);
  });
});

describe('external test files never create users, send mail or print secrets', () => {
  const files = Object.entries(externalFiles);
  const calls = (text: string, method: string) => [...text.matchAll(new RegExp(String.raw`\.${method}\(([^)]*)\)`, 'g'))];

  it.each(files)('%s: sign-up and reset only ever use the malformed-address constant', (_name, text) => {
    expect(text).toMatch(/const MALFORMED_EMAIL = '[^'@]*'/);
    const signUps = calls(text, 'signUp');
    const resets = calls(text, 'resetPasswordForEmail');
    for (const m of signUps) expect(m[1]).toMatch(/^\s*\{\s*email: MALFORMED_EMAIL,/);
    for (const m of resets) expect(m[1].trim()).toBe('MALFORMED_EMAIL');
  });

  it.each(files)('%s: no other sign-up or recovery path is used', (_name, text) => {
    expect(text).not.toMatch(/\.(signInWithOtp|inviteUserByEmail|resend|admin\b)/);
    expect(text).not.toMatch(/\/auth\/v1\/(signup|recover|otp|magiclink|invite)/);
  });

  it.each(files)('%s: never logs, and never puts the password or key on a line that outputs', (_name, text) => {
    expect(text).not.toMatch(/console\.|process\.stdout|\.log\(/);
    const sensitive = text.split('\n').filter((l) => /PASSWORD|PUBLISHABLE_KEY/.test(l) && !l.includes('REQUIRED'));
    for (const line of sensitive) {
      expect(line).not.toMatch(/expect\(|Error\(|toBe\(|toEqual\(|toThrow|message/);
    }
  });
});
