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

**Scan outcomes**:
Every way a Scan can end without the user getting all the fields they expected, what the user is told, and how a retry behaves. Written here once because the words and rules lived in each client and drifted (#111, #115). Decided 2026-10-14 (#111, D1 to D10); research in `docs/research/scan-failure-handling.md`. The rows are also the shared fixture `test-vectors/scan_outcomes.json`, which Web (`web/src/scanOutcomes.test.ts`) and Android (`ScanOutcomesFixtureTest.kt`) each load and check their own behaviour against, as both do for `test-vectors/breakdown_cases.json`. Change a row here and in the fixture together; a client that disagrees with a row fails its test. Each client keeps its own strings in one place (Web: `api.ts`, `scanImage.ts`, `scanError.ts`, `scanNotice.ts`; Android: `ScanMessages.kt`, with `ScanFailure.kt` and `ScanNotice.kt`); there is no shared code table, since the clients are in different languages.

Every message says whether a Scan Credit was used, whether it was refunded, whether a retry costs another, and the next step (the order is not pinned). A message may word a sentence its own way, and Web may write "scan" where Android writes "Scan"; the fixture pins the phrases in the last column below.

| # | Case | Spent | Refunded | Retry keeps the request id | Try again | Next step |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `insufficient_credits` (402) | no | n/a | no | no | buy a pack (Pro) or upgrade (Free) |
| 2 | `unauthorized` (401) | no | n/a | no | no | sign in again |
| 3 | `auth_unavailable` (503) | no | n/a | no | yes | try again shortly |
| 4 | `extraction_failed` (502) | yes | **yes** | no | yes | a clearer photo, or type it in; a new attempt is a new Scan |
| 5 | `extraction_failed_no_refund` (502) | yes | **no** (the refund failed) | **yes** | yes | try the same photo again; contact support if it keeps happening |
| 6 | `billing_error` (502) | **unknown** | n/a | **yes** | yes | try again |
| 7 | `bad_request` (400) | no | n/a | no | no | a different photo, or type it in |
| 8 | A photo the client cannot send | no | n/a | no | no | a different photo, or type it in |
| 9 | No scan service address in this build (Web only) | no | n/a | no | no | type it in |
| 10a | No connection | **unknown** | n/a | **yes** | yes | try again |
| 10b | A reply that is not the Worker's (an edge error page, an unreadable success) | **unknown** | n/a | **yes** | yes | try again |
| 11 | No answer within the client's time limit (see Time limits) | **unknown** | n/a | **yes** | yes | try again |
| 12a | Delivered, every field blank | yes | **no** | no | no | type it in, or a different photo |
| 12b | Delivered, a stand-alone ticket with no weight | yes | **no** | no | no | type the weight in, or a different photo |
| 12c | Delivered, some fields blank | yes | **no** | no | no | type the blank ones in, or a different photo |
| 12d | Delivered, every field filled (a value that looks wrong is fixed on the review step) | yes | **no** | no | no | none; no notice |

What the user reads (the phrases in the fixture are taken from these):

1. "You're out of Scans. Nothing was used. Buy more Scans, or type the numbers in yourself."
2. "Your sign-in has expired. Nothing was used. Sign in again to scan."
3. "We couldn't verify your account just now. Nothing was used. Try again in a moment."
4. "We couldn't read that photo, and your Scan Credit was refunded. Trying again uses another Scan. A clearer photo may work better, or type the numbers in yourself."
5. "We couldn't read that photo, and couldn't refund your Scan Credit automatically. Trying this photo again won't charge you again. If it keeps happening, contact support."
6. "We couldn't confirm your Scan balance, so nothing was read. You may not have been charged. Try again in a moment; a retry is not charged twice."
7. "We couldn't use that photo. Try a different photo, or type the numbers in yourself. Nothing was used." The Worker's own text for what it disliked is for developers and is never shown.
8. "We couldn't open that photo. Try a different photo, or type the numbers in yourself. Nothing was used." (Web names the format or the size instead of "open"; it says the same two other things.)
9. "Scanning is not set up on this site. Nothing was used. You can type the numbers in yourself."
10a. "We couldn't reach the scan service. You may not have been charged. Check your connection and try again; a retry is not charged twice."
10b. "We didn't get a usable answer from the scan service. You may not have been charged. Try again; a retry is not charged twice."
11. "The scan service took too long to answer. You may not have been charged. Try again; a retry is not charged twice."
12a. "A Scan was used and nothing could be read. Type the numbers in, or go back and choose a different photo."
12b. "We read the ticket but couldn't find a weight. That Scan was used, and trying again uses another. Type the weight in, or choose a different photo."
12c. "A Scan was used, but we couldn't read: <fields>. Type them in, or go back and choose a different photo." Name the fields that were not read with the labels the entry screen shows for them, joined as `A`, `A and B` or `A, B and C`; with exactly one, the last sentence reads "Type it in, or go back and choose a different photo." Fields a Scan does not read (a name, an axle count, a stand-alone weight) are never named.

Rows 12a to 12d are a notice on the screen the Scan leads to, not a failure state (D1): the Scan was delivered and charged, so it offers no Try again (D2; the same photo would probably read the same, as another paid Scan). The notice goes away when the user leaves that screen or types in every field that was blank.

Retry rules:
- **Same request id** when the answer to the last request is unknown, or the Scan was charged and not refunded: rows 5, 6, 10a, 10b and 11. The retry must be for the same photo (the Idempotency Key also covers the image). Web keeps it per photo file (`ScanAttempts`), Android per photo and document.
- **New request id** after any answer that settles the attempt: a delivered Scan, and rows 1 to 4, 7 and 8. The next Scan is a new paid Scan.
- **Try again** is offered only where sending the same photo again is free or correctly priced (rows 3 to 6, 10a, 10b, 11). Where the same photo would fail again or is not wanted, the next step is a different photo or typing the numbers in.
- After every outcome the balance on screen is read again; after row 1 it is first set to 0 because the Worker has just said so. A failed read leaves the balance as it was and says nothing (D6, D7).

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
