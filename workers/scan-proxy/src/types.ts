export type MediaType = "image/jpeg" | "image/png" | "image/webp" | "image/gif";

export interface Env {
  // Secrets — set via `wrangler secret put <NAME>`, never committed.
  ANTHROPIC_API_KEY: string;
  REVENUECAT_SECRET_KEY: string;

  // Plain config — set in wrangler.toml's [vars].
  REVENUECAT_PROJECT_ID: string;
  REVENUECAT_CURRENCY_CODE: string;
}
