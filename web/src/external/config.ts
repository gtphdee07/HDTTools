export const REQUIRED = [
  'VITE_SUPABASE_URL',
  'VITE_SUPABASE_PUBLISHABLE_KEY',
  'WEB_EXTERNAL_TEST_EMAIL',
  'WEB_EXTERNAL_TEST_PASSWORD',
] as const;

export type ExternalConfig = Record<(typeof REQUIRED)[number], string>;

// A missing credential must fail the run, never skip it. The message names variables only, never values.
export function readConfig(env: Record<string, string | undefined>): ExternalConfig {
  const missing = REQUIRED.filter((name) => !env[name]);
  if (missing.length > 0) {
    throw new Error(`External test credentials missing (set them in web/.env.local): ${missing.join(', ')}`);
  }
  return Object.fromEntries(REQUIRED.map((name) => [name, env[name]])) as ExternalConfig;
}
