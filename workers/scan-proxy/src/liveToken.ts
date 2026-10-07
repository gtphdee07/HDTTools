// Real account tokens for the live suites (weekly/ and release/): signs in the
// Supabase external test users and returns their access tokens. Credentials
// come from the environment, falling back to web/.env.local (where
// scripts/wizard_web_external_test_user.sh writes them). A missing value fails
// the run naming the variable - it never skips - and values are never printed.
import { Buffer } from "node:buffer";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const WEB_ENV_FILE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../web/.env.local");

export type TestAccount = "funded" | "noCredits";

const ACCOUNT_VARS: Record<TestAccount, { email: string; password: string }> = {
  funded: { email: "WEB_EXTERNAL_TEST_EMAIL", password: "WEB_EXTERNAL_TEST_PASSWORD" },
  // A second Supabase test user whose RevenueCat customer (named by its UUID) has no SCAN balance.
  noCredits: { email: "WEB_EXTERNAL_TEST_NOCREDITS_EMAIL", password: "WEB_EXTERNAL_TEST_NOCREDITS_PASSWORD" },
};

function parseEnvFile(): Record<string, string> {
  let text: string;
  try {
    text = readFileSync(WEB_ENV_FILE, "utf8");
  } catch {
    return {};
  }
  const values: Record<string, string> = {};
  for (const line of text.split(/\r?\n/)) {
    const match = /^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/.exec(line);
    if (match) values[match[1]!] = match[2]!.replace(/^(["'])(.*)\1$/, "$2");
  }
  return values;
}

function requireVars(names: string[]): Record<string, string> {
  const fromFile = parseEnvFile();
  const values: Record<string, string> = {};
  const missing: string[] = [];
  for (const name of names) {
    const value = process.env[name] || fromFile[name];
    if (value) values[name] = value;
    else missing.push(name);
  }
  if (missing.length > 0) {
    throw new Error(
      `Live test credentials missing (set them in the environment or web/.env.local): ${missing.join(", ")}`,
    );
  }
  return values;
}

export function liveSupabaseUrl(): string {
  return requireVars(["VITE_SUPABASE_URL"]).VITE_SUPABASE_URL!;
}

export async function signInTestAccount(account: TestAccount): Promise<string> {
  const vars = ACCOUNT_VARS[account];
  const values = requireVars(["VITE_SUPABASE_URL", "VITE_SUPABASE_PUBLISHABLE_KEY", vars.email, vars.password]);
  const res = await fetch(`${values.VITE_SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: values.VITE_SUPABASE_PUBLISHABLE_KEY!, "Content-Type": "application/json" },
    body: JSON.stringify({ email: values[vars.email], password: values[vars.password] }),
    signal: AbortSignal.timeout(15_000),
  });
  if (!res.ok) {
    throw new Error(`Supabase sign-in for the ${account} test account failed with HTTP ${res.status}`);
  }
  const body = (await res.json()) as { access_token?: unknown };
  if (typeof body.access_token !== "string" || !body.access_token) {
    throw new Error(`Supabase sign-in for the ${account} test account returned no access_token`);
  }
  return body.access_token;
}

// The account id a token names - the RevenueCat customer id the Worker will spend.
export function subjectOf(token: string): string {
  const claims = JSON.parse(Buffer.from(token.split(".")[1] ?? "", "base64url").toString("utf8")) as { sub?: unknown };
  if (typeof claims.sub !== "string" || !claims.sub) throw new Error("access token has no sub claim");
  return claims.sub;
}
