# RigCheck — where things stand

Working notes for picking this back up on another machine. Written 2026-08-13.

## 💰 Android monetization: billing model decided, build in progress

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
  scratch space, not part of the application), and the pattern going
  forward is: read the key via `anthropic.Anthropic()`'s automatic env
  var pickup, never hardcode it, even in a gitignored file. One Windows
  gotcha hit and resolved: a newly-set User environment variable doesn't
  propagate to already-running processes (or even freshly-opened
  terminals, in this case) until Explorer's cached environment refreshes
  — a reboot fixed it; restarting Explorer.exe is the lighter-weight
  alternative if this comes up again for the next two accounts.
- **Cloudflare: done.** Account created and linked via `npx wrangler
  login` (browser OAuth) — `wrangler whoami` confirms the CLI is
  authenticated as `gtphdee07@gmail.com`'s account
  (`0031ccba6a8de63fe9dc719b3061170a`), OAuth token cached in
  `%APPDATA%\xdg.config\.wrangler\config\default.toml`. Free Workers
  plan, no domain needed.
- **`cd workers/scan-proxy && npm install`: done.** This was the first
  time it had ever been run, and it wasn't clean — surfaced a real
  version conflict (`package.json` pinned `@cloudflare/workers-types` to
  `^4.20260101.0`, but the `wrangler` release that resolved now peer-
  depends on `^5.x` — ordinary drift from the gap between when the code
  was written and when it was first installed, not anyone's error).
  Fixed by bumping the pin to `^5.20260811.1`. That alone was clean, but
  running `tsc --noEmit` for the first time ever (same reason — could
  never run before install worked) surfaced ~20 pre-existing type errors
  unrelated to the bump: `@types/node` was missing from `package.json`
  entirely (broke every `node:test`/`node:assert` import), a
  value-used-as-type bug in `scan.ts` (`typeof` was needed), an
  undertyped `schema` field in `docTypes.ts` (now tied directly to the
  Anthropic SDK's own `Tool.InputSchema` type instead of a loose
  `Record<string, unknown>`), and 4 spots in `scan.test.ts` needing a
  type assertion after `@cloudflare/workers-types` v5 deliberately
  tightened `Response.json()` from `any` to `unknown`. All fixed;
  `typecheck` is fully clean and all 20 tests still pass unchanged
  (confirms none of this altered runtime behavior). `package-lock.json`
  now exists and is committed for the first time — 97 packages, ~212MB
  installed (dominated by the `workerd` and `esbuild` native binaries,
  both approved via `npm approve-scripts` since npm blocks unknown
  postinstall scripts by default).
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
  which the Worker correctly turns into a `502 billing_error`. **Not yet
  tested: an actual successful charge or a real Claude-vision call** —
  needs a real RevenueCat test customer with `SCAN` credits, which
  wasn't set up tonight. Explicit next step, by user request.

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
(`@cloudflare/vitest-pool-workers`) are still a separate, un-started gap
(see "Tests still outstanding" below); the real `npm install` itself is
now done (2026-08-17, see progress update above) and `tsc --noEmit` is
clean.

**Known v1 gap, accepted on purpose:** the Worker trusts whatever
`app_user_id` the client sends with no signed-token verification — someone
who obtained another user's anonymous RevenueCat UUID could spend their
credits. There's no real discovery path for another user's UUID short of
device compromise, so this was accepted as fine for a first release; adding
Firebase Authentication is the documented upgrade path if it ever matters.

**Still needed before this can go live** (none of this can be done from
here — needs your own accounts/decisions):

- **Create the three accounts, in this order (guidance from 2026-08-14) —
  Anthropic → Cloudflare → RevenueCat.** Anthropic first: simplest, and
  gives real per-scan cost data that feeds the pricing decision above.
  Cloudflare second: simple, unlocks actually deploying/testing the
  Worker. RevenueCat last: has the most internal setup (project, currency,
  secret key) and is most useful once the other two already work.
  - **Anthropic — ✅ done (2026-08-17).** Account created, key generated
    and verified working, stored as a local `ANTHROPIC_API_KEY`
    environment variable for testing. Still needs a *separate* step
    later: paste the same key into `wrangler secret put
    ANTHROPIC_API_KEY` when actually deploying the Worker — a local env
    var and a Wrangler secret are two different places, both needed,
    neither done automatically from the other. Never hand the raw key to
    Claude in chat.
  - **Cloudflare — ✅ done (2026-08-17).** Account created
    (dash.cloudflare.com, free Workers plan, no domain name needed —
    Workers get a free `*.workers.dev` subdomain) and linked via `npx
    wrangler login` (browser OAuth) from `workers/scan-proxy/`.
    `wrangler whoami` confirms the login.
  - **RevenueCat — ✅ done (2026-08-17).** Project `RigCheck` created
    (ID `proj07f52826`, now in `wrangler.toml`'s `[vars]`). Entitlement
    `RigCheck Pro`, virtual currency `SCAN`, and two placeholder products
    (`lifetime`, `consumable`, both granting 10 `SCAN` per purchase) all
    created — see the progress update above for the placeholder-pricing
    caveats and the `consumable`/entitlement cleanup note. Secret API
    Key created and set directly via `wrangler secret put
    REVENUECAT_SECRET_KEY`. The Google Play Console side is still **not**
    connected — not needed yet, since the Worker only talks to
    RevenueCat's virtual-currency API directly, not the Play Billing
    verification path; that connection matters once real purchases need
    to flow in automatically.
  - **Aside, not blocking, worth starting whenever there's spare time:**
    the eventual Google Play Console developer account ($25 one-time +
    identity verification that can take days) is independent of the
    three above and has by far the longest lead time of anything on this
    list — worth kicking off early so the wait isn't on the critical path
    later.
- ✅ `cd workers/scan-proxy && npm install` — done 2026-08-17 (see
  progress update above for what that actually took — a version bump
  plus several pre-existing typecheck fixes, not just a plain install).
- ✅ `wrangler login` — done 2026-08-17.
- ✅ Both Worker secrets (`ANTHROPIC_API_KEY`, `REVENUECAT_SECRET_KEY`)
  set via `wrangler secret put` — done 2026-08-17, never committed.
- ✅ `wrangler deploy` + billing-path smoke test — done 2026-08-17 (see
  progress update above). Live at
  `https://rigcheck-scan-proxy.wanderingtrailswaggingtails.workers.dev`.
- The Android app itself doesn't exist yet and has no code calling this
  endpoint — Play Billing product setup (lifetime unlock SKU + consumable
  scan-pack SKUs) still needs to happen in Play Console.

**Next step:** all three cloud accounts, both Worker secrets, and a
first deploy are done as of 2026-08-17, with the billing-path (charge
attempt → RevenueCat auth → structured error) confirmed working
end-to-end. What's left for a *full* happy-path smoke test: in the
RevenueCat dashboard, create a real test customer and grant it `SCAN`
virtual-currency balance, then re-send `POST /v1/scan` against the live
Worker — this should produce a real `200`, a real RevenueCat credit
deduction, and a real (small-cost) Claude Haiku vision call. Explicitly
queued as tomorrow's starting point, by user request. After that:
(separately, no fixed timeline) the Android Studio project itself,
which doesn't exist yet. The billing-model decision itself is done —
see above.

## 📐 Idea, not started: tiered test strategy (sanity → regression → full)

Raised 2026-08-15, deliberately parked — **not being worked on now**, pick
up whenever there's time (e.g. while waiting on account setup/approval
lead times elsewhere). At 50+ pytest tests and growing (plus 20 more in
`workers/scan-proxy/`, a third runner), it's worth structuring testing
the way hardware/digital design verification does, rather than just
"run everything, every time":

- **Sanity** — a small, fast set run on every change to catch major
  breakage.
- **Module regression** — a fuller suite for the specific module touched,
  run when a change lands there.
- **Integration sanity** — a fast cross-module check.
- **Full/"weekend" regression** — every corner case, every module,
  including integrations — run periodically rather than on every change.

The idea: a change to module A runs A's sanity, then integration sanity,
then a regression depth appropriate to the change's size — not
necessarily the full suite every time. Periodic (e.g. weekly) runs cover
sanity everywhere plus full regression per module and top-level.

**Open questions to resolve before this becomes an actionable plan**
(raised when this was first discussed, not yet answered):

1. **What "module" means here.** Hardware verification maps cleanly onto
   design blocks; this codebase's boundaries are fuzzier — candidates:
   OCR parsing (3 readers), breakdown/verdict math, the API layer, web
   frontend, Streamlit frontend, `workers/scan-proxy/`, eventually
   Android. Confirm the right granularity.
2. **What concretely distinguishes the tiers.** Today's full 54-test
   pytest suite already runs in ~2 seconds (mocked-everything) — by
   hardware-verification standards that's arguably already "sanity."
   Likely mapping: sanity = today's suite; regression = broader
   parametrized cases (more synthetic label variants); full = the real
   `ExampleDocs/` photo runs (slower — real Tesseract OCR). Confirm.
3. **Whether "full" ever calls the real Claude API.** The vision-based
   readers (and eventually Android's scan feature) could be tested
   end-to-end against the live Anthropic API — but that costs real money
   per run and adds non-determinism. Leaning toward: full regression
   stays confined to the Tesseract path against static fixtures, vision-
   API path always mocked — needs an explicit decision, not an default.
4. **Automation vs. checklist.** No CI exists anywhere in this repo (no
   GitHub Actions, nothing). Is the near-term goal a documented checklist
   a human runs periodically, or eventual CI (on push + a scheduled
   "weekend" job)? Doesn't block starting, but the plan should say which
   one it's aiming at.
5. **One scheme across four different test runners, or four idiomatic
   ones.** pytest (backend/OCR/breakdown), `node --test` (scan-proxy
   Worker), nothing yet for web (no test framework installed there at
   all — would need Vitest), nothing yet for Streamlit beyond ad-hoc
   `AppTest` scripts run by hand and never committed as real tests.
6. **The concrete, immediate gap regardless of how the above resolves**:
   `ExampleDocs/` real-photo verification has only ever happened via
   manual ad-hoc runs when checking a specific fix — never a committed,
   repeatable test. Probably the single best starting point whenever
   this gets picked up, independent of how the broader tiering scheme
   shakes out.

## 🧪 Tests still outstanding

Living checklist — remove an entry (or fold it into a "✅ Done" note,
matching this file's convention) the moment its test actually gets
written. Add new entries here as soon as a gap is spotted, not just
mentioned in conversation, so it survives a machine switch. See
`Claude.md`'s "NEXT_STEPS.md Maintenance" section for the standing rule
behind this.

**`workers/scan-proxy/` (Cloudflare Worker):**
- **Workers-runtime integration tests** (`@cloudflare/vitest-pool-workers`)
  — the 20 tests in `src/*.test.ts` run on plain Node and cover the
  request validation, RevenueCat request-shaping, doc-type schema
  integrity, and the charge/extract/refund control flow, but nothing
  Workers-runtime-specific (this Worker doesn't currently use any
  Workers-only APIs, so the gap is low-risk for now).
  **Unblocked 2026-08-17** — `npm install` is done and `tsc --noEmit` is
  clean, so this could be written now; just hasn't been yet.
- **Live RevenueCat API test** — `revenuecat.test.ts`'s mocked responses
  were hand-written from RevenueCat's docs, never verified against a real
  account/API response as a *committed* test (manually verified via
  `curl` + `wrangler tail` on 2026-08-17 — confirmed real 401/403/404
  response shapes match what the mocks assume, but that was ad-hoc, not
  turned into a repeatable test).
  **Unblocked 2026-08-17** — RevenueCat project + V2 secret key both
  exist and are confirmed working; just hasn't been written as a real
  test yet.
- **Live Claude-vision extraction test** — `claude.ts`'s `extractFields`
  has never been called against the real Anthropic API from this Worker.
  **Blocked on:** a RevenueCat test customer with `SCAN` credits (so a
  real request gets past the billing check and actually reaches Claude)
  — queued as tomorrow's next step, see the progress update above. The
  secret itself is already set.
- **End-to-end `POST /v1/scan` test** (real request through a running
  Worker, real RevenueCat + Anthropic calls).
  **Partially done 2026-08-17** — deployed and smoke-tested manually
  (billing-check path confirmed working end-to-end against real
  RevenueCat), but the full happy path (successful charge + real Claude
  call) hasn't run yet, and none of this is a committed automated test.
  **Blocked on:** same RevenueCat test-customer step as above, then
  turning the manual `curl` check into a real test.

**Android app:**
- **No test suite exists** — the app itself hasn't been scaffolded yet.
  Once it is, needs: a Kotlin port of `compute_breakdown`/`verdict_for`
  tested against the same scenarios as `tests/test_breakdown.py` (the
  documented shared spec — see the portability section below), RevenueCat
  Android SDK integration tests, and purchase-flow tests (lifetime unlock
  + consumable credit packs) once that code exists.
  **Blocked on:** the Android Studio/Gradle project being scaffolded (on
  the other dev machine, per the standing "Android compilation happens
  elsewhere" preference).

## ✅ Done: tongue-weight fallback fix (implemented 2026-08-15)

Discovered while reviewing the Android design handoff (`android/design/`,
not version-controlled — see its `README.md` for the full screen list):
the Android design's blank-field fallback for stand-alone weight assumes
`trailer_axle_lb` is **80% of the trailer's actual total weight** (a
standard fifth-wheel/gooseneck pin-weight rule of thumb — pin weight is
commonly cited as 15–25% of trailer weight). The web/Streamlit apps'
current fallback — when stand-alone weight is blank, just skip the
tongue-weight adjustment entirely — isn't merely less accurate, **it's
wrong in the unsafe direction**: it implicitly assumes tongue weight is
0%, which can make an overweight trailer look compliant on the "Trailer
Total (GVWR)" check. Tongue weight physically transfers onto the truck's
axles when hitched and never appears in `trailer_axle_lb` — so comparing
`trailer_axle_lb` alone against the trailer's GVWR (a *total*-weight
rating) understates the real number whenever tongue/pin weight isn't
separately supplied.

**Fix implemented**: adopted the Android design's 80% assumption as the
correct default everywhere, per the plan above.

- `src/hdttools/api/breakdown.py`: added `DEFAULT_AXLE_TO_TOTAL_RATIO = 0.8`
  as a named constant; when `standalone_weight_lb` is blank,
  `compute_breakdown()` now sets
  `trailer_total_actual = trailer_axle_lb / DEFAULT_AXLE_TO_TOTAL_RATIO`
  with the note text specified above. The exact-figure path
  (`standalone_weight_lb` provided) is unchanged.
- `tests/test_breakdown.py`'s omitted-stand-alone-weight test now asserts
  the `/0.8` estimate (renamed
  `test_trailer_total_estimates_from_axle_reading_when_standalone_weight_omitted`).
  No new test was needed for the provided-path regression — the existing
  provided/clamp-at-zero tests exercise the untouched `if` branch
  directly, so they already prove it. 54 backend tests pass.
- Streamlit imports `compute_breakdown` directly, so this one fix covers
  both frontends — verified live via Streamlit `AppTest`: a trailer that
  previously showed "1,120 lb to spare" (falsely safe, unadjusted axle
  reading vs. GVWR) now correctly shows "1,725 lb over" in red.
- Android's design already baked in this behavior as the intended
  default — nothing to change there once built, just make sure the
  eventual Kotlin port uses the same `0.8` ratio.
- Not yet done: re-verifying against the real `ExampleDocs/` photos
  specifically (the fix was verified with synthetic numbers matching the
  existing test fixtures, not a fresh photo run) — low-risk since the
  math is a single division, but worth a real-photo pass if it matters.

## ✅ Done: portability pass (implemented 2026-08-13)

Full plan at `~/.claude/plans/i-would-like-to-toasty-dusk.md` on the
machine that ran it (won't exist elsewhere — summarized here). Goal:
make RigCheck portable to additional hosting types (Streamlit, eventually
Android), decided as **no shared hosted backend** — each platform is
self-contained.

- **Web app (`web/` + `src/hdttools/api/`) is now database-free.**
  `api/store.py` and the SQLite `rigs`/`checks` tables are gone.
  `POST /api/checks` became stateless `POST /api/breakdown` (no `rig_id`,
  no persistence). Rigs are now a client-side "last 5" list
  (`web/src/recentRigs.ts`, `localStorage`, keyed by a user-typed
  nickname, storing the full reviewed truck/trailer data so picking a
  remembered rig skips straight to the Scale Ticket step). Check history
  is session-only (gone on refresh) — this was a deliberate simplification,
  not an oversight.
- **New self-contained Streamlit app** (`streamlit_app/`) — same wizard
  flow, single Python process, no FastAPI/HTTP hop, imports
  `hdttools`'s OCR-parsing and breakdown logic directly. Recent rigs
  persist to `~/.rigcheck/recent_rigs.json` instead of a database. See
  `streamlit_app/README.md`.
- **`hdttools/__init__.py`** now tolerates a missing `tkinter` (wraps the
  desktop CLI reader imports in try/except) since it isn't always present
  on headless/minimal Python builds — relevant if Streamlit or the API
  ever runs somewhere without it.
- **`ocr_common.py`**'s Tesseract path detection now also checks common
  macOS/Linux install locations, not just Windows.
- **Android**: high-level roadmap only, not started. Decided: fully
  native (Kotlin/Compose), no OCR at all — reference images + manual
  entry instead, no network/API-key dependency. Needs its own
  Android Studio/Gradle project (doesn't exist in this repo).
  `compute_breakdown`/`verdict_for` would need a Kotlin port —
  `tests/test_breakdown.py`'s scenarios are the shared spec to check any
  port against.

54 backend tests pass; frontend typechecks/builds clean; Streamlit
smoke-tested end-to-end against the real `ExampleDocs/` photos.

**Note found during this pass, not fixed:** `ExampleDocs/GooseTag.jpg`
and `ExampleDocs/AddieTag.jpg` are swapped relative to what their names
suggest — `GooseTag.jpg` is actually the Brinkley RV **trailer** tag and
`AddieTag.jpg` is the Ford **truck** tag (opposite of the CAT ticket's
"TRACTOR # GOOSE TRAILER # ADDIE"). Didn't rename them since that wasn't
part of the ask, but any future test/demo code should use them this way
around.

## ✅ Done: axle-count / tongue-weight plan (implemented 2026-08-13)

Two logic-fault fixes were designed and approved in the session that wrote
this file, and implemented in the following session (different machine,
after `git pull`). Plan text below is kept as a record of what was built;
see `tests/test_breakdown.py` for the five tests covering all four
scenarios (default axle count, custom axle count, tongue weight omitted,
tongue weight provided, clamp-at-0), plus updated `models.py`,
`database.py`, `api/schemas.py`, `mockData.ts`, and `types.ts`. All 55
backend tests pass; frontend typechecks and builds clean.

**The two faults:**
1. `compute_breakdown()` hardcodes a 2-axle trailer (`gawr_per_axle * 2`)
   regardless of the trailer's actual axle count.
2. "Trailer Total (GVWR)" always excludes tongue weight (an acknowledged
   approximation from the original design — no tongue-weight field exists
   on either tag).

**Agreed fix**, both fields **optional with graceful fallback** to today's
behavior when left blank, and the tongue-weight estimate **folds into the
existing "Trailer Total (GVWR)" card** rather than getting a new one:

- Add `axle_count: int | None = None` to `TrailerTagData`
  (`src/hdttools/models.py`) — user-typed during trailer review (not
  OCR-derivable), field def added to `web/src/mockData.ts`'s `MODULES[2]`.
  `breakdown.py`: `gawr_per_axle * int(trailer.get("axle_count") or 2)`,
  with a note that's dynamic ("Trailer axle rating: N axle(s)...") when
  provided vs. today's "Assumes a 2-axle trailer..." when defaulted.
- Add `standalone_weight_lb: float | None = None` to `TruckTagData`
  (lb-only, no `_kg` counterpart — matches `ScaleTicketData`'s weight
  fields) — user-typed during truck review, field def added to
  `MODULES[1]`. `breakdown.py`: when provided, `tongue_weight =
  max(0.0, (steer + drive) - standalone_weight_lb)` (clamped at 0 — a
  negative estimate is physically meaningless and would understate the
  trailer total, the wrong direction for a safety check), and
  `trailer_total_actual = trailer_axle + tongue_weight` with an updated
  note explaining the estimate. When blank, keep today's exact behavior
  and note unchanged.
- Mirror both new fields into `src/hdttools/database.py`'s
  `_TRAILER_TAG_COLUMNS`/`_TRUCK_TAG_COLUMNS` and
  `src/hdttools/api/schemas.py`'s `TrailerTagOut`/`TruckTagOut`, for
  consistency (CLI persistence, API schema completeness) even though OCR
  won't populate them.
- **No other frontend code changes needed** — `ReviewStep.tsx` and
  `App.tsx`'s `createCheck` already handle `MODULES[step].fields`
  generically, so the two new field defs are sufficient to get working
  input rows end to end.
- New `tests/test_breakdown.py` (currently `compute_breakdown`/
  `verdict_for` only have indirect coverage via one `test_api.py` case):
  default-2-axle case, custom axle count, stand-alone weight omitted vs.
  provided, and the clamp-at-0 edge case (stand-alone weight larger than
  the hitched total).
- Verify against the real `ExampleDocs/` photos again after: blank vs.
  filled-in axle count changes the "Trailer Axle(s)" limit/note correctly;
  blank vs. filled-in stand-alone weight changes the "Trailer Total" actual
  value/note correctly.

**Explicitly deferred** (your idea, agreed as a good eventual direction
but not this round): reading a *second* CAT scale ticket (unhitched) so
`standalone_weight_lb` comes from an actual measurement instead of a typed
number. The math in `compute_breakdown` won't need to change again for
this — only where `standalone_weight_lb` comes from.

**Superseded by the section above**: the "when blank, skip the
tongue-weight adjustment entirely" fallback described below turned out to
be unsafe (implicitly assumes 0% tongue weight) — see "Next up" at the top
of this file for the fix.

## What exists right now

**Frontend** (`web/`, React + Vite + TS): all 7 RigCheck screens, wired to a
real backend (no more mocked data). `npm install && npm run dev` — runs on
`localhost:5173`.

**Backend** (`src/hdttools/api/`, FastAPI): OCR-only extraction (Tesseract,
no `ANTHROPIC_API_KEY`) for truck tags, trailer tags, and CAT scale
tickets, plus stateless breakdown computation (`POST /api/breakdown`) —
no persistence, no database. `uv run uvicorn hdttools.api.main:app
--reload --port 8000` — runs on `localhost:8000` (`/docs` for Swagger UI).

**Streamlit** (`streamlit_app/`): same wizard flow, self-contained, no
separate backend process — see `streamlit_app/README.md`.

Both web-app processes are already set up in `.claude/launch.json` in the
**RVSafetyCheck** directory (not this repo) if you're continuing in that
same Claude Code session/workspace — otherwise just run the commands
above.

Full pipeline is verified end-to-end against the real photos in
`ExampleDocs/` (not synthetic data): upload → OCR extract → editable
review → computed pass/fail verdict → shows up in session History/
Dashboard. 54 backend tests pass (`uv run pytest -q`).

## Fresh-machine setup checklist

On a machine that hasn't run this before:
1. `brew install uv tesseract node` (all three were missing on this Mac
   when this phase started — don't assume they're present).
2. `cd HDTTools && uv sync` (Python deps) and `cd web && npm install` (JS
   deps).
3. `git pull` to get this commit if you're setting up a second machine.

## Known limitations (intentional, not bugs)

- **Uploaded photos aren't persisted.** OCR'd in memory, discarded after
  extraction — only the reviewed field values get saved. If you want to
  revisit a check's original photo later, this would need to change.
- **OCR accuracy is real-world-imperfect**, same caveat as the pre-existing
  `scale_ticket_ocr.py`. Confirmed two live examples during testing:
  - Compliance labels sometimes drop a digit entirely (e.g. "8000" →
    "800" on the trailer tag's GAWR) — this is Tesseract misreading the
    photo itself, not a parsing bug, and there's no real regex fix for it.
  - "LB" gets misread as "1B"/"L8" etc. on tight kerning — this one *was*
    fixable and is now handled (`_kg_lb`'s trailing-unit pattern in both
    `truck_tag_ocr.py` and `trailer_tag_ocr.py` tolerates it, with a
    regression test in `test_truck_tag_ocr_parsing.py`).
  - VIN and tire-spec fields are the least reliable (not shown in the web
    review form at all, so this doesn't block anything — only 4 fields per
    document actually surface in the UI: manufacturer + the 3 weight
    figures).
- **No mobile layout, no drag-and-drop upload** (click-to-browse file input
  only) — matches the original design handoff's stated scope.
- **Not hosted anywhere yet** — local dev only, per your instruction this
  round. Since the backend is now stateless (no database), hosting it is
  simpler than before — no managed Postgres/persistence question to
  answer, just getting the process running somewhere with
  `apt-get install tesseract-ocr` available (Render was the earlier
  recommendation, Docker-based).

## Natural next steps, roughly in order

1. **Try it against more real labels.** Only one truck-tag manufacturer
   (Ford) and one trailer manufacturer (Brinkley RV) have been tested.
   Other manufacturers' compliance labels will have different layouts —
   expect to extend `truck_tag_ocr._parse_fields` /
   `trailer_tag_ocr._parse_fields` with more pattern variants as you feed
   it real photos of your actual rig.
2. **Android**, if you want to pick that up — see the portability section
   above for the decided approach (native, no OCR, reference-image +
   manual entry). Needs an Android Studio/Gradle project set up first;
   nothing in this repo blocks starting that.
3. **Decide on hosting** when ready to move off `localhost` for the web
   app — see the note above, or revisit if requirements have changed.
4. Nothing currently blocks day-to-day local use — both the web app and
   the Streamlit app are functional as-is for testing your own rig's
   numbers.
