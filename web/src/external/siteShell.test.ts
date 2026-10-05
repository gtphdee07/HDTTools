import { describe, expect, it } from 'vitest';
import { assetUrls, bakedSecretKinds, bakedSupabaseHosts, hostOf } from './siteShell';

const SHELL = `<!doctype html>
<html lang="en"><head>
<title>RigCheck</title>
<script type="module" crossorigin src="/assets/index-AbC123.js"></script>
<link rel="stylesheet" crossorigin href="/assets/index-XyZ789.css">
<link rel="icon" type="image/png" href="/logo.png" />
</head><body><div id="root"></div></body></html>`;

describe('assetUrls', () => {
  it('resolves the module script and stylesheet against the site URL', () => {
    expect(assetUrls(SHELL, 'https://site.example/')).toEqual({
      scripts: ['https://site.example/assets/index-AbC123.js'],
      styles: ['https://site.example/assets/index-XyZ789.css'],
    });
  });

  it('ignores icon links and inline scripts', () => {
    const html = '<script>var a = 1</script><link rel="icon" href="/logo.png">';
    expect(assetUrls(html, 'https://site.example/')).toEqual({ scripts: [], styles: [] });
  });

  it('keeps an already-absolute URL as is', () => {
    const html = '<script type="module" src="https://cdn.example/app.js"></script>';
    expect(assetUrls(html, 'https://site.example/').scripts).toEqual(['https://cdn.example/app.js']);
  });
});

describe('bakedSupabaseHosts', () => {
  it('lists each distinct supabase.co host once', () => {
    const bundle = 'a("https://abcdefghij.supabase.co");b(`https://abcdefghij.supabase.co/auth/v1`);c("x.supabase.co")';
    expect(bakedSupabaseHosts(bundle)).toEqual(['abcdefghij.supabase.co', 'x.supabase.co']);
  });

  it('reports a placeholder host like undefined.supabase.co rather than hiding it', () => {
    expect(bakedSupabaseHosts('"https://undefined.supabase.co"')).toEqual(['undefined.supabase.co']);
  });

  it('is empty when the bundle names no supabase host', () => {
    expect(bakedSupabaseHosts('const a = "https://example.com"')).toEqual([]);
  });
});

const jwt = (payload: object) =>
  ['eyJhbGciOiJIUzI1NiJ9', Buffer.from(JSON.stringify(payload)).toString('base64url'), 'c2ln'].join('.');

describe('bakedSecretKinds', () => {
  it('is empty for a bundle with only a publishable key and the library mentioning sb_secret_ in prose', () => {
    const bundle = `const k="sb_publishable_abcdefghijklmnop1234";warn("do not use sb_secret_ keys in a browser")`;
    expect(bakedSecretKinds(bundle)).toEqual([]);
  });

  it('flags a real-looking sb_secret_ key without returning its value', () => {
    const kinds = bakedSecretKinds('const k="sb_secret_0123456789abcdefghijklmn"');
    expect(kinds).toEqual(['sb_secret_ key']);
    expect(JSON.stringify(kinds)).not.toContain('0123456789');
  });

  it('flags a service_role JWT but not an anon one', () => {
    expect(bakedSecretKinds(`k("${jwt({ role: 'service_role' })}")`)).toEqual(['service_role JWT']);
    expect(bakedSecretKinds(`k("${jwt({ role: 'anon' })}")`)).toEqual([]);
  });

  it('ignores JWT-looking text that is not valid base64 JSON', () => {
    expect(bakedSecretKinds('x("eyJhbGciOi.@@@.zzz")')).toEqual([]);
  });
});

describe('hostOf', () => {
  it('returns the host of a URL', () => {
    expect(hostOf('https://abcdefghij.supabase.co/anything?x=1')).toBe('abcdefghij.supabase.co');
  });
});
