# Archive: Android monetization / backend billing history

Detailed narrative for the RevenueCat + Cloudflare Worker (`scan-proxy`)
billing build-out, moved out of `NEXT_STEPS.md` 2026-08-23 to keep that
file's current-status section cheap to read. Current status/roadmap lives
in `NEXT_STEPS.md` — this file is history, not a place to look for "what's
next."

**Entry-tag convention** (for `Grep`-based lookup instead of reading this
whole file): entries lead with `✅ **Real`, `**Decided`, `**Important
gotcha`, or similar bold tags — grep for those to filter by type.

---

## 💰 Android monetization: billing model decided, backend fully verified

Optional Claude-vision-powered "scan instead of type" feature (the native
app's default manual-entry-only flow stays free and fully offline per
`ANDROID_DESIGN_BRIEF.md`).

**Progress update, 2026-08-17 — account setup underway, `workers/scan-proxy/`
now actually installs and typechecks clean:**

- **Anthropic: done.** Account created, API key generated, stored as a
  persistent User-level `ANTHROPIC_API_KEY` environment variable on this
  machine (not hardcoded anywhere) and verified working with a real API
  call. `src/AccountSetup/AnthropicAccountTest.py` is the verification
  script — that whole directory is gitignored (local credential-testing
  scratch space, not part of the application); read the key via
  `anthropic.Anthropic()`'s automatic env var pickup, never hardcode it.
  Windows gotcha: a newly-set User env var won't propagate to
  already-running processes until Explorer's cached environment
  refreshes — reboot or restart Explorer.exe if a freshly-set var isn't
  picked up.
- **Cloudflare: done.** Account created and linked via `npx wrangler
  login` (browser OAuth) — `wrangler whoami` confirms the CLI is
  authenticated as `gtphdee07@gmail.com`'s account
  (`0031ccba6a8de63fe9dc719b3061170a`), OAuth token cached in
  `%APPDATA%\xdg.config\.wrangler\config\default.toml`. Free Workers
  plan, no domain needed.
- **`cd workers/scan-proxy && npm install`: done.** First-ever run of
  `npm install`/`tsc --noEmit` on this project surfaced a real
  `@cloudflare/workers-types` v4→v5 peer-dependency conflict (fixed by
  bumping the pin) plus ~20 pre-existing typecheck errors, all fixed —
  `typecheck` is clean and all 20 tests still pass unchanged. See git
  history around 2026-08-17 for the specific fixes if ever needed again.
  `package-lock.json` now exists and is committed for the first time.
- **Machine note (this Windows machine specifically, not portable
  info)**: npm's global package cache was relocated from
  `C:\Users\Angela\AppData\Local\npm-cache` to `G:\npm-cache` — the C:
  drive is space-constrained (see the "System Tool Installs" standing
  rule in `Claude.md`), and this cache grows with *every* npm project
  used on this machine, not just this one. Existing 115MB moved, not
  duplicated.
- **RevenueCat: done.** Project created (name `RigCheck`, ID
  `proj07f52826` — written into `wrangler.toml`'s `[vars]` as
  `REVENUECAT_PROJECT_ID`, not a secret). Entitlement `RigCheck Pro`
  created for the lifetime-unlock gate. Virtual currency `SCAN` created
  (matches `wrangler.toml`'s `REVENUECAT_CURRENCY_CODE` and the code
  `src/revenuecat.ts` already sends). Two placeholder products exist
  under Product catalog — `lifetime` (non-consumable, attached to
  `RigCheck Pro`, $99.99 RevenueCat-default placeholder price — not a
  real pricing decision) and `consumable` — both currently configured to
  grant 10 `SCAN` credits per purchase (also placeholder; real pack
  sizing still open). Note: `consumable` ended up with `RigCheck Pro`
  attached too, which it doesn't need (only `lifetime` should gate the
  entitlement) — harmless for now, worth detaching before this goes
  live. **Important gotcha, cost real debugging time:** RevenueCat has
  two separate API key systems — legacy **V1** (app-scoped) and newer
  **V2** (project-scoped). The Worker calls the V2 Virtual Currency
  endpoint (`/v2/projects/{id}/customers/.../virtual_currencies/transactions`
  in `src/revenuecat.ts`), so the secret key **must** come from the V2
  API Keys section of the dashboard, not the V1/legacy one — a V1 key
  fails with a `403 authorization_error` ("legacy API key... use API v2")
  that only shows up once the Worker is actually deployed and called,
  not at key-creation time. Secret key set via `wrangler secret put`
  (see below) and confirmed working (2026-08-17) — real request to the
  deployed Worker gets a real, correctly-authenticated RevenueCat
  response.
