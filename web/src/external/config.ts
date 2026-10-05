export const REQUIRED = [
  'VITE_SUPABASE_URL',
  'VITE_SUPABASE_PUBLISHABLE_KEY',
  'WEB_EXTERNAL_TEST_EMAIL',
  'WEB_EXTERNAL_TEST_PASSWORD',
] as const;

export type ConfigName = (typeof REQUIRED)[number];
export type ExternalConfig = Record<ConfigName, string>;

// A missing credential must fail the run, never skip it. The message names variables only, never values.
// `names` narrows the check to what one surface actually needs (e.g. the Pages site needs no test account).
export function readConfig(env: Record<string, string | undefined>): ExternalConfig;
export function readConfig<N extends ConfigName>(env: Record<string, string | undefined>, names: readonly N[]): Record<N, string>;
export function readConfig(env: Record<string, string | undefined>, names: readonly ConfigName[] = REQUIRED) {
  const missing = names.filter((name) => !env[name]);
  if (missing.length > 0) {
    throw new Error(`External test credentials missing (set them in web/.env.local): ${missing.join(', ')}`);
  }
  return Object.fromEntries(names.map((name) => [name, env[name]]));
}
