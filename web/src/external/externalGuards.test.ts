import { describe, expect, it } from 'vitest';
import viteConfig from '../../vite.config';
import externalConfig from '../../vitest.external.config';

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
    const signUps = calls(text, 'signUp');
    const resets = calls(text, 'resetPasswordForEmail');
    // A file that never signs up or resets (e.g. the Pages site's) has nothing to constrain.
    if (signUps.length + resets.length > 0) expect(text).toMatch(/const MALFORMED_EMAIL = '[^'@]*'/);
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

describe('the Pages site test never runs with the test-account credentials', () => {
  type Project = { test?: { name?: string; include?: string[]; exclude?: string[]; env?: Record<string, string> } };
  const resolved = (externalConfig as unknown as (env: { mode: string; command: string }) => { test?: { projects?: Project[] } })({
    mode: 'test',
    command: 'serve',
  });
  const projects = resolved.test?.projects ?? [];
  const pages = projects.find((p) => p.test?.name === 'pages-site');
  const others = projects.filter((p) => p.test?.name !== 'pages-site');

  it('runs the Pages site test as its own project', () => {
    expect(pages).toBeDefined();
    expect(pages?.test?.include).toEqual(['src/**/pagesSite.external.test.ts']);
  });

  it('gives that project only the VITE_SUPABASE_ variables, never WEB_EXTERNAL_ ones', () => {
    expect(pages).toBeDefined();
    const names = Object.keys(pages?.test?.env ?? {});
    expect(names.filter((n) => n.startsWith('WEB_EXTERNAL_'))).toEqual([]);
    expect(names.filter((n) => !n.startsWith('VITE_SUPABASE_'))).toEqual([]);
  });

  it('keeps every other external test in a project that excludes the Pages test, so none is silently skipped', () => {
    expect(others.length).toBeGreaterThan(0);
    for (const p of others) {
      expect(p.test?.include).toEqual(['src/**/*.external.test.ts']);
      expect(p.test?.exclude).toContain('src/**/pagesSite.external.test.ts');
    }
  });

  const pagesText = Object.entries(externalFiles).find(([name]) => name.includes('pagesSite'))?.[1] ?? '';

  it('the test scrubs any inherited WEB_EXTERNAL_ variable before evaluating fetched code', () => {
    const scrub = pagesText.indexOf("startsWith('WEB_EXTERNAL_')");
    const evalAt = pagesText.indexOf('(0, eval)(');
    expect(scrub).toBeGreaterThan(-1);
    expect(scrub).toBeLessThan(evalAt);
  });

  it('the test refuses fetched script or stylesheet URLs from another origin', () => {
    expect(pagesText).toContain('foreignUrls(');
  });
});

describe('the Pages site external test only reads', () => {
  const [pagesFile, text] = Object.entries(externalFiles).find(([name]) => name.includes('pagesSite')) ?? ['', ''];

  it('exists', () => {
    expect(pagesFile).not.toBe('');
  });

  it('never signs in, never submits a form and only issues GETs', () => {
    expect(text).not.toMatch(/signInWithPassword|\.submit\(|requestSubmit|method:\s*['"](POST|PUT|PATCH|DELETE)/i);
    expect(text).not.toMatch(/\.(signUp|resetPasswordForEmail)\(/);
  });
});