- **Both Worker secrets set (2026-08-17).** `ANTHROPIC_API_KEY` and
  `REVENUECAT_SECRET_KEY` were each set via `npx wrangler secret put
  <NAME>` run directly in the user's own terminal (never typed into
  chat) from `workers/scan-proxy/`. First run of `wrangler secret put`
  also had to create the `rigcheck-scan-proxy` Worker itself (didn't
  exist yet — nothing had been deployed), which it did automatically on
  confirmation. Wrangler also offered to install Cloudflare-specific
  Claude Code skills at this point — accepted; low-risk local
  config/instruction files, not a system-wide install, doesn't trip the
  C:-drive standing rule.
- **Worker deployed and smoke-tested (2026-08-17).** Picked a
  `workers.dev` subdomain (`wanderingtrailswaggingtails.workers.dev` —
  a one-time, permanent, account-wide choice required by Cloudflare
  before any dev/deploy that touches real infrastructure) and ran `npx
  wrangler deploy` from `workers/scan-proxy/`. Live at
  `https://rigcheck-scan-proxy.wanderingtrailswaggingtails.workers.dev`.
  Note: `wrangler dev --remote` (the local dev-preview-against-real-
  infra mode) failed with an opaque, undebuggable "internal error" —
  Wrangler's own startup message flags `--remote` as a legacy mode being
  replaced, so a real `wrangler deploy` was used instead for smoke
  testing, which worked cleanly and is the actual production path
  anyway. Sent a real `POST /v1/scan` request and used `wrangler tail`
  to watch live logs, which is how the V1-vs-V2 API key issue above got
  diagnosed — added a `console.error` in `src/scan.ts`'s `spendCredit`
  failure branch to surface RevenueCat's actual error body (kept
  in, not reverted — genuinely useful for future ops debugging via
  `wrangler tail`, doesn't log anything secret). End state confirmed:
  deploy pipeline, secrets, and RevenueCat V2 auth all work — a request
  with a fabricated `app_user_id` correctly gets `404 Customer could not
  be found` from RevenueCat (expected; RevenueCat only creates customer
  records via the SDK or a real purchase, not this direct ledger API),
  which the Worker correctly turns into a `502 billing_error`.
- **Full happy-path test passed (2026-08-17).** No mobile app or store
  sandbox needed to get a test customer — RevenueCat's REST API
  auto-creates a customer the same way the SDK does, so a single `GET
  /v1/subscribers/smoke-test-user` call (using the **public** SDK key,
  not the secret one) created customer `smoke-test-user` with a `201`.
  Granted it the `RigCheck Pro` entitlement + 100 `SCAN` credits directly
  from its RevenueCat dashboard page. Sent a real photo
  (`ExampleDocs/AddieTag.jpg`, base64-encoded) through `POST /v1/scan` —
  got a real `200` with correctly-extracted fields (manufacturer, VIN,
  GVWR, front/rear GAWR, tire specs) from a live Claude Haiku vision
  call, and confirmed in the RevenueCat dashboard that the customer's
  `SCAN` balance dropped from 100 to 99. This is the full production
  path working end-to-end against real infrastructure — the last
  blocker before Android app work itself.

