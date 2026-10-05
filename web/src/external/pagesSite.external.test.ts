// @vitest-environment jsdom
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { readConfig } from './config';
import { assetUrls, bakedSecretKinds, bakedSupabaseHosts, foreignUrls, hostOf } from './siteShell';

// External suite (ADR-0008): real requests to the deployed Cloudflare Pages site, run only via
// `npm run test:external`. The "[pages-site]" name tag is what the wrapper filters on.
// Read-only: it only GETs public URLs, and the journey stops at the sign-in screen (it never
// submits the form). The site is public, so there is nothing to authenticate against.
// Only the Supabase variables are needed, to know what the production build should have baked in.

const SITE_URL = 'https://rigcheck-web.pages.dev/';
// Pages has no 404 page configured, so any path must fall back to the app shell.
const UNKNOWN_PATHS = ['/no/such/page', '/history/deep/link'];

const REQUIRED_HERE = ['VITE_SUPABASE_URL', 'VITE_SUPABASE_PUBLISHABLE_KEY'] as const;

const get = (url: string) => fetch(url);

async function until<T>(probe: () => T | null | undefined, what: string, ms = 10_000): Promise<T> {
  const deadline = Date.now() + ms;
  for (;;) {
    const found = probe();
    if (found) return found;
    if (Date.now() > deadline) throw new Error(`Timed out waiting for ${what}`);
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
}

const buttonsNamed = (name: string) => [...document.querySelectorAll('button')].filter((b) => b.textContent?.trim() === name);

describe('[pages-site] Deployed Pages site live contract', () => {
  let cfg: Record<(typeof REQUIRED_HERE)[number], string>;
  let shell: string;
  let shellResponse: Response;
  let bundleResponse: Response;
  let bundle: string;
  let assets: ReturnType<typeof assetUrls>;

  beforeAll(async () => {
    // The journey runs fetched code in this process. vitest.external.config.ts already keeps the test-account
    // credentials out of this project's env; scrub any that a shell export inherited as well.
    for (const name of Object.keys(process.env)) if (name.startsWith('WEB_EXTERNAL_')) delete process.env[name];

    cfg = readConfig(import.meta.env as Record<string, string | undefined>, REQUIRED_HERE);
    shellResponse = await get(SITE_URL);
    shell = await shellResponse.text();
    assets = assetUrls(shell, SITE_URL);
    const foreign = foreignUrls(assets.scripts, SITE_URL);
    if (foreign.length > 0) throw new Error(`The shell names a script on another origin; refusing to fetch or run it: ${foreign.join(', ')}`);
    bundleResponse = await get(assets.scripts[0] ?? SITE_URL);
    bundle = await bundleResponse.text();
  });

  afterAll(() => {
    document.body.innerHTML = '';
  });

  it('serves the app shell with a 200 over HTML', () => {
    expect(shellResponse.status).toBe(200);
    expect(shellResponse.headers.get('content-type')).toMatch(/^text\/html/);
    expect(shell).toContain('<div id="root"></div>');
    expect(shell).toContain('<title>RigCheck');
  });

  it('serves the JS bundle and stylesheet the shell references', async () => {
    expect(assets.scripts).toHaveLength(1);
    expect(assets.styles).toHaveLength(1);
    expect(foreignUrls([...assets.scripts, ...assets.styles], SITE_URL)).toEqual([]);

    expect(bundleResponse.status).toBe(200);
    expect(bundleResponse.headers.get('content-type')).toMatch(/javascript/);
    // Booleans, not `expect(bundle)`, so a failure never prints the whole bundle.
    expect(bundle.length).toBeGreaterThan(100_000);
    const isHtml = /^\s*<!doctype html/i.test(bundle);
    expect(isHtml).toBe(false);

    const css = await get(assets.styles[0]);
    expect(css.status).toBe(200);
    expect(css.headers.get('content-type')).toMatch(/^text\/css/);

    const logo = await get(new URL('/logo.png', SITE_URL).href);
    expect(logo.status).toBe(200);
    expect(logo.headers.get('content-type')).toMatch(/^image\/png/);
  });

  it('has the configured Supabase project host baked into the production bundle', () => {
    const expectedHost = hostOf(cfg.VITE_SUPABASE_URL);
    expect(expectedHost).toMatch(/^[a-z0-9]{20}\.supabase\.co$/);
    // Exactly the configured project: no undefined, placeholder or second project host.
    expect(bakedSupabaseHosts(bundle)).toEqual([expectedHost]);
  });

  it('has the configured publishable key baked in and no secret key', () => {
    const baked = bundle.includes(cfg.VITE_SUPABASE_PUBLISHABLE_KEY);
    expect(baked).toBe(true);
    expect(bakedSecretKinds(bundle)).toEqual([]);
  });

  it.each(UNKNOWN_PATHS)('serves the app shell, not a platform error page, for the unknown path %s', async (path) => {
    const response = await get(new URL(path, SITE_URL).href);
    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toMatch(/^text\/html/);
    expect(await response.text()).toBe(shell);
  });

  it('runs without the test-account credentials in its process environment', () => {
    expect(Object.keys(process.env).filter((name) => name.startsWith('WEB_EXTERNAL_'))).toEqual([]);
  });

  it('journey: loads the page and reaches the sign-in screen', async () => {
    const body = new DOMParser().parseFromString(shell, 'text/html').body;
    body.querySelectorAll('script').forEach((s) => s.remove());
    document.body.innerHTML = body.innerHTML;

    // Run the live production bundle as the browser would. The shell loads it as a module, but Vite emits a
    // single chunk with no import or export statements, so it also runs as a plain script here.
    (0, eval)(bundle);

    const [signIn] = await until(() => (buttonsNamed('Sign in').length > 0 ? buttonsNamed('Sign in') : null), 'the "Sign in" button in the header');
    signIn.click();

    const email = await until(() => document.querySelector('input[type="email"]'), 'the email field');
    expect(email).not.toBeNull();
    expect(document.querySelector('input[type="password"]')).not.toBeNull();
    expect(document.body.textContent).not.toContain('Accounts unavailable');
    // The header button and the form's submit button are both named "Sign in".
    expect(buttonsNamed('Sign in')).toHaveLength(2);
  });
});
