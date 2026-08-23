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
| **Weekly** | ✅ built (4 tests) | ongoing/ad hoc — the free case is cheap enough to run anytime; the other three each spend a real credit and (for two of them) a real Claude call | real, bounded, dedicated test customer | `npm run test:weekly` |
| **Release** | 🟡 built, needs your local secrets to run | before pushing a major update to the Play Store, not a fixed cadence | real, against RevenueCat/Anthropic directly | `.\test-release.ps1` (`-SkipKeys` to allow skipping) |

Sanity is a small subset of daily's tests, tagged `[sanity]` in their
names and selected via `node --test`'s `--test-name-pattern`, not a
separate set of test files. Weekly and release both need real dedicated
RevenueCat test customers (never `smoke-test-user`, which stays reserved
for manual Android field testing) — `weekly-test-user` and
`weekly-test-user-no-credits` were created 2026-08-21 for exactly this
(see `NEXT_STEPS.md`'s scan-proxy section). Weekly tests live in
`src/weekly/*.test.ts`, deliberately excluded from `src/*.test.ts`'s glob
(so `npm test`/`npm run test:sanity` never pick them up) and run only via
`npm run test:weekly`.

**Release tier, built 2026-08-22**: real API calls at the service-provider
boundaries this Worker depends on — RevenueCat and Anthropic directly
(`revenuecat.ts`/`claude.ts`'s own functions called in-process), not
mocks and not routed through the deployed Worker as an intermediary —
including their error conditions, to catch a breaking change at either
boundary before it reaches production. Gated on a real event (deciding
to push a major update to the Play Store), not a calendar or a `wrangler
deploy` — with no CI in this repo, "after every deploy" never had a real
trigger anyway, whereas "before a major release" is a decision a person
actually makes. Distinct from the Weekly tier above (Weekly is cheap
enough to run anytime with no real cost; Release is the deliberate,
thorough gate) and distinct from Android's own Weekly-equivalent tier
despite sharing the same gating trigger — see `android/TESTING.md`'s
tier notes for that relationship, and the root `TESTING.md`'s category 4
for the recommended sequencing (this tier first — cheaper and far easier
to debug — before the Android layer).

**Needs `ANTHROPIC_API_KEY` and `REVENUECAT_SECRET_KEY` exported in your
own shell before running** — the same two values already set as this
Worker's deployed secrets via `wrangler secret put`, read from
`process.env` here instead of ever being typed into chat.

**Default behavior is strict, not a graceful skip (revised 2026-08-22,
per explicit direction)**: run via `.\test-release.ps1` (or `npm run
test:release`/`SKIP_KEYS=1 npm run test:release` directly — the
enforcement lives in the test file itself, not the wrapper, so it holds
regardless of entry point). With no `-SkipKeys`, a missing key stops the
*entire file* before any test runs — reported as one failed test naming
which key is missing, not a silent per-test skip, since a silent skip
here would be indistinguishable from "this boundary was never actually
checked this release." Pass `-SkipKeys` (`.\test-release.ps1 -SkipKeys`,
or `SKIP_KEYS=1 npm run test:release`) to explicitly allow a missing key
to fall back to a per-boundary skip instead — RevenueCat and Anthropic
skip independently, so you can verify one without having a key for the
other.

**A key that *is* present but wrong is never just a generic assertion
mismatch, either** — `assertNotAuthFailure`/`rejectingAuthFailureAsBadKey`
in the test file turn a real 401/403 from either service into an
explicit `"<ENV_VAR_NAME> appears invalid"` failure, with the real error
body attached, naming exactly which key. Verified 2026-08-22 with a
deliberately garbage `REVENUECAT_SECRET_KEY`: both RevenueCat cases
failed with `REVENUECAT_SECRET_KEY appears invalid - RevenueCat returned
401: {"message":"Invalid API key."...}`, not a bare "expected 200, got
401."

**Real cost note**: the Anthropic happy-path case makes one real, billed
Claude call (~$0.01, same baseline as a real user scan) — infrequent by
design, matching the tier's gating trigger, but not free. The
RevenueCat-side cases are free (currency-ledger adjustments only) and
net zero balance change (`weekly-test-user`'s spend is immediately
refunded back). **Found while first verifying this tier**:
`ANTHROPIC_API_KEY` was already set ambiently in this dev machine's
shell environment (not deliberately) — worth checking for ambient
secrets before running anything that could hit a paid API unexpectedly.

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

### `weekly/scan.weekly.test.ts` — real network, against the live deployed Worker (`npm run test:weekly` only)

- **a customer with no SCAN credits gets 402 insufficient_credits, never reaches Claude** — real POST to the deployed Worker using `weekly-test-user-no-credits` (0 balance, no entitlement granted). Costs nothing to run repeatedly: `spendCredit`'s real 422 short-circuits the request before any real Claude call happens, the same control-flow ordering `scan.test.ts`'s equivalent mocked case already proves — this is that same claim, proven for real.
- **a real scan of a real truck tag succeeds and returns real extracted fields** (2026-08-22) — `weekly-test-user`, `ExampleDocs/AddieTag.jpg`. The real-scan-and-charge case: proves the full Worker pipeline (spend → real Claude call → return fields) works end-to-end for a genuine success, not just the failure paths the other three cases in this file cover. **Real cost: one SCAN credit and one billed Claude call (~$0.01) every run** — not free to re-run repeatedly, unlike the case above.
- **a real scan of a valid but irrelevant image still succeeds and is charged, not refunded** (2026-08-22) — the WTWT logo (`streamlit_app/assets/wtwt_logo.png`), a real, valid, real-world image that just isn't a truck tag. Exists because `claude.ts` forces Claude's `tool_choice` to the extraction tool — it can't refuse just because the photo is wrong, so it returns a (mostly-empty) result instead of erroring. Proves `scan.ts`'s refund path is genuinely conditioned on `extractFields` throwing, not on "was the result useful" — a real user who photographs the wrong thing still gets charged, matching current intended behavior. Same real cost as the case above.
- **a corrupted/undecodable image triggers the real refund path** (2026-08-22) — the same logo file, deliberately truncated to its first 200 bytes so Anthropic's API genuinely rejects it before any model call happens (free — a rejected request is never billed). The response itself is the proof the refund succeeded: `code: "extraction_failed"` only appears when `refundCredit`'s own real call also succeeded; `"extraction_failed_no_refund"` would mean the refund itself failed, a different, worse real outcome this test would also have caught.

### `release/scan.release.test.ts` — real API calls directly at the RevenueCat/Anthropic boundaries (`.\test-release.ps1` / `npm run test:release`, needs your local secrets)

- **Module-level hard stop, not a per-test skip, when a key is missing and `SKIP_KEYS` isn't set** — the whole file throws before any test runs, reported as one failed test naming which env var is missing. `SKIP_KEYS=1` (set by `-SkipKeys`) is required to fall back to the per-boundary skips below.
- **spendCredit against a real funded customer succeeds, and refundCredit reverses it** — `weekly-test-user`, net zero balance change (spend then immediately refund with the paired idempotency key). Proves the real `Authorization`/`Idempotency-Key`/adjustment-body request shape `revenuecat.ts` sends is still accepted for both a debit and a credit.
- **spendCredit against a real customer with zero balance gets the real 422 `scan.ts` depends on** — `weekly-test-user-no-credits`, calling `revenuecat.ts` directly rather than through the Worker (the Weekly tier's equivalent case goes through the deployed Worker's full request/response envelope; this one isolates the RevenueCat boundary itself).
- **Both of the above fail explicitly as a bad-key problem, not a bare status mismatch, if `REVENUECAT_SECRET_KEY` is present but wrong** — `assertNotAuthFailure` turns a real 401/403 into `"REVENUECAT_SECRET_KEY appears invalid - RevenueCat returned <status>: <real error body>"`. Verified 2026-08-22 with a deliberately garbage key.
- **extractFields against the real Anthropic API extracts real fields from a real truck tag photo** — `ExampleDocs/AddieTag.jpg`, the same file the original 2026-08-17 scan-proxy smoke test used. Proves the real request shape (model name, forced `tool_choice`, image content block) is still accepted and still returns a matching `tool_use` block with real field names — not any particular extracted value, since real vision accuracy isn't this test's concern (that's `tests/test_scale_ticket_real_photo.py`'s job on the Python/Tesseract side; this is the same idea applied directly to Claude). The one real, billed call in this file — fails explicitly as `"ANTHROPIC_API_KEY appears invalid"` (via `rejectingAuthFailureAsBadKey`), not a bare SDK error, if the real key is present but wrong.
- **extractFields against the real Anthropic API rejects an invalid key with a real auth error** — free (fails before any billed inference), proves the auth-failure shape `extractFields`'s error handling assumes is still what a real 401 actually looks like. (This one's *point* is a bad key being correctly rejected, so it's not wrapped in `rejectingAuthFailureAsBadKey` — that wrapper is for `ANTHROPIC_API_KEY` unexpectedly being the thing that's wrong, not this test's own deliberately-bad key.)

## Known gaps (deliberately not tested, or not yet)

- **Investigated 2026-08-21, confirmed not a gap**: whether a customer's
  `RigCheck Pro` *entitlement* state (vs. its `SCAN` credit balance)
  needs its own dedicated test customer/test case. It doesn't, currently
  — neither `scan.ts` nor the Android app ever reads entitlement state at
  all; `spendCredit`'s 422 on an empty balance is the only gate that
  exists anywhere (see the comment in `scan.ts`). A no-entitlement or
  expired-entitlement test customer would exercise no code path that
  differs from a normal one. Revisit if entitlement-based gating is ever
  actually built.

- **No timeout on the Anthropic/RevenueCat `fetch` calls** — not a test gap so much as a missing feature (both here and Android-client-side); a hung call currently means the Android loading spinner never resolves. Raised, not yet a task.
- **No request-level idempotency across client retries** — each `runScan` call mints its own key; a client retry after a timeout is a second real charge. Documented as current behavior in `scan.test.ts`, not fixed.
- **Workers-runtime-specific behavior** (`@cloudflare/vitest-pool-workers`) — this Worker doesn't currently use any Workers-only APIs, so plain Node test coverage is representative; low-risk gap, unblocked but not written.
