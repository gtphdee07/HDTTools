// Real account tokens for the live suites (weekly/ and release/): signs in the
// Supabase external test users and returns their access tokens. Credentials
// come from the environment, falling back to web/.env.local (where
// scripts/wizard_web_external_test_user.sh and
// scripts/wizard_scan_proxy_live_accounts.sh write them). A missing value
// fails the run naming the variable - it never skips on its own - and values
// are never printed.
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { decodeJwt } from "./jwt.ts";

const WEB_ENV_FILE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../web/.env.local");

export type TestAccount = "funded" | "noCredits";

const SUPABASE_VARS = ["VITE_SUPABASE_URL", "VITE_SUPABASE_PUBLISHABLE_KEY"];

const ACCOUNT_VARS: Record<TestAccount, { email: string; password: string }> = {
  funded: { email: "WEB_EXTERNAL_TEST_EMAIL", password: "WEB_EXTERNAL_TEST_PASSWORD" },
  // A second Supabase test user whose RevenueCat customer (named by its UUID) has no SCAN balance.
  noCredits: { email: "WEB_EXTERNAL_TEST_NOCREDITS_EMAIL", password: "WEB_EXTERNAL_TEST_NOCREDITS_PASSWORD" },
};

// KEY=value lines of a dotenv file (comments and blanks skipped, matching quotes stripped).
export function parseEnvText(text: string): Record<string, string> {
  const values: Record<string, string> = {};
  for (const line of text.split(/\r?\n/)) {
    const match = /^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/.exec(line);
    if (match) values[match[1]!] = match[2]!.replace(/^(["'])(.*)\1$/, "$2");
  }
  return values;
}

// Names (never values) among `names` that neither the environment nor the file provides.
export function missingVars(
  names: string[],
  env: Record<string, string | undefined>,
  fileValues: Record<string, string>,
): string[] {
  return names.filter((name) => !(env[name] || fileValues[name]));
}

// The file's values, or none at all if it doesn't exist.
export function readEnvFile(file: string = WEB_ENV_FILE): Record<string, string> {
  try {
    return parseEnvText(readFileSync(file, "utf8"));
  } catch {
    return {};
  }
}

function varsFor(accounts: TestAccount[]): string[] {
  return [...SUPABASE_VARS, ...accounts.flatMap((account) => Object.values(ACCOUNT_VARS[account]))];
}

// What the given accounts' sign-in still needs - lets the release suite skip
// (under SKIP_KEYS) or stop up front instead of failing mid-test.
export function liveCredentialsMissing(accounts: TestAccount[]): string[] {
  return missingVars(varsFor(accounts), process.env, readEnvFile());
}

// The values for `names`, or a thrown error naming (never showing) what's missing.
export function requireVars(
  names: string[],
  env: Record<string, string | undefined> = process.env,
  fileValues: Record<string, string> = readEnvFile(),
): Record<string, string> {
  const missing = missingVars(names, env, fileValues);
  if (missing.length > 0) {
    throw new Error(
      `Live test credentials missing (set them in the environment or web/.env.local): ${missing.join(", ")}`,
    );
  }
  return Object.fromEntries(names.map((name) => [name, (env[name] || fileValues[name])!]));
}

export function liveSupabaseUrl(): string {
  return requireVars(["VITE_SUPABASE_URL"]).VITE_SUPABASE_URL!;
}

export async function signInTestAccount(account: TestAccount): Promise<string> {
  const vars = ACCOUNT_VARS[account];
  const values = requireVars([...SUPABASE_VARS, vars.email, vars.password]);
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
  const { claims } = decodeJwt(token);
  const sub = (claims as { sub?: unknown } | undefined)?.sub;
  if (typeof sub !== "string" || !sub) throw new Error("access token has no sub claim");
  return sub;
}
