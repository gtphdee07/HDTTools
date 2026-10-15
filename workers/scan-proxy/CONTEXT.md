# Scan Proxy

The Cloudflare Worker that gates paid Claude-vision scans behind a purchase, and performs the scan on the client's behalf so the Anthropic API key never ships in the app.

## Language

**Scan**:
One request to extract fields from a photographed document (Truck Tag, Trailer Tag, or Scale Ticket — see Core's `CONTEXT.md`) via Claude vision, gated by Scan Credit.

**Scan Credit**:
The unit of paid usage, implemented as a RevenueCat "virtual currency" (currency code `SCAN`). A user's Scan Credit balance is spent before a Scan runs and refunded if the Scan fails to deliver a result.

**Spend / Refund**:
The two credit-balance operations Scan Proxy performs against RevenueCat directly (server-side, not through the client SDK's own purchase flow): Spend happens before the costly Claude call; Refund happens only if extraction then fails, so a user is never billed for a Scan that didn't deliver.
A **delivered** Scan is charged even if the client then finds nothing usable in it (for example a Scale Ticket answer with no weight). The Worker does not interpret document contents, and whether a usable value was found depends on the document and is decided only on the client, so there is no refund for it; clients tell the user the Scan was used.

**Account token**:
The signed Supabase access token (a JWT, ES256) a signed-in user's client sends as `Authorization: Bearer` on every Scan. The Worker verifies it against Supabase's public keys and takes the token's `sub` — the account id, which is also the RevenueCat app user id — as the one whose Scan Credit is spent. Anonymous Supabase users' tokens are refused. No request field can name a different account. Its expected shape is defined once, in `src/accountTokenContract.ts`.

**Idempotency Key**:
The key RevenueCat receives with a Spend (and, with a `-refund` suffix, its Refund), making them safe to retry without double-charging or double-refunding after a lost or timed-out response. The Worker derives it as a hash of the verified account, document type, media type, image and the client's `client_request_id` (an id the client keeps stable across retries of the same logical Scan attempt), so the client's id alone never decides what is charged.

**Time limits**:
How long a Scan may take, and how the Worker's limit and each client's limit agree. A client that gives up before the Worker can finish abandons a Scan the Worker then completes and charges for, and the user never sees the result. Decided 2026-10-15 (#112): the Worker makes **one** Claude attempt and never retries it (the Anthropic SDK's default of two retries, which also honours a `Retry-After` of up to 60 s per wait, made the worst case about 87 s at best and unbounded in practice). A failed attempt already refunds the Scan Credit and the user retries at no charge, so a silent retry bought little.

| Step | Limit |
| --- | --- |
| Sign-in key fetch (`JWKS_TIMEOUT_MS`) | 5 s |
| Credit spend (`REVENUECAT_TIMEOUT_MS`) | 10 s |
| Claude call (`ANTHROPIC_TIMEOUT_MS`, `ANTHROPIC_MAX_RETRIES` = 0) | 20 s |
| Credit refund, only if the Claude call failed (`REVENUECAT_TIMEOUT_MS`) | 10 s |
| **Worker worst case** | **45 s** |
| Android (`ScanApiClient` read timeout) | 60 s |
| Web (`SCAN_TIMEOUT_MS` in `web/src/api.ts`, the whole exchange) | 60 s |

Both clients' limits must stay above the Worker's worst case. `src/timeLimits.test.ts` reads the two clients' values from their own source and fails if either is not above the sum, or if retries are turned back on. Changing any Worker step's limit, or the retry count, means redoing this table; a Worker change goes live (`wrangler deploy`) before a client's limit is lowered, or the old Worker's longer worst case outlasts the new limit. Android's read timeout only bounds the gap between reads; a `callTimeout` for the whole exchange is not set.

**Entitlement** (reserved term — narrower uses should say "Scan Credit balance," not "entitlement"):
The cross-platform question of which system is the **source of truth** for a user's paid status. Decided 2026-09-23 (see ADR-0003): RevenueCat, for both Android and Web — no owned entitlements database exists. Scan-gating itself also unifies into one shared Worker serving both platforms under this decision (also ADR-0003). Don't use "entitlement" for the per-request "does this user have enough Scan Credit balance" check performed inside `runScan` — that's a Spend, and a `422`/`insufficient_credits` response from it is a balance check, not the entitlement source-of-truth question this term refers to.
