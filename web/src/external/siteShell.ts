// Pure readers for the live Pages site's HTML shell and JS bundle, used by pagesSite.external.test.ts.

export interface AssetUrls {
  scripts: string[];
  styles: string[];
}

const attr = (tag: string, name: string) => new RegExp(String.raw`\b${name}\s*=\s*["']([^"']+)["']`, 'i').exec(tag)?.[1];

// The shell's external scripts and stylesheets, resolved to absolute URLs against the site.
export function assetUrls(html: string, siteUrl: string): AssetUrls {
  const scripts = [...html.matchAll(/<script\b[^>]*>/gi)]
    .map((m) => attr(m[0], 'src'))
    .filter((src): src is string => Boolean(src));
  const styles = [...html.matchAll(/<link\b[^>]*>/gi)]
    .filter((m) => attr(m[0], 'rel')?.toLowerCase() === 'stylesheet')
    .map((m) => attr(m[0], 'href'))
    .filter((href): href is string => Boolean(href));
  const resolve = (u: string) => new URL(u, siteUrl).href;
  return { scripts: scripts.map(resolve), styles: styles.map(resolve) };
}

// Every distinct "<name>.supabase.co" host named in a bundle, so a placeholder like undefined.supabase.co shows up.
export function bakedSupabaseHosts(bundle: string): string[] {
  return [...new Set([...bundle.matchAll(/[\w-]+\.supabase\.co/g)].map((m) => m[0]))];
}

const roleOf = (jwtPayload: string) => {
  try {
    return (JSON.parse(Buffer.from(jwtPayload, 'base64url').toString('utf8')) as { role?: unknown }).role;
  } catch {
    return undefined;
  }
};

// The kinds (never the values) of server-only Supabase credentials that a browser bundle must not contain.
// supabase-js itself mentions "sb_secret_" in a warning, so only a key-shaped token counts.
export function bakedSecretKinds(bundle: string): string[] {
  const kinds: string[] = [];
  if (/sb_secret_[\w-]{16,}/.test(bundle)) kinds.push('sb_secret_ key');
  const roles = [...bundle.matchAll(/eyJ[\w-]+\.([\w-]+)\.[\w-]+/g)].map((m) => roleOf(m[1]));
  if (roles.includes('service_role')) kinds.push('service_role JWT');
  return kinds;
}

export const hostOf = (url: string) => new URL(url).host;