**Decided for good, 2026-08-14: lifetime purchase + consumable credit
packs.** A one-time purchase unlocks the app for life and includes a
pre-set number of Claude-vision scans; once used up, additional scans are
sold as consumable in-app-purchase "packs" (e.g. "20 more scans"). A flat
monthly/annual subscription was considered and explicitly rejected — don't
revisit this without a real change in circumstances. Reasoning:
- **Usage pattern.** RigCheck gets used a handful of times a year per
  owner (before a trip, after buying gear) — a poor fit for a recurring
  charge, a good fit for pay-once-own-it.
- **Cost-risk protection**, the original motivation for moving off
  subscription: a flat subscription exposes you to Anthropic's future
  per-token pricing with no lever besides re-pricing existing subscribers.
  Credits already sold are already priced; a future price change only
  affects margin on packs not yet sold.
- **Already built around it.** `workers/scan-proxy/` charges/refunds a
  RevenueCat *virtual currency* balance, not a boolean entitlement —
  switching to a subscription now would mean discarding that design.

**Pricing and pack sizes — deliberately deferred (2026-08-14), not an
unstarted to-do.** The actual price (e.g. "$X for lifetime + 10 scans, $Y
for 20 more") is being held until real numbers are in hand instead of
guessed at: Google's actual cut at your volume, RevenueCat's fee tier at
your volume, and *measured* Claude API cost (the $0.01–0.03/scan baseline
below is from documented per-token pricing, not observed spend yet).
Pricing before that data would mean setting margin blind. This costs
nothing to defer — it's a leaf decision that doesn't block anything below:
the Worker only deals in credit counts, never dollar amounts; RevenueCat's
virtual currency is just a code, no price attached; Play Console product
IDs can be created and wired into Android code now and re-priced later
without any rework. One independent, non-blocking thing worth starting
early if there's ever idle time: Play Console developer/app registration
can have its own review lead time unrelated to pricing.

The backend build-out below is still in progress — only the billing
*model* is final; pricing is intentionally still open.

**Cost baseline** (documented pricing, not a measured count): a full
3-photo check (truck tag + trailer tag + scale ticket) via Claude vision
costs roughly **$0.01 on Haiku 4.5** or **$0.03 on Claude Sonnet 5** in raw
API spend — each image is a small extraction task (~1,600 image tokens at
standard resolution + a short prompt + compact JSON output), not a
high-res/reasoning-heavy call. Haiku 4.5 is very likely sufficient for
this — structured field extraction from a printed label is squarely its
use case. This is compute cost only; doesn't include Play Store fees or
your own margin.

**The part that matters more than the billing rail:** `ANTHROPIC_API_KEY`
can never ship inside the Android app (trivially extracted from the APK).
Enabling Claude-vision scanning requires a backend that holds the key,
checks entitlement, and proxies the request — reopening the "no backend"
decision in `ANDROID_DESIGN_BRIEF.md`.

**Capability split for building this** (roughly): I can write essentially
all of the code — the Android purchase-flow UI, the credit-balance display,
the backend proxy function, and the RevenueCat/API wiring. What's yours to
do: create and own the RevenueCat, Google Play Console, and (if used)
Stripe accounts; set actual prices; accept Google's Play Console developer
agreement and any tax/payout info; and any legal/compliance judgment calls
(refund policy wording, terms of service) — those need to be your accounts
and your decisions, not something I can do on your behalf.

**Backend architecture — answered 2026-08-14:** you don't need to run a
traditional server or build your own credit-ledger database.
[RevenueCat's Virtual Currency feature](https://www.revenuecat.com/feature/virtual-currency)
now handles purchase verification for both the lifetime-unlock product and
the consumable scan-packs, *and* tracks the credit balance itself (not just
boolean subscription entitlements) — it increments on purchase, you read/
decrement via their API, and it reconciles automatically on refunds/
chargebacks. That covers the ledger/state-keeping question.

What's still unavoidable: a small server-side function that holds
`ANTHROPIC_API_KEY` and, per scan request, checks the RevenueCat balance →
calls Claude vision → decrements the balance → returns the result. It's
stateless (no database of its own needed — RevenueCat holds the balance),
so it's a good fit for a serverless function rather than a maintained
server: **Firebase Cloud Functions, Supabase Edge Functions, or Cloudflare
Workers** are all reasonable, pay-per-use, no-uptime-babysitting options.
**GoDaddy specifically is not a good fit** — it's domain registration and
shared cPanel/WordPress hosting, not built for reliably running this kind
of function on a payment-critical path.

So the recommended shape: **RevenueCat (purchases + credit ledger) + one
small serverless function (the Claude-key proxy)** — no self-managed
server at all.

**Backend proxy — source written 2026-08-14, not deployed:**
`workers/scan-proxy/` is a Cloudflare Worker implementing the architecture
above — see its `README.md` for the full design. Ports the exact system
prompts/JSON schemas from the desktop CLI's Claude-vision readers
(`src/hdttools/truck_tag.py` / `trailer_tag.py` / `scale_ticket.py` /
`vision_client.py`) into TypeScript (`src/docTypes.ts`), so both extraction
paths agree on field names. `POST /v1/scan` charges one RevenueCat credit
*before* calling Claude (RevenueCat's `422` on insufficient balance doubles
as the entitlement check, so a zero-credit user never triggers a paid
Claude call), and refunds the credit if extraction then fails. Uses Haiku
4.5 per the cost baseline above.

**20 unit tests written and passing, zero installs required.** The
charge/extract/refund logic (`src/scan.ts`) takes its dependencies
injected, and only loads `claude.ts` (and the Anthropic SDK) lazily on
first real use — so `npm test` (`node --test`, built into Node 26, already
on this machine) covers the money-critical control flow, RevenueCat
request-shaping, and doc-type schema integrity without installing
anything. See `workers/scan-proxy/README.md`'s Testing section for what
this does and doesn't cover — full Workers-runtime integration tests
(`@cloudflare/vitest-pool-workers`) are still a separate, un-started gap;
the real `npm install` itself is now done (2026-08-17, see progress update
above) and `tsc --noEmit` is clean.

**Known v1 gap, accepted on purpose:** the Worker trusts whatever
`app_user_id` the client sends with no signed-token verification — someone
who obtained another user's anonymous RevenueCat UUID could spend their
credits. There's no real discovery path for another user's UUID short of
device compromise, so this was accepted as fine for a first release; adding
Firebase Authentication is the documented upgrade path if it ever matters.

**Still needed before this can go live:**

- ✅ Anthropic, Cloudflare, and RevenueCat accounts (created in that
  order, per 2026-08-14 guidance) — all done 2026-08-17, see the
  progress update above for detail and the gotchas hit along the way.
- ✅ `npm install`, `wrangler login`, both Worker secrets
  (`ANTHROPIC_API_KEY`, `REVENUECAT_SECRET_KEY`), and a first `wrangler
  deploy` + billing-path smoke test — all done 2026-08-17, see progress
  update above. Live at
  `https://rigcheck-scan-proxy.wanderingtrailswaggingtails.workers.dev`.
- **Aside, not blocking, worth starting whenever there's spare time:**
  the Google Play Console developer account ($25 one-time + identity
  verification that can take days) — independent of the above and has
  by far the longest lead time of anything on this list.
- The Android app itself didn't exist yet at the time and had no code
  calling this endpoint — see `ARCHIVE_ANDROID.md` for Phases 0-4, all
  since done.

**Next step (as of 2026-08-17):** the backend is fully built, deployed,
and verified against real infrastructure (accounts, secrets, deploy, and
a full happy-path charge + extraction, all confirmed) — nothing left to
do here until the Android app exists to actually call it. That app now
exists — see `ARCHIVE_ANDROID.md`. The billing-model decision itself is
done — see above.

---

## ✅ Two real production gaps closed: outbound timeouts + request-level idempotency (roadmap item #5, 2026-08-23)

**The gaps, found by reading the code, not guessed.** `src/claude.ts`'s
Anthropic SDK call and `src/revenuecat.ts`'s raw `fetch()` had no explicit
timeout — a hung upstream would tie up the Worker until Cloudflare's own
platform execution limit killed it uncontrolled, not a clean mapped error
(Gap A). Separately, `scan.ts`'s idempotency machinery already existed —
`revenuecat.ts` already sent an `Idempotency-Key` header, and RevenueCat's
own docs confirm that header guarantees "executed at most one time" — but
the key was minted fresh via `crypto.randomUUID()` on *every* Worker
invocation, so a client retry after a lost/timed-out response generated a
new key and charged the credit balance again (Gap B).

**Gap A fix.** `claude.ts` exports `ANTHROPIC_TIMEOUT_MS = 20_000`, passed
to the SDK client's own `timeout` option — deliberately shorter than
Android's `ScanApiClient` 60s `readTimeout`, or a Worker-side timeout would
never fire before the app's own client had already given up.
`revenuecat.ts` exports `REVENUECAT_TIMEOUT_MS = 10_000`, passed as
`signal: AbortSignal.timeout(...)` to its raw `fetch()` — tighter, since
it's a simple ledger write, not a vision model call. Confirmed by reading
`@anthropic-ai/sdk`'s `client.js` that the SDK already builds a per-request
`AbortController` and wires its `signal` into `fetch` — the timeout option
was genuinely missing, not silently a no-op.

The less obvious half of Gap A: `claude.ts`'s own thrown errors were
already caught generically by `scan.ts`'s existing `extractFields`
try/catch (mapped to `extraction_failed` + a refund attempt) — no code
change needed there. But `revenuecat.ts`'s `spendCredit` call had **no**
catch around it at all; `scan.test.ts` had an existing test explicitly
documenting this as a known, unfixed gap ("propagates out of runScan
rather than being caught"). Closing Gap A properly meant also adding that
catch — otherwise a real timeout would just be a *faster* uncaught
crash, not a clean `billing_error`. That test was rewritten (not just
patched) to assert the new behavior; `revenuecat.test.ts`'s matching
"known gap" comment was corrected too, since it was about to go stale.

**Gap B fix.** `request.ts`'s `ScanRequest` gained an optional
`client_request_id?: string`, client-generated and stable across retries
of the same logical attempt — absent falls back to today's random-UUID
behavior, so any already-shipped app build stays compatible.
`scan.ts`'s `runScan` uses `request.client_request_id ?? crypto.randomUUID()`
as the idempotency key. On Android, `RigCheckViewModel.performScan` and
`performStandaloneScan` each generate one `UUID.randomUUID()` per
user-initiated tap (no existing client-side retry loop, so "one id per
logical attempt" is just "one id per call") and thread it through
`ScanApiClient.scan(...)`'s new optional `clientRequestId` parameter.

**Accepted tradeoff, decided 2026-08-23 (confirmed by the user before
implementation):** this protects the RevenueCat *credit balance* from
double-charging, but does **not** stop the Worker calling Claude twice on
a genuine retry — `extractFields` still runs unconditionally every
request. Fully closing that would need caching the extraction result
somewhere (Workers KV), which breaks the Worker's deliberately stateless
design (see its `README.md`'s "No database" note). Decided to accept the
small residual Claude-cost duplication (bounded, rare, ~$0.01, only on a
lost/retried response) and keep the Worker stateless. Also confirmed:
20s for `ANTHROPIC_TIMEOUT_MS` specifically (the 10s RevenueCat figure
was the plan's own proposal, not separately re-confirmed, but is a low-
stakes value with headroom either way).

**✅ Real bug caught by the hands-on verification step, not by review.**
The plan called for sending two identical real scans with the same
`client_request_id` against real RevenueCat and confirming the balance
moves exactly once. First run (before remembering to deploy): balance
went from 53 to 52 after **two** scans — i.e. it moved twice, not once.
The local source change was correct and all 57 unit tests (fakes only)
passed, but the **deployed** Cloudflare Worker the Android app actually
talks to was still running the old code — `npm run deploy` had not been
run. This is exactly the kind of gap unit tests with injected fakes can
never catch: they prove the *logic* is right, not that the *live system*
has it. After confirming with the user and running `npm run deploy`
(version `2743feea-fe1c-40d0-b9a3-4471a6b8839d`), the identical test
passed for real: two scans sharing one `client_request_id` moved
`weekly-test-user`'s balance by exactly 1.

**New tests.** `scan.test.ts`: a `spendCredit` rejection (standing in for
what a real timeout eventually produces) maps to a clean `billing_error`,
not a hang; an `extractFields` timeout-shaped rejection still refunds and
maps to `extraction_failed` like any other extraction failure (pinning
down that the existing generic catch already covers this case); two
`runScan` calls sharing one `client_request_id` reuse the same
idempotency key; a request without it still gets a fresh random key each
call, unchanged from today. `request.test.ts`: parses/passes through
`client_request_id`; null treated as absent (matching `media_type`'s
existing convention); blank or wrong-typed values rejected the same way
other known fields are. `claude.test.ts`: `ANTHROPIC_TIMEOUT_MS` is
20,000 and is asserted to be less than Android's 60,000ms read timeout —
constructing a real `Anthropic` client and reading back its own `.timeout`
property, since the SDK's internal timer isn't otherwise observable
without actually waiting for one to fire. `revenuecat.test.ts`: `fetch`
is called with a real `AbortSignal` (proving the wiring exists, not that
it fires). New Android instrumented test,
`PaywallScreenWeeklyTest.realDuplicateScanWithSameClientRequestIdSpendsOnce`
— the hands-on real-network proof described above; costs one extra real
~$0.01 Claude call each time this specific test runs, on top of the
existing suite's cost.

**Verification, in full.** `npm test` (scan-proxy): 57/57 (was 46).
`npm run test:weekly`: 4/4 real, against the deployed Worker. `npm run
typecheck`: clean. Android `./gradlew test` (Unit): 31/31 unchanged.
Android `./gradlew connectedDebugAndroidTest` (Daily): 39/39 — one
`RigCheckNavHostTest` failure (`ComposeTimeoutException`) on the full run
reproduced clean on an isolated re-run after waking the emulator screen,
matching the already-documented screen-sleep flakiness gotcha
(`ARCHIVE_TESTING.md`), not a real regression; unrelated to this change's
files either way. `.\test-weekly.ps1` (all 4 cases): one
`realPurchaseIncrementsBalance` failure (`PurchasesException: Error
performing request` from RevenueCat's own virtual-currency endpoint, not
the Worker) on the full run, also reproduced clean in isolation — a
transient RevenueCat network blip, unrelated to `client_request_id` or
timeout wiring. The Release tier (`npm run test:release`) was not
re-run this pass — no `REVENUECAT_SECRET_KEY` in this shell, and per its
own design it's gated to major Play Store release timing, not every
change; nothing in this change alters `spendCredit`/`refundCredit`/
`extractFields`'s call signatures in a way the Release tier would newly
exercise differently.

**Follow-up, same day**: the stale-deploy near-miss above (the first
real hands-on run genuinely spending twice because the fix wasn't
deployed yet) was pointed out by the user as a real gap in the test
script itself, not just a one-off mistake to remember next time - "why
doesn't the test verify the remote is current?" `workers/scan-proxy/package.json`
now has a `pretest:weekly` hook (`npm run typecheck && npm run deploy`,
using npm's own pre-script convention - it runs automatically before
`test:weekly`, no separate invocation needed) so `npm run test:weekly`
can never again silently test a stale deployed Worker; verified by
running it for real immediately after adding it (deploy + 4/4 real
tests, in one command). `android/test-weekly.ps1` got the equivalent
explicit typecheck+deploy step via `npm run ... --prefix ..\workers\scan-proxy`,
before it builds/installs anything. Full detail, including a second,
unrelated real infrastructure issue (an emulator launcher ANR) found
while verifying the *other* fix from this same conversation (the
screen-wake Gradle task), in `ARCHIVE_TESTING.md`.

## 🐛 Real bug: the deployed Worker used the wrong Claude model for label extraction — found and fixed 2026-08-25

Found by item #13's new Android pass-pool test
(`PaywallScreenWeeklyTest.kt::scanPassPoolRandomPickMatchesGoldenFields`,
`NEXT_STEPS.md` item #15), while building it — not a pre-existing test,
a brand-new one that caught something real on its very first real run.

**The setup**: while investigating item #13's Android fail-pool
candidate (a real F-150 photo item #11 said Claude fails on because the
top of the tag is outside the frame), a direct call to the deployed
Worker returned confident, specific — but *wrong* — GVWR/GAWR numbers
instead of the expected `null`s. Suspecting the same photo might just be
genuinely ambiguous, `AddieTag.jpg` (the easiest, clearest, previously
"known good" fixture in the entire repo — the baseline every other
finding this session has trusted) was checked too, for the first time
ever against the *actual deployed Worker* rather than Python's direct
`vision_client.py` call:

```
Real response (via POST /v1/scan, doc_type truck_tag):
  gvwr_lb: 6000       (real value: 14000)
  front_gawr_lb: 2700 (real value: 6000)   -- a second call: 3000
  rear_gawr_lb: 3300  (real value: 9900)   -- a second call: 3000
  tire size, VIN: different (and wrong) on each call
```

Two calls, two different sets of wrong answers, on the single clearest
photo available — not a hard-photo problem.

**Ruled out first**: a stale deployed Worker (this repo's own documented
precedent from 2026-08-23, "Follow-up, same day" above — a redeploy step
was missing from a test script once before). Redeployed for real
(`npm run typecheck && npm run deploy`), re-tested — same wrong,
still-varying answers. Not staleness.

**Real root cause, confirmed empirically**: `workers/scan-proxy/src/claude.ts`
pinned `MODEL = "claude-haiku-4-5-20251001"` — chosen for cost
(~$0.01/scan vs ~$0.03 on Sonnet 5, per its own now-outdated comment).
Python's `vision_client.py` (`DEFAULT_MODEL = "claude-sonnet-5"`) —
the actual basis for item #11's "Claude vision is robust, 9/10 photos
succeed" finding — had *never* used Haiku. Nobody had ever validated
the cheaper, actually-deployed model against this task. A direct call to
`claude-sonnet-5` with the byte-identical prompt/schema/image:

```json
{"gvwr_lb": 14000, "front_gawr_lb": 6000, "rear_gawr_lb": 9900, ...}
```

Exactly right, matching the physical tag. Confirmed root cause.

**The fix**: `claude.ts`'s `MODEL` constant switched to `claude-sonnet-5`
(comment updated with this finding); the 3 tests in `claude.test.ts`/
`index.test.ts` that hardcoded the old model string as an expected value
updated to match (57/57 scan-proxy tests pass). Redeployed; re-verified
for real against both fixtures — `AddieTag.jpg` now returns the exact
correct values, and the F-150 framing-gap photo now correctly returns
`null` for the fields genuinely outside the frame (matching the system
prompt's "leave a field null if it is not present" instruction, and
matching item #11's original — Sonnet-5-based — expectation exactly).

**No production impact**: confirmed directly with the project owner that
the app isn't deployed and has no real users yet, still in testing/
development — this was caught before it could ever reach one. Real,
concrete vindication of the "duplicate, not inherit" decision for
Android's testing (item #13): the bug lived specifically in the
Worker's real, deployed configuration, which only a test that actually
calls the real deployed Worker (not Python's direct-Claude path, and not
a mocked scan-proxy unit test) could ever have caught.
