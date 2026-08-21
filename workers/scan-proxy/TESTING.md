# scan-proxy testing

This Worker's tests are organized into tiers, matching the tiered
regression strategy described in the root repo's `NEXT_STEPS.md`. This
file documents the tiers themselves and what each individual test
covers, so picking this back up doesn't require reading every test file
cold. It's a reference for current state — see `NEXT_STEPS.md` for the
narrative history (when each tier was built, what bugs were found along
the way, why specific design choices were made). See the root
`TESTING.md`'s "Reconciling with per-platform network/cadence tiers"
section for how this tiering relates to that file's Minor/Major
regression-scoping rules — the two are independent axes, not
alternatives to choose between.

## Tiers

| Tier | Status | Cadence | Network calls | Command |
|---|---|---|---|---|
| **Sanity** | ✅ built | before every commit | none (mocked) | `npm run test:sanity` |
| **Daily** | ✅ built | while actively working on this Worker | none (mocked) | `npm test` |
| **Weekly** | not built | weekly / before an uncertain deploy | real, bounded, dedicated test customer | `npm run test:weekly` (doesn't exist yet) |
| **Release** | not built | before/after every `wrangler deploy` | real, against the live deployed Worker | `npm run test:release` (doesn't exist yet) |

Sanity is a small subset of daily's tests, tagged `[sanity]` in their
names and selected via `node --test`'s `--test-name-pattern`, not a
separate set of test files. Weekly and release are deliberately deferred
until a dedicated disposable RevenueCat test customer exists (separate
from `smoke-test-user`, which is reserved for manual Android field
testing) — see `NEXT_STEPS.md`'s scan-proxy section for that status.

All tiers are run manually — there is no CI in this repo.

## What each test covers

Organized by file, in the order a request actually flows through the
Worker (`index.ts` → `request.ts` → `scan.ts` → `revenuecat.ts` /
`claude.ts` → `http.ts`/`docTypes.ts` as shared support). `[sanity]` marks
tests also included in the sanity tier.

### `docTypes.test.ts` — the static prompt/schema config per document type

- `[sanity]` **every doc type has a complete config** — every entry in
  `DOC_TYPE_CONFIG` has a non-empty prompt/tool name/description and an
  object-typed schema.
- **every schema's required list matches its properties, including
  nested tire schemas** — recursively checks `required[]` exactly
  matches `properties` keys at every level (including the nested
  `front_tire`/`rear_tire`/`tire` schemas) — guards against copy-paste
  drift from hand-porting near-identical schemas across doc types.
- **every doc type's schema still contains the field names the Android
  client reads** — checks the schema still has the exact keys
  `ScanFieldMapping.kt` on Android depends on (e.g. `front_gawr_lb` for
  `truck_tag`, `gawr_per_axle_lb` for `trailer_tag`). The
  required-matches-properties test above only checks internal
  self-consistency; this is the one that would catch a field silently
  disappearing.
- **toolName values are unique across doc types** — no two doc types
  could be confused with each other by Claude's tool-choice mechanism.

### `request.test.ts` — `parseScanRequest`'s validation

- `[sanity]` **parses a fully valid request** — the whole-object happy path.
- **defaults media_type to image/jpeg when omitted**.
- **rejects a non-object body** — string, `null`, and a bare number all rejected.
- **rejects a missing or blank app_user_id** — empty string, whitespace-only, and key entirely absent.
- **rejects an invalid doc_type** — an unrecognized value, and the key entirely absent.
- **rejects a missing image_base64** — empty string, and the key entirely absent.
- **rejects an unsupported media_type** — e.g. `image/heic`.
- **rejects wrong-typed fields, not just wrong/missing values** — a number where `app_user_id`/`doc_type`/`image_base64` should be a string, and an array where `doc_type` should be a string.
- **an explicit null media_type is treated the same as an omitted one**.
- **rejects an array payload the same way as any other non-conforming object** — `[]` and `["truck_tag"]`.
- **silently ignores unknown extra fields rather than rejecting them** — documents intended behavior (only the four known keys are ever read).

### `scan.test.ts` — `runScan`, the money-critical charge/extract/refund control flow (fake `ScanDeps`, no real network)

- `[sanity]` **successful scan charges exactly once and returns the extracted fields**.
- **insufficient credits (422) returns 402 and never calls Claude** — proves the pay-before-extract ordering short-circuits correctly.
- **a non-422 billing failure returns 502 and never calls Claude**.
- **extraction failure refunds the credit for the same user and reports extraction_failed**.
- **a failed refund attempt doesn't crash the request, and doesn't falsely claim a refund happened** — pins down the fix for the real "Credit refunded" lying-message bug found 2026-08-19: a refund that throws now returns `extraction_failed_no_refund` with an honest message, not the old always-says-refunded text.
- **a refund call that resolves with ok:false (not a throw) is also treated as a failed refund** — the other way a refund can fail without throwing.
- **a successful scan never issues a refund**.
- **spendCredit and refundCredit are called with the same idempotency key** — scan.ts's own responsibility (revenuecat.ts derives the refund's distinct `-refund` suffix from whatever raw key it's given); a regression minting a fresh key per call would silently break the charge/refund pairing.
- **spendCredit itself rejecting propagates out of runScan rather than being caught** — documents a known gap: no `try/catch` around the spend call, so a real network failure here currently means an ungraceful failure rather than a clean `billing_error` response.
- **trailer_tag and scale_ticket scans use their own doc type's config and echo it back** — every other test in this file uses `truck_tag`; this is the only one exercising the other two doc types through `runScan` directly.

### `revenuecat.test.ts` — `spendCredit`/`refundCredit`, the RevenueCat Virtual Currency API client (`fetch`-mocked)

- `[sanity]` **spendCredit posts a -1 adjustment to the right URL with the right headers** — URL, method, `Authorization`, `Idempotency-Key`, and body shape.
- **refundCredit posts a +1 adjustment with a distinct idempotency key** — the `-refund` suffix.
- **URL-encodes the customer id** — a customer id with spaces/slashes.
- **a 422 (insufficient balance) is surfaced as ok:false, not thrown** — this response IS the entitlement check.
- **a non-JSON error body doesn't throw** — an HTML error page from a 502 doesn't crash the parser; `body` ends up `null`.
- **a network failure (fetch rejecting) propagates out of spendCredit rather than being caught** — documents a known gap, the same shape as `scan.test.ts`'s matching case one layer up.
- **uses the currency code from env, not a value baked into the module** — a non-`SCAN` currency code flows through into the adjustment body correctly.
- **the real response body is returned to the caller, not discarded** — the success-path body isn't just treated as opaque.

### `claude.test.ts` — `extractFields`, the only module touching the real `@anthropic-ai/sdk` (`fetch`-mocked at the HTTP boundary, not the SDK internals)

- `[sanity]` **extracts fields from a matching tool_use block** — happy path, and asserts the actual HTTP request sent (URL, model, `tool_choice`, image `source`/`media_type`/`data`).
- **throws when no content block matches the requested tool** — the single most important case in this file: this is exactly the branch `scan.ts`'s entire refund path exists to handle.
- **finds the matching tool_use block even when a non-matching block comes first** — a text block before the real tool_use block.
- **a tool_use block with a different tool name is not accepted** — falls through to the same throw as no match at all.

### `http.test.ts` — `json`/`badRequest`, the response-shaping helpers used everywhere

- `[sanity]` **json() defaults to status 200 with a JSON content-type**.
- **json() uses the given status when provided**.
- **json() round-trips nested objects, arrays, and nulls unchanged**.
- **badRequest() returns the exact ok:false/bad_request envelope at 400**.

### `index.test.ts` — the router/entry point, `worker.fetch` (real `defaultScanDeps` — no injection point at this layer, so `fetch` is mocked to route by URL between RevenueCat and Anthropic)

- `[sanity]` **a valid POST /v1/scan runs the real dependency wiring end-to-end and returns extracted fields** — the only place anywhere in this suite that exercises the real `defaultScanDeps`/lazy-`claude.ts`-import wiring rather than fake deps.
- **extraction failure through the real wiring triggers a real refund and reports extraction_failed** — same real-wiring proof, on the failure path; confirms exactly two RevenueCat calls happen (one spend, one refund).
- **GET /v1/scan falls through to the generic 404, not a method-specific error**.
- **an unknown route returns the same generic 404**.
- **malformed JSON body returns 400 bad_request, not a 500**.
- **valid JSON that fails parseScanRequest returns 400 with that specific message, not swallowed** — proves `index.ts` passes `parseScanRequest`'s actual error message through rather than replacing it with something generic.

## Known gaps (deliberately not tested, or not yet)

- **No timeout on the Anthropic/RevenueCat `fetch` calls** — not a test gap so much as a missing feature (both here and Android-client-side); a hung call currently means the Android loading spinner never resolves. Raised, not yet a task.
- **No request-level idempotency across client retries** — each `runScan` call mints its own key; a client retry after a timeout is a second real charge. Documented as current behavior in `scan.test.ts`, not fixed.
- **Workers-runtime-specific behavior** (`@cloudflare/vitest-pool-workers`) — this Worker doesn't currently use any Workers-only APIs, so plain Node test coverage is representative; low-risk gap, unblocked but not written.
