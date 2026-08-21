# RigCheck — where things stand

Working notes for picking this back up on another machine. Written 2026-08-13.

## 🖼️ Web + Streamlit: skip-image entry and predictive tow-vehicle-alone weight — done 2026-08-20

Two related, real-world-driven requests, scoped to Web + Streamlit only
(Android/CLI untouched this round): (1) users may have 0-3 of (truck tag,
trailer tag, scale ticket) photos and need a way to skip straight to manual
entry instead of being blocked at the upload screen; (2) growing interest in
*pre-purchase* "can I tow this" estimation, which needs a tow-vehicle-alone
weight even before a real rig exists to put on a scale.

**Backend (`src/hdttools/api/breakdown.py`, the shared source of truth):**
- `compute_breakdown` gained a `pin_weight_pct` parameter (default 0.20,
  was the hardcoded `DEFAULT_AXLE_TO_TOTAL_RATIO = 0.8`) and a new 3-way
  branch for "Trailer Total (GVWR)": exact tongue-weight math when
  `standalone_weight_lb` is known, `trailer_axle / (1 - pin_weight_pct)`
  when a real trailer-axle scale reading exists, or — new — an estimate
  off the trailer's *rated* GVWR when there's no scale reading at all
  (the pre-purchase case).
- New `"insufficient"` tone + verdict tier ("Not Enough Information" when
  every row lacks data, "Partially Checked" when some do) sits alongside
  the existing pass/fail, driven by per-row **source-field presence**
  (`x_raw is None`), not `limit <= 0` — the latter was tried first and
  found wrong via test-writing (a row can have a real limit but a missing
  actual, which `limit<=0` would silently show as a false pass).
- Fixed a latent bug in both `main.py` and `streamlit_app/app.py`: each
  derived pass/fail by sniffing whether the headline starts with "Not" —
  broken once "Not Enough Information" also starts with "Not". Both now
  read `verdict_for`'s new explicit `status` field instead.
- 65/65 `uv run pytest -q` passing (was 54 before this feature).

**Web**: `UploadStep` gained an "I don't have this image" button (skips
straight to the blank review form, reusing the same rendering path a real
empty-OCR-result already takes); `ReviewStep`'s truck step gained a
tow-vehicle-only scale-ticket scanner (reuses the existing scale-ticket OCR
pipeline, maps the reading onto `standalone_weight_lb`) and, when that's
still empty, a 15-25% pin-weight slider defaulting to 20%. Verified live via
a Playwright walkthrough: 0 images at all → "Not Enough Information" with
correct "Not enough info" badges on every row, zero console errors.

**Streamlit**: same shape (`_module_step` skip button, `_render_review`,
`_render_standalone_ticket_section`) — but this is where a **real,
crash-causing bug** was caught live, not by pytest: `st.number_input`
cannot return `None`, so simply *rendering* the review screen was silently
turning every un-entered numeric field into a real `0.0` instead of leaving
it blank. That defeated the new presence-based insufficient-tracking (a
literal `0.0` isn't `None`) and then hit a `ZeroDivisionError` computing a
percentage against a `0` limit once a fully-skipped rig reached Results.
Fixed by passing `value=None` to `st.number_input` (supported since
Streamlit ~1.23; this project runs 1.61.1) instead of defaulting to `0.0` —
it now renders a genuinely blank input and returns `None` until the user
types something. Also fixed a smaller UX bug found the same way: the
"Tesseract returned no text at all" warning was showing after a deliberate
skip too (no OCR ever ran) — now gated behind a new
`st.session_state[f"{module_key}_skipped"]` flag, showing "No photo
provided" instead.
- **`tests/test_streamlit_app.py` (new)** — the project's first Streamlit
  UI-level automated tests, via `streamlit.testing.v1.AppTest`. Two tests:
  the full skip-everything-reaches-Results-without-crashing regression
  (this is what pins down the `ZeroDivisionError` fix — `compute_breakdown`'s
  own unit tests can't see this bug, since they call it directly with
  genuinely-`None` dicts, never through `app.py`'s widget layer), and the
  skip-notice-vs-OCR-warning distinction. See the corrected `AppTest`-on-
  Windows note further down (search "Correction, 2026-08-20") — it does
  *not* hang on this machine, contrary to an earlier session's finding.
- Verified live via Playwright, same walkthrough as Web: 0 images at all →
  "Not Enough Information", all six rows showing "Not enough info", no
  exceptions.

Scope deliberately left for a follow-up round (per the plan this was built
from): no new predictive/cargo-capacity *output* row yet — just the two
input mechanisms (skip button, tow-vehicle-alone weight source).

**Follow-up done, 2026-08-20 — the output row above, plus a legal
disclaimer.** "Tow Vehicle Total (GVWR)" previously stayed "Not enough
info" forever in the pre-purchase scenario (a tow-vehicle-alone reading
known, but no real hitched combined scale reading) — its insufficiency
check only ever recognized a real `steer_axle_lb`+`drive_axle_lb` pair.
Fixed by giving `compute_breakdown` a second, independent branch for the
truck-side total: when there's no hitched reading but a real stand-alone
one exists, estimate the missing tongue weight off the trailer-side total
(`trailer_total_actual * pin_weight_pct`) and add it onto the stand-alone
weight — same math shape as the existing trailer-side estimate, just
mirrored onto the truck side.
- **Real bug fixed in passing, found while redesigning this**: the old
  trailer-total branch gated its three-way logic on `if standalone_weight`
  truthy *alone*, not on whether a real hitched reading also existed — so
  a user with *only* a tow-vehicle-alone reading (the exact pre-purchase
  case) silently got `tongue_weight = max(0, 0 - standalone) = 0`, losing
  the tongue-weight estimate entirely instead of falling back to the
  axle-based or GVWR-fallback estimate. Fixed by decoupling
  `have_hitched`/`have_standalone` explicitly. Regression test:
  `tests/test_breakdown.py::test_truck_and_trailer_totals_both_estimate_when_only_a_trailer_axle_reading_exists`
  (asserts the trailer total comes out to the correct 14,225 lb estimate,
  not the bug's 11,380 lb symptom).
- **New `estimated: bool` field** on each breakdown item (additive,
  `BreakdownItemOut`/`BreakdownItem` in both schema layers) — `True` only
  when a row's number came from `pin_weight_pct` math rather than a real
  reading; always `False` on insufficient rows (a row can internally take
  an estimate branch while still being insufficient for an unrelated
  reason, e.g. no trailer GVWR at all — the flag must not leak `true` in
  that case; see the corresponding pytest case).
- **New persistent legal disclaimer** — explicitly requested with real
  content, not just a generic warning: build/trim options change real
  payload, passengers/cargo aren't accounted for, the specific vehicle's
  own certification label must be checked before buying, and the
  consumer alone is responsible for safe towing and FMCSA/DOT compliance
  (federal and state). Deliberately **not** the existing one-time
  `DisclaimerModal`/`DISCLAIMER_TEXT` (acknowledged once, then gone) —
  this one re-renders every time any row has `estimated: true`:
  `web/src/components/PredictiveEstimateNotice.tsx` (amber `--state-warning`
  callout, visually distinct from the mauve `--state-info` "insufficient"
  styling) and Streamlit's `PREDICTIVE_ESTIMATE_NOTICE` via `st.warning`.
- Verified live on both platforms (Playwright for Web, `AppTest` for
  Streamlit) with the same scenario: truck tag + stand-alone weight
  entered, trailer tag entered, scale ticket fully skipped — confirms
  "Tow Vehicle Total (GVWR)" renders a real "5,500 lb to spare" badge
  (was "Not enough info"), and the new disclaimer renders on both.
- `uv run pytest -q`: 70/70 passing (was 65). `npm run build` clean.

**Follow-up, 2026-08-20 (same day) — Scale Ticket step now points at the
predictive path explicitly.** The generic "I don't have this image" skip
button didn't tell anyone that skipping the *scale* step specifically is
what unlocks the estimate above. `UploadStep.tsx`'s scale-module rendering
(and Streamlit's `_module_step` for `module_key == "scale"`) now show:
an italic caption ("No CAT scale ticket? You can skip this step and still
build an estimated model from your truck and trailer tag ratings.") plus
*two* buttons instead of one — "No Image / Enter Weight Manually" (renamed
from the old generic label, same skip action) and "Build Estimated Model /
No CAT scale info" (new, same skip action, framed for the predictive use
case). Both buttons call the identical underlying skip handler — this is
purely a messaging/framing change, no new behavior. Truck Tag and Trailer
Tag steps are unchanged (still one generic "I don't have this image"
button each). Verified live on both platforms (Playwright screenshot for
Web, `AppTest` for Streamlit). `uv run pytest -q`: still 70/70. `npm run
build`: clean.

**Follow-up, 2026-08-20 (same day) — real tow-vehicle-only photo added,
real bug found and fixed via it.** `ExampleDocs/CatScale-GooseOnly.jpg` is
a real CAT Scale ticket weighing just the tow vehicle (tractor# GOOSE, no
trailer hitched — trailer axle reads 00 LB). Used to close a
long-flagged gap: this repo had never had a test that runs real Tesseract
OCR against a real photo file, only hand-transcribed text.
- ✅ **Real bug found and fixed, Streamlit only**: scanning a
  tow-vehicle-only ticket correctly set `truck["standalone_weight_lb"]`,
  but the very next render of the review form silently overwrote it back
  to blank. Root cause: `_render_review`'s `st.number_input(key=
  "truck_standalone_weight_lb", ...)` had already been instantiated
  earlier in the run (in a prior page load, before the scan), so its own
  cached widget state — still blank — took priority over the freshly
  updated data dict on the next rerun, per Streamlit's standard "a new
  `value=` is ignored once a keyed widget already has session-state" rule.
  Never caught before because the only prior verification of this feature
  was a screenshot of the upload UI rendering, not an actual scan-and-
  confirm-the-field-updates walkthrough. Fixed via the standard Streamlit
  workaround: stash the new value in a scratch `_pending_standalone_weight_lb`
  key and apply it to the widget's own key at the *top* of `_module_step`,
  before `_render_review` instantiates the widget (setting a widget's key
  *after* it's already been instantiated this run raises a
  `StreamlitAPIException` — tried that first, had to switch approaches).
  Verified against the real live app via Playwright, not just `AppTest`.
- **New tests, all real-photo/real-OCR, not mocked**:
  `tests/test_scale_ticket_ocr_parsing.py::test_parse_fields_on_a_real_tow_vehicle_only_ticket`
  (ground-truth `_parse_fields` coverage using this ticket's actual
  Tesseract output — documents, doesn't fix, some unrelated cosmetic OCR
  garbling in `tractor_number`/`trailer_number`/`location_name`, none of
  which feed into `compute_breakdown`). `tests/test_scale_ticket_real_photo.py`
  (new file — the first test in this repo to run real Tesseract against a
  real `ExampleDocs/` image end to end, both at the `scale_ticket_ocr`
  module level and through the real `/api/extract/scale-ticket` FastAPI
  endpoint with nothing mocked). `tests/test_streamlit_app.py::
  test_scanning_a_real_tow_vehicle_only_photo_fills_in_standalone_weight`
  (the regression test for the bug above, uploading the real photo through
  `AppTest`'s `file_uploader.set_value(...)`).
- **Unrelated environment note**: hit the recurring "websockets" file-lock
  quirk (see the "Session gotcha hit twice" note further down) badly
  enough this session that the package ended up genuinely corrupted (missing
  `__version__`, Streamlit failed to boot at all) rather than just the
  usual cosmetic warning — fixed by manually deleting
  `.venv/Lib/site-packages/websockets*` and letting `uv sync --extra
  streamlit` reinstall clean. If `streamlit run` ever fails with
  `ImportError: cannot import name '__version__' from 'websockets'`, this
  is the fix.
- `uv run pytest -q`: 74/74 passing (was 70).

**Follow-up, 2026-08-20 (same day) — WTWT branding in the Streamlit
sidebar, and a real test-isolation bug found in the process.**
`streamlit_app/assets/wtwt_logo.png` (the "Wandering Trails Wagging
Tails" logo — RV, mountains, two dogs — provided by the user) now renders
via `st.image(..., width=160)` at the top of the sidebar, unconditionally
(the sidebar itself used to only render at all once a check existed in
session history; restructured so branding shows from the very first page
load, with "This session's checks" nested conditionally beneath it).
- ✅ **Real bug found and fixed**: `tests/test_streamlit_app.py`'s
  `AppTest`-driven tests run the real (non-mocked) `app.py`, including its
  real `recent_rigs.py` persistence layer — which has always written
  straight to `~/.rigcheck/recent_rigs.json`, the developer's actual local
  file, with no test-time override. Every prior run of this test file
  silently left synthetic "Test Rig"/"Predictive Verify"/etc. entries in
  the real recent-rigs list (confirmed and cleaned up manually this
  session; also found via a live screenshot showing them cluttering the
  rig picker). Fixed with an autouse `monkeypatch` fixture that redirects
  `recent_rigs.RECENT_RIGS_PATH` to a `tmp_path` for every test in the
  file — verified the real file's mtime is now untouched by a full test
  run. **If any *other* future Streamlit test file drives a full checkout
  through `AppTest`, it needs this same fixture** — it isn't automatic
  across files.
- `uv run pytest -q`: still 74/74.

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
- The Android app itself doesn't exist yet and has no code calling this
  endpoint — Play Billing product setup (lifetime unlock SKU + consumable
  scan-pack SKUs) still needs to happen in Play Console.

**Next step:** the backend is fully built, deployed, and verified against
real infrastructure (accounts, secrets, deploy, and now a full happy-path
charge + extraction, all confirmed 2026-08-17) — nothing left to do here
until the Android app exists to actually call it. Remaining work is
Play Console developer registration (long lead time, worth starting
whenever there's spare time — see above) and, separately with no fixed
timeline, the Android Studio project itself. The billing-model decision
itself is done — see above.

## 🤖 Android app: Phases 0-4 done, paid scan feature working end-to-end

Full roadmap (6 phases) was planned 2026-08-17 — see git history / ask for
the plan if needed; not duplicated here. This section tracks execution
status only. Decided: build happens on this Windows machine (the earlier
"Android compilation happens elsewhere" note referred to a *different*
machine, not this one). `applicationId` = `com.rigcheck.app`. RevenueCat
SDK choice: native `purchases-android`, not `purchases-kmp`.

**Phase 0 (dev environment) — done, verified via CLI, 2026-08-17:**
- Android Studio (Quail 3 | 2026.1.3) installed to `G:\Android\AndroidStudio`
  (checksum-verified download, silent-install needs admin elevation this
  automated session couldn't grant, so the user ran the installer/wizard
  directly — same pattern as GUI dashboard steps elsewhere in this project).
  SDK installed to `G:\Android\Sdk` via its Setup Wizard.
- **No standalone JDK installed** — Android Studio bundles a JetBrains
  Runtime at `G:\Android\AndroidStudio\jbr`; set as `JAVA_HOME` (User env
  var) so `gradlew`/`sdkmanager`/`avdmanager` work from a bare terminal too.
- `GRADLE_USER_HOME=G:\GradleUserHome` set (User env var) — Gradle's
  dependency cache, same category of fix as the earlier npm-cache move.
- **Session gotcha, will recur:** newly-set User env vars aren't visible to
  an already-running shell (same class of issue as the `ANTHROPIC_API_KEY`
  propagation gotcha) — every `gradlew`/`sdkmanager`/`avdmanager`/`emulator`
  call in a shell opened *before* a var was set needs it passed inline
  (`JAVA_HOME=... GRADLE_USER_HOME=... command`) until the shell restarts.
- Confirmed via CLI: `./gradlew assembleDebug` and `./gradlew test` both
  succeed; Gradle cache correctly lands on `G:\GradleUserHome`, not C:.

**Phase 1 (project scaffolding) — done, verified via CLI, 2026-08-17:**
- Project created at `android/` (inside this repo) via Android Studio's New
  Project wizard — Empty Activity template, Compose, Kotlin DSL.
  `applicationId=com.rigcheck.app`, `minSdk=26`, `targetSdk=37`.
- A save-location warning about the space in
  `G:\Claude Experiment\...` was dismissed — that warning is a legacy
  caution for NDK/native-toolchain builds; this project has no native code,
  and the build succeeded with the space in the path.
- Baseline deps added: Navigation-Compose (2.9.8), `lifecycle-viewmodel-compose`
  (2.11.0), `kotlinx-serialization-json` (1.11.0) + the matching Kotlin
  serialization Gradle plugin — versions checked directly against Google's/
  Maven Central's metadata (not guessed), filtered to the latest genuinely
  stable release (the metadata's own `<latest>`/`<release>` tags include
  alpha/rc builds, so those had to be excluded explicitly). Build confirmed
  green with all of them in.

**Phase 2 (core business logic port) — done, 2026-08-17, all tests green:**
- Ported `compute_breakdown`/`verdict_for` to
  `android/app/src/main/java/com/rigcheck/app/domain/Breakdown.kt` +
  `VerdictInfo.kt`, with `TruckTag`/`TrailerTag`/`ScaleTicket` domain models
  under `domain/model/` (deliberately narrower than the full Python
  dataclasses — only fields `compute_breakdown` or manual entry actually
  use; VIN/tire-spec/scale-metadata fields are scan-only and don't exist in
  the Kotlin domain model at all).
- Fixed the Python-truthiness parity trap identified in planning before it
  could bite: `if standalone_weight:` and `if axle_count_raw else 2` both
  treat an explicit `0` as "not provided" in the original — ported
  explicitly (`!= null && != 0`), not via a naive `?:`, which would have
  silently diverged on a `0` input.
- String formatting deliberately split from the domain layer (unlike the
  Python/TS originals, which bake comma-formatted strings directly into
  their output): `domain/NumberFormatting.kt` holds the one canonical
  `formatWholeNumber()` (needed by both the domain layer itself, since note
  text like "1,660 lb tongue weight" embeds a formatted number as business
  text, and by `ui/format/NumberFormatting.kt`'s display helpers
  `formatLb()`/`badgeLabel()`). `barColor`/`bandBg` (CSS var strings in the
  originals) don't port at all — deferred to whenever the UI screens map
  `Tone` to actual Compose colors.
- **Caught and fixed one real bug during testing, not just porting**: the
  first draft of the tongue-weight note used a local `roundToInt().toString()`
  instead of the shared comma-formatter, which would have produced `"1660 lb
  tongue weight"` instead of the spec's `"1,660 lb tongue weight"` — the
  ported test caught this immediately (comma-formatted assertion failed),
  fixed by routing through the one shared `formatWholeNumber()`.
- **Test port**: `BreakdownTest.kt` — the same 5 scenarios from
  `tests/test_breakdown.py` (default axle count, custom axle count,
  standalone-weight omitted/provided, clamp-at-0) *plus* 2 new cases the
  Python suite doesn't cover (`axle_count = 0`, `standalone_weight_lb =
  0.0`) verifying the truthiness-parity fix above. Plus `VerdictTest.kt`
  (2 cases — `verdict_for` also has no existing Python test) and
  `NumberFormattingTest.kt` (3 cases). **13/13 tests pass**, confirmed via
  `./gradlew test` and the generated JUnit XML reports (`tests="7"` /
  `"2"` / `"3"` / `"1"` across the 4 test classes, 0 failures/errors) — not
  just a green Gradle exit code, the actual per-class counts were checked.
  `./gradlew assembleDebug` also still succeeds.

**Emulator setup — AVD created, boot blocked on a real hardware issue:**
- `cmdline-tools` (sdkmanager/avdmanager) weren't part of Studio's default
  SDK install — downloaded separately (checksum-verified) and extracted to
  `G:\Android\Sdk\cmdline-tools\latest`.
- System image `system-images;android-37.0;google_apis_playstore;x86_64`
  (2.8 GB) installed manually via `sdkmanager`, matching `targetSdk=37` and
  including Play Store (useful later for Phase 4/6 billing tests).
- **`avdmanager create avd` (the older, deprecated tool) is broken for this
  system image** — fails with "Could not load devices from ...devices.xml"
  because this particular image ships with no `devices.xml`. Worked around
  by using the newer `android` CLI instead (also in `cmdline-tools/latest/bin`,
  the tool `sdkmanager`'s own deprecation warning points to):
  `android --sdk="G:\Android\Sdk" emulator create <profile>` (profile names:
  `android emulator create --list-profiles`). This tool auto-picked its own
  system image (API 36, not the API 37 one installed above) rather than
  reusing it — harmless (G: has ample space) but means both API 36 and 37
  images now sit on disk unused-except-one.
- **Real mistake caught and fixed:** the `android` CLI **defaults to its own
  SDK at `C:\Users\Angela\AppData\Local\Android\Sdk`** if `--sdk` isn't
  passed explicitly — first attempt did exactly this and silently downloaded
  ~3.4 GB (platform-tools, emulator binary, the API 36 system image) to the
  space-constrained C: drive. Caught via `android info` showing the wrong
  `sdk:` path, deleted (`Remove-Item` on the whole stray folder, 3.4 GB
  reclaimed), and redone with `--sdk` explicit. **Always pass `--sdk=` (or
  `ANDROID_SDK_ROOT`) explicitly with this tool — it does not reliably pick
  up the SDK from Android Studio's own configured location.**
- AVD instance data (`~/.android`, normally lands on C: — flagged in the
  original plan as "stubborn, revisit if C: usage climbs") was proactively
  relocated *before* first boot, since first boot can add several GB via
  userdata/snapshot images: `ANDROID_AVD_HOME=G:\Android\EmulatorHome\avd`
  and `ANDROID_EMULATOR_HOME=G:\Android\EmulatorHome` (both User env vars).
  Note the emulator binary's actual runtime search order (confirmed via
  `emulator.exe -help-all` and by directly hitting the error) is
  `$ANDROID_AVD_HOME` → `$ANDROID_SDK_HOME\avd` → `$HOME\.android\avd` —
  `ANDROID_EMULATOR_HOME` alone was *not* sufficient to relocate the `avd/`
  subfolder despite the help text implying it would be; both vars are now
  set for safety.
- ✅ **Emulator fully working — done 2026-08-18.** Booting needed *two*
  separate fixes, not one — worth remembering both if this ever needs
  reproducing on another machine:
  1. **BIOS/UEFI firmware virtualization** (Intel VT-x/AMD-V) was off —
     `systeminfo`'s `Virtualization Enabled In Firmware: No` caught this;
     fixed by the user rebooting into firmware setup and enabling it (no
     software/Windows-feature toggle can do this, hardware-level only).
  2. **Windows Hypervisor Platform**, a separate *Windows* feature from the
     BIOS setting — still showed `InstallState: 2` (disabled) even after
     the BIOS fix (checked via `Get-CimInstance -ClassName
     Win32_OptionalFeature -Filter "Name='HypervisorPlatform'"`, since the
     more obvious `Get-WindowsOptionalFeature` cmdlet itself requires
     elevation even to *read* status). Needs admin elevation to enable
     (`dism.exe /online /enable-feature /featurename:HypervisorPlatform
     /all`, or the "Turn Windows features on or off" GUI) — same
     elevation wall as the Android Studio installer, so the user ran it
     directly, then rebooted again.
  - With both fixed, `emulator -avd medium_phone` boots cleanly — log
    confirms `WHPX on Windows 10.0.26200 detected. Windows Hypervisor
    Platform accelerator is operational`. Full pipeline verified: `adb
    devices` sees it, `gradlew installDebug` installs the real app,
    `adb shell am start` launches it, confirmed via a real screenshot
    (`adb exec-out screencap`) showing the stock "Hello Android!" screen
    rendering correctly with the Play Store icon present in the status bar.

**Phase 3 (manual-entry UI) — done, verified end-to-end on-device,
2026-08-18.** Real screens built from the 2026-08-17 mockups (reconciled
into `ANDROID_DESIGN_BRIEF.md`), not stubs:

- **Theme**: `ui/theme/Color.kt`/`Theme.kt`/`Type.kt` replaced entirely —
  were 100% stock Android Studio purple/pink template before this phase.
  Real brand palette from `web/src/design-system/tokens.css`, light-only
  `lightColorScheme`, `dynamicColor` off (so Material You can't override
  the fixed brand colors). Quicksand + Karla wired via the Compose
  **Downloadable Fonts API** (fetched at runtime from Google Fonts, not
  bundled `.ttf` files) — needed `res/values/font_certs.xml`, which
  **must be copied verbatim from Google's own sample**, not
  hand-transcribed: a first attempt at reproducing it from memory got the
  certificate bytes wrong and used the wrong XML array type
  (`<array>` vs `<string-array>`), caught only by fetching the real file
  from `android/user-interface-samples` and diffing before it shipped.
- **Reference images**: the 3 mockup photos (`android/design/extracted/.../
  reference-images/`) resized via a one-off `uv run python` + Pillow
  script (repo's existing Python dependency, no new tooling) from
  ~3.6 MB combined down to ~0.63 MB, capped at 1600px long edge, and
  copied into `res/drawable/` as `ref_truck_tag.jpg`/`ref_trailer_tag.jpg`/
  `ref_scale_ticket.jpg`. **Real bug caught by on-device testing**: the
  first resize pass called `ImageOps.exif_transpose()`, which rotated the
  truck-tag photo sideways — the design export's pixel data was already
  correctly rotated (confirmed by direct visual inspection), but the file
  carries a *stale* EXIF orientation tag left over from the original phone
  capture that no longer matches the pixels. Fixed by dropping the
  `exif_transpose()` call entirely.
- **Domain model change**: `TruckTag`/`TrailerTag`'s `manufacturer` field
  renamed to `description`, plus a new `name` field added to both —
  matches the reconciled brief's mockup-driven field list. Safe rename:
  `manufacturer` was never read by `compute_breakdown`, no test fixture
  set it.
- **Domain layer change, decided this session**: `Breakdown.kt`'s
  `"Tow Vehicle Total (GVWR)"` and `"Combined Rig Weight"` rows now get
  dynamic, number-specific note text (e.g. "Steer (5,640) + drive (9,080)
  = 14,720 lb, which is 720 lb over this truck's 14,000 lb GVWR.")
  instead of a fixed generic sentence — matches the mockup, but is a
  **deliberate Android-only enhancement**, not ported back to
  `breakdown.py`/`calc.ts`. Two new JUnit cases added
  (`BreakdownTest.kt`) asserting the exact generated text.
- **Data layer**: `data/RecentRigsRepository.kt` — Preferences DataStore
  (new dependency, `androidx.datastore:datastore-preferences` 1.2.1),
  one serialized JSON blob via `kotlinx.serialization`, porting
  `web/src/recentRigs.ts`'s exact algorithm (case-insensitive dedupe by
  nickname, prepend, slice to 5) — verified against the real file this
  session, not from memory.
- **Navigation**: `ui/navigation/RigCheckNavHost.kt` — Navigation-Compose
  with type-safe `@Serializable` route objects (natural fit given
  `kotlinx-serialization-json` was already a dependency). One
  nav-graph-scoped `RigCheckViewModel` (`AndroidViewModel`, no DI
  framework needed) holds in-progress truck/trailer/scale state and an
  in-memory-only `disclaimerAcknowledged` flag — never persisted, shown
  once per process per the brief.
- **Reference-image zoom, decided this session**: tap-and-hold (not the
  alternative persistent-lower-third-crop option) — press and drag on the
  truck/trailer tag photos to zoom into that exact spot, matching the
  mockup's hover-to-zoom intent adapted for touch. Highlight-ring color
  (`#f0942f`) pulled directly from the mockup's own JS, not guessed.
  Scale-ticket screen uses a simpler static numbered-legend instead (no
  interaction) — exact badge x/y positions weren't extractable from the
  design source, so the legend row carries the number-to-field mapping.
- **"Scan Photo" is now fully live on all three chooser screens** — see
  the Phase 4 section below.
- **Full on-device verification, real data, both branches of the
  tongue-weight fallback exercised**: installed the real (non-stub) app
  on the now-fully-working emulator, manually drove the entire flow via
  `adb shell input tap`/`text` (with `uiautomator dump` for exact element
  bounds — screen-relative tap coordinates broke once the keyboard
  reflowed the layout, a test-methodology gotcha, not an app bug) using
  the real `ExampleDocs/`-equivalent CAT Scale ticket numbers. Confirmed
  via real screenshots at every step: Rig Picker (gradient header, empty
  state, working nickname field) → Chooser (disabled Scan card, active
  Manual card) → Truck Tag Entry (corrected reference image, all fields
  bind correctly) → Trailer Tag Entry → Scale Ticket Entry (numbered
  legend + real ticket image) → Disclaimer (exact finalized text) →
  **Results**, which rendered the full real breakdown correctly: mixed
  pass/fail rows, correct colors/borders/percentages, and the new dynamic
  note text tap-to-expanded exactly as designed. `./gradlew test
  assembleDebug` both still pass after all of the above.

**Phase 4 (optional paid scan feature) — done, verified on-device,
2026-08-18:** connected to the RevenueCat test customer `smoke-test-user`
(the same one used for the 2026-08-17 server-side Worker smoke test),
using the RevenueCat **public** Test Store SDK key pasted directly into
chat (public keys are explicitly exempt from the "never type secrets in
chat" rule — unlike `REVENUECAT_SECRET_KEY`/`ANTHROPIC_API_KEY`, which
stayed out of chat/commands as always).
- **RevenueCat SDK wiring**: `RigCheckApplication.kt` configures
  `Purchases` with a hardcoded `appUserID("smoke-test-user")` —
  deliberately a testing-only shortcut, commented in code as needing to
  change to the SDK's default per-install anonymous ID before any real
  release. `data/RevenueCatManager.kt` wraps the SDK's callback APIs as
  suspend functions (balance, offerings, purchase via the current
  non-deprecated `PurchaseParams.Builder`/`purchase()` path, restore).
- **Scan pipeline**: `ActivityResultContracts.TakePicture()` +
  `FileProvider` (no `CAMERA` permission needed) →
  `data/PhotoEncoding.kt` (downscale ≤1600px long edge, JPEG q85, base64)
  → `data/ScanApiClient.kt` (OkHttp POST to the deployed `scan-proxy`
  Worker) → `data/ScanFieldMapping.kt` (merges extracted fields onto the
  current module's state, never clobbering a value the user already
  typed) → lands on the *same* Phase 3 entry screen for review, exactly
  as planned (no new form UI needed).
- **New `RigCheckRoute.Paywall` + `PaywallScreen.kt`**: custom Compose
  layout (not RevenueCat's prebuilt UI), real Test Store offerings/prices
  via `StoreProduct.price.formatted` (never hardcoded), "Restore
  purchase" link. Reachable by tapping Scan Photo at 0 credits, or by
  tapping the new credit-balance chip directly ("get more scans"
  affordance).
- **Real bug caught and fixed during on-device verification**: the
  RevenueCat SDK caches virtual-currency balance client-side and has no
  way to know the Worker just deducted a credit server-side via a direct
  REST call (not through the SDK's own purchase flow) — so the credit
  chip kept showing the pre-scan balance after a real scan. Fixed by
  calling the SDK's `invalidateVirtualCurrenciesCache()` before every
  balance fetch in `RevenueCatManager.getScanCreditBalance()`, so launch
  and post-scan/post-purchase refreshes always hit the network. This is
  the same "don't trust memory, verify against the real decompiled jar"
  discipline as the Phase 4 planning stage (`javap -p` on
  `purchases-10.17.0.aar`'s `classes.jar` found the method).
- **Full on-device verification, `./gradlew assembleDebug` clean**,
  driven via `adb shell input`/`uiautomator dump` (same technique as
  Phase 3): credit chip showed the real `smoke-test-user` balance (99) on
  launch; tapping Scan Photo launched the real system camera app via
  `FileProvider` with no crash; capturing and confirming a photo drove
  the full pipeline (encode → upload → real Worker call → real Claude
  call → parsed response → merged onto `TruckTag` → navigated to the
  review screen) — fields came back blank/`<UNKNOWN>` as expected since
  the AVD's back camera is a generic virtual scene, not a real label, but
  the pipeline itself is proven; balance correctly decremented 99 → 98,
  confirmed durable across an app reinstall (not just an optimistic local
  update); Paywall rendered two real Test Store products ($99.99
  Lifetime, $0.99 Consumable) with working "Restore purchase"; a real
  Test Store purchase completed end-to-end (RevenueCat's own "Test Store
  Purchase" confirmation dialog → "Purchase complete!" toast → balance
  correctly incremented 98 → 108, the consumable pack's configured
  credit grant).

All 6 planned phases are now done. Remaining Android work is polish/tests
only — see "🧪 Tests still outstanding" below.

**Two real bugs found during the user's own hands-on emulator testing,
both fixed and re-verified on-device, 2026-08-18:**
- **Recent-rig selection skipped the Chooser entirely.** Picking an
  existing rig from `RigPickerScreen` navigated straight to
  `RigCheckRoute.ScaleTicketEntry`, bypassing `Chooser(EntryModule.SCALE)`
  — so returning users had no Scan Photo option at all, only the fresh
  "start a new rig" path did. Fixed in `RigCheckNavHost.kt`:
  `onSelectRecentRig` now navigates to `Chooser(EntryModule.SCALE)`
  instead. Re-verified: selecting an existing rig now lands on the
  Chooser with Scan Photo available.
- **Scan Photo only offered "take a new photo," never "use one you
  already have."** The user correctly pointed out that in practice the
  photo is usually already taken before opening the app — certainly true
  for a CAT Scale ticket, which is a printed receipt handed over well
  before anyone opens RigCheck. `ChooserScreen.kt` now shows a small
  dialog on tapping Scan Photo ("Take Photo" / "Choose from Gallery"),
  the latter via `ActivityResultContracts.PickVisualMedia()` (the modern
  Android Photo Picker — no storage permission needed on any API level).
  The credit-balance chip also got a `onClick` (opens the Paywall
  directly, a "get more scans" affordance) to support testing this
  without spending real Test Store credits repeatedly.
  **AVD-testing-only gotcha hit and fixed while verifying this**: photos
  pushed onto the emulator via `adb push` land in MediaStore with
  `is_pending=1` (a flag meaning "still being written"), which hides them
  from every gallery/picker app including the new one — not an app bug,
  a test-environment quirk. Fix: `adb shell content update --uri
  content://media/external/images/media/<id> --bind is_pending:i:0` per
  file. Even after that, the Photo Picker's own separate sync can lag
  behind a raw `adb push`; `adb shell am force-stop
  com.google.android.providers.media.module` forces it to resync on next
  launch. Re-verified end-to-end with a real, legible photo this time
  (`ExampleDocs/CatScale-Ticket.jpg` via "Choose from Gallery," not the
  AVD's virtual-scene camera): Claude correctly extracted every field —
  scale location "LOVES COUNTRY STORES," steer 5640, drive 9080, trailer
  19680 lb, all matching the real ticket exactly — and the credit balance
  decremented correctly (108 → 107).

## 📱 Android distribution: sideloading confirmed viable, Play Console decision parked

Raised 2026-08-18 after Phase 4 was committed/pushed — the user wants to
field-test the app on their own phone for a while before deciding
anything about a real Play Store release. **Not blocking further work,
no action taken yet** — this section exists so the decision context
survives a machine switch.

**Sideloading needs no Google Play Console account at all** — confirmed
this is a fully separate concern from Play Store distribution:
- **Recommended path**: enable Developer Options (Settings → About Phone
  → tap Build Number 7×) and USB Debugging on the phone, plug it into
  this PC, authorize the one-time "Allow USB debugging?" prompt, then
  `adb install` the existing debug APK exactly like every emulator
  install this session — no rebuild needed beyond what already exists.
- **Cable-free alternative**: transfer the APK to the phone any way
  (email, Drive, USB file copy) and tap to install; Android prompts for a
  one-time "install unknown apps" permission on whichever app opened the
  file. Fully standalone afterward either way — the cable/PC is only
  needed at install time, not for ongoing use.
- **Caveat specific to field-testing the paid scan feature**: the app is
  currently wired to RevenueCat's **Test Store** with the hardcoded
  `smoke-test-user` identity (see the Phase 4 section above) — so scans/
  purchases on a sideloaded phone build won't involve real money and will
  share the same credit balance this session's testing has been using
  (107 as of the last check), not a fresh account. Convenient for free
  field testing, but not representative of a real customer's experience,
  and this hardcoded identity must change before any real release
  (already flagged in code as testing-phase-only). Manual entry (the
  free, offline path) has no such caveat.

**Play Console registration — decision explicitly parked by the user,
"need to think about it for a while":**
- **Personal vs. Organization account** is the open question. Personal
  is simpler (no D-U-N-S/business-entity verification) and was my
  recommendation for a solo/experimental project like RigCheck;
  Organization is only needed to publish under a registered business
  name. Neither choice is reversible without creating a new account, so
  there's no harm in taking time here.
- Known facts for whenever this decision resumes: one-time $25 USD
  registration fee; Google now requires **identity verification**
  (government-ID upload, possibly a live selfie-match step) for *all*
  new developer accounts, personal or organization, which can take
  anywhere from a few days to ~2 weeks to clear; after approval, Google
  requires new personal accounts to run a **closed test with 20+ testers
  for 14 continuous days** before allowing a production release.
- None of this blocks sideloaded field testing, which needs no Play
  Console account at all — the two tracks (personal field testing vs.
  eventual Play Store release) are fully independent until the user
  decides to actually publish.

## 📐 Tiered test strategy: methodology decided 2026-08-20, Python retrofit done 2026-08-21

Raised 2026-08-15 as a parked idea; **the methodology itself was decided
2026-08-20 and is now written down in `TESTING.md`** — a Minor/Major
regression-scoping model (test scope driven by what a change actually
touches: new library or interface change = Major, internal-only = Minor),
replacing the sanity/regression/full framing originally sketched below.

**2026-08-21 — Python side retrofitted.** `tests/TESTING.md` (new)
classifies all 14 Python test files against the four categories. Found
and closed one real gap in the process: nothing checked that
`compute_breakdown`'s `estimated` field actually survives the real
`/api/breakdown` → Pydantic `response_model` → JSON round trip — a
rename/drop on either side of that boundary would have gone uncaught
even with every other breakdown test passing. New interface test:
`test_api.py::test_breakdown_endpoint_response_preserves_the_estimated_field`.
Two more gaps identified but **not yet closed** (see `tests/TESTING.md`'s
"Known gaps" section): the truck/trailer OCR-output-keys-vs-schema
contract, and the OCR-output-keys-vs-Streamlit's-`FIELDS`-dict contract —
both lower-risk (a mismatch shows up as a `None` field, not silently
wrong math, unlike the breakdown case). `uv run pytest -q`: 75/75.

**2026-08-21 (same day) — shared Python/Kotlin golden vectors built, and
a real live bug found on Android.** Checking how far `Breakdown.kt`
(Android's hand-port of `compute_breakdown`/`verdict_for`) had actually
drifted, before building the shared-vector infrastructure `TESTING.md`
calls for, turned up more than expected: **none** of the 2026-08-19–
2026-08-20 feature arc made it to Kotlin — no adjustable `pinWeightPct`
(still hardcodes the old `DEFAULT_AXLE_TO_TOTAL_RATIO = 0.8`), no
`INSUFFICIENT` tone, `verdictFor` only ever returns pass/fail (no
partial/insufficient), no `estimated` field, no predictive standalone-
only truck-side estimate branch. **Worse — a real, live bug**: Kotlin's
existing standalone-weight branch has the *exact* bug fixed in Python
this session (`standaloneProvided` doesn't check whether a real hitched
reading also exists), so a tow-vehicle-alone reading with no hitched
scale data still silently produces the wrong trailer total on Android
today.

Built `test-vectors/breakdown_cases.json` (10 cases, snake_case fields,
rounded-whole-number `actual_lb`/`limit_lb` — not exact doubles or
formatted strings, since Python only exposes formatted display strings
and Kotlin deliberately keeps raw unrounded numbers, formatting only at
the UI layer; this tests the math, not presentation) — shared by
`tests/test_breakdown_golden_vectors.py` (Python, all 10 pass — it's the
source of truth) and
`android/.../domain/BreakdownGoldenVectorTest.kt` (Kotlin). Each case
declares a `requires` list; Kotlin's runner skips (`Assume`, not a
silent pass) anything needing a capability it doesn't have, and prints a
count every run: **4 of 9 fully supported, 5 skipped by name**. The 10th
case — the live bug — was deliberately left unskipped per your explicit
call: it fails for real, `expected:<14225> but was:<11380>`, an honest,
reproducible proof the bug is live on the shipped Android app, not just
a missing feature. Confirmed via a real `./gradlew testDebugUnitTest`
run (not just `test`, which isn't a valid task name for this Android
module — use the variant-specific task). Full Android suite after: 22
tests, exactly that 1 expected failure, nothing else regressed.

**Deliberately not done as part of this**: fixing `Breakdown.kt` itself
(porting the missing features, fixing the live bug) — this was
infrastructure only, per your choice to build the mechanism before doing
the port. That's real, separate feature/bugfix work, not yet started or
scheduled.

**2026-08-21 (same day) — Round 1 correctness fixes done.** Per your
"correctness fixes first" call: `Breakdown.kt` now mirrors Python's
current 3-branch trailer-total logic (exact/axle-estimate/GVWR-fallback),
`Tone` gained `INSUFFICIENT`, `verdictFor` gained the full
pass/fail/partial/insufficient priority logic (a new `VerdictStatus`
enum, mirroring Python's explicit `status` field — never derived from
headline text), and adjustable `pinWeightPct` was folded in too (a
near-free parametrization of code already being touched, per the
reclassification flagged in the plan and approved). UI: `BreakdownRow`/
`ResultsScreen` render `INSUFFICIENT` with the already-defined-but-unused
`DuskMauve` and an info icon.
- ✅ **The live bug is fixed** — `standalone_without_hitched_falls_back_to_axle_estimate`
  (renamed from the "live bug" case now that it's fixed) passes on both
  platforms.
- **A second real bug found while porting**: Python's own `have_standalone`
  check had regressed to a plain `is not None` earlier this session
  (during the trailer-total decoupling fix) — an explicit
  `standalone_weight_lb: 0` was being treated as *provided* instead of
  "not entered," producing a nonsensical result (a truck "weighing 0 lb"
  used as real tongue-weight math). No test had covered this specific
  edge case. Caught only because Kotlin's *existing* test for this exact
  scenario (a deliberate truthiness-parity decision from Android's
  original build) failed against the ported logic. Fixed in both
  `compute_breakdown` and `Breakdown.kt` — `bool(standalone_raw)` /
  `!= null && != 0.0`, matching `axle_count`'s existing pattern.
- **A third real bug found via manual on-device verification, not any
  automated test**: `BreakdownRow`'s progress bar only passed `color` to
  `LinearProgressIndicator`, not `trackColor` — Material3's default track
  color is theme-derived, not based on `color`, so the empty portion of
  every insufficient row's bar (always 0%, i.e. all track) rendered a
  fixed green regardless of tone. Invisible for a normal row (mostly
  covered by the colored fill), glaring on a real device for a blank rig.
  Fixed by setting `trackColor` explicitly.
- One golden-vector case needed re-tagging: `standalone_without_hitched_falls_back_to_axle_estimate`'s
  "Tow Vehicle Total (GVWR)" row expectation also depends on
  `predictive_truck_estimate` (Python's oracle bakes both capabilities
  into this input combination together, since Python already has the
  predictive branch) — re-tagged `requires: ["predictive_truck_estimate"]`,
  so it's correctly skipped until Round 2, not a false failure.
- Verified: `./gradlew testDebugUnitTest` (30 tests) and
  `./gradlew connectedDebugAndroidTest` (33 tests, real emulator) both
  fully green; `uv run pytest -q` 86/86. Manual on-device walkthrough of
  a fully blank rig confirmed "Not Enough Information" renders correctly
  end to end (screenshotted, not just asserted).
  **Emulator gotcha hit and fixed**: a background-launched emulator
  reported `sys.boot_completed=1` and `adb devices` showed `device`
  almost immediately, but the screen was actually asleep the whole time —
  every instrumented test failed with "No compose hierarchies found in
  the app" (Compose can't build a semantics tree with nothing rendering),
  a misleading error that looked like a code/config problem but was
  purely an idle/display-off emulator. `adb shell input keyevent
  KEYCODE_WAKEUP` alone wasn't durable (the screen went back to sleep
  during the ~2.5 minute instrumented test run despite an extended
  `screen_off_timeout` setting); `adb shell svc power stayon true`
  (stay-awake-while-charging, always true for an emulator) fixed it for
  good. Worth remembering if this ever needs reproducing.
- Golden-vector status after Round 1: **8 of 10 cases fully supported**
  by the Kotlin port (was 4 of 9 before Round 1 — the standalone-zero fix
  above didn't change this count, it was caught by `BreakdownTest.kt`,
  not the golden vectors). The 2 still skipped both need
  `predictive_truck_estimate` — Round 2.

**2026-08-21 (same day) — Round 2 tests written and landed red, on
purpose.** Per your TDD request: wrote and committed the predictive
standalone-only truck-estimate tests *before* the feature itself, so
implementation starts from a known-red state against an already-agreed
spec rather than a blank page. `predictive_truck_estimate` moved into
`BreakdownGoldenVectorTest.kt`'s `SUPPORTED_CAPABILITIES` (so its case,
and `standalone_without_hitched_falls_back_to_axle_estimate`'s — which
also needs it — run for real instead of skipping); `BreakdownTest.kt`
gained a new case mirroring `tests/test_breakdown.py`'s
`test_truck_total_estimates_from_standalone_weight_when_no_hitched_reading`.
Confirmed both fail with clean `ComparisonFailure`/`AssertionError` diffs
(`expected:<success> but was:<insufficient>`), not crashes or compile
errors — `./gradlew testDebugUnitTest`: 31 tests, exactly these 2 red.
No production code touched this round; `computeBreakdown` still lacks
the branch. **UI tests deliberately not added** — a Compose test
referencing a not-yet-existing UI state/component would fail to
*compile*, not just fail an assertion (a real limit of TDD against a
statically-typed UI framework, flagged before starting); those land
alongside their composables when the feature itself is built, not ahead
of them. `uv run pytest -q` unaffected (86/86, no Python changes).

**2026-08-21 (same day) — Round 2 implemented: predictive standalone-only
truck-side estimate, domain + full UI.** `computeBreakdown` gained the
standalone-only truck-side branch (mirrors `breakdown.py`'s
`elif have_standalone:` exactly: `truckTongueWeightEstimate =
trailerTotalActual * pinWeightPct`, `truckTotalActual = standaloneWeight +
truckTongueWeightEstimate`) — the two red tests from earlier that day went
green with no changes to themselves, and golden vectors went to 10/10
(full parity with Python). Also added `BreakdownItem.estimated: Boolean`
(mirrors Python's `estimated` field, deliberately deferred until now — see
Round 1's note) and wired it through both the trailer-total branches and
the new truck-total branch; `BreakdownGoldenVectorTest.kt` now asserts it
too.

UI half, all new this round: `RigCheckViewModel` gained `pinWeightPct`
(whole-number percentage 15-25, default 20, same convention as Web's
`wizard.pinWeightPct`) threaded into `computeBreakdown`, and
`performStandaloneScan` — reuses the existing paid `EntryModule.SCALE`
scan pipeline (Android's only OCR path, unlike Web's separate free-tier
extraction endpoint, so a standalone scan consumes a credit like any
other scan) and maps the result onto `truck.standaloneWeightLb` via a new
`standaloneWeightFrom()` helper in `ScanFieldMapping.kt` (steer+drive if
both present, else `gross_weight_lb` — mirrors Web's
`scanStandaloneTicket`). `TruckTagEntryScreen` gained a "Don't know your
tow vehicle's stand-alone weight?" section below the existing stand-alone
field: a "Scan tow-vehicle-only ticket" button (own camera/gallery
launchers + source-choice dialog, matching `ChooserScreen`'s pattern) and
a pin-weight-% `Slider` (15-25, hidden once a stand-alone weight is
known). `ResultsScreen` gained `EstimatedFiguresNotice` (new file,
Android port of Web's `PredictiveEstimateNotice.tsx`, same legal copy),
shown whenever `breakdown.any { it.estimated }`.

Verified: `./gradlew testDebugUnitTest` 31/31 (all green, no reds left).
`connectedDebugAndroidTest` 39/39 (33 prior + 6 new: 4 in
`TruckTagEntryScreenTest` for the slider show/hide and scan dialog/error,
2 in `ResultsScreenTest` for the notice show/hide). Full manual on-device
walkthrough on `medium_phone` AVD: created a rig with only a truck GVWR/
GAWRs + a manually-entered 6,000 lb stand-alone weight, no trailer scale
data, no truck scale data at all — confirmed the pin-weight slider
disappeared once stand-alone weight was entered, the "Scan tow-vehicle-
only ticket" button opened the Take Photo/Choose from Gallery dialog
correctly, and the Results screen showed the `EstimatedFiguresNotice`
plus a correct "Tow Vehicle Total (GVWR): 8,500 lb" (6,000 standalone +
20% of the 12,500 lb GVWR-fallback trailer estimate) and "Trailer Total
(GVWR): 12,500 lb of 12,500 lb, 100%" — both exactly matching the
`predictive_truck_estimate` golden vector's numbers for the same inputs.
No Python/Web files changed this round (Android-only work, matching an
already-built cross-platform spec).

**2026-08-21 (same day) — `web/` test infrastructure installed.** Added
`vitest`, `@testing-library/react`, `@testing-library/jest-dom`,
`@testing-library/user-event`, `jsdom` as dev dependencies; `npm test`
now runs `vitest run`. `vite.config.ts` gained a `test` block
(`environment: 'jsdom'`, `setupFiles: ['./src/setupTests.ts']`) via the
`/// <reference types="vitest/config" />` triple-slash pattern (keeps
one config file instead of a separate `vitest.config.ts`).
`src/setupTests.ts` imports `@testing-library/jest-dom/vitest` for the
`toBeInTheDocument()`-style matchers. One smoke test
(`src/App.smoke.test.tsx`, renders `<App />`, asserts "RigCheck" shows)
proves the harness end-to-end before any real tests are written against
it — passes. `npm run build` (which typechecks `src/**` via `tsc -b`,
test files included per `tsconfig.app.json`'s `include: ["src"]`) still
clean.

**2026-08-21 (same day) — App.tsx interaction tests written.** New
`web/src/App.interaction.test.tsx`, five cases, all driven through the
real rendered UI with `@testing-library/user-event` (`App.tsx` has no
exported handlers to call directly - its ~10 handlers all read/write one
shared `wizard` object via closures, so the UI is the only real entry
point): (1) a full happy path - start a new rig, skip all three image
steps, reach Results, confirm both `recentRigs` (localStorage) and
`history` updated from the same `continueReview` call; (2) selecting an
existing rig jumps straight to the scale step, skipping truck/trailer -
written as a regression-shaped test ahead of any bug, mirroring the exact
shape of the real bug `RigCheckNavHostTest` caught on Android 2026-08-18;
(3) an extraction error clears once the user skips instead of lingering
on `wizard.uploadError`; (4) scanning a tow-vehicle-only ticket fills the
stand-alone-weight field and hides the pin-weight slider; (5) the
pin-weight slider's value reaches `createBreakdown` as the raw 15-25
whole number, not divided by 100 - the exact `pin_weight_pct` units-risk
flagged below, now locked down from the Web side. `npm test`: 6/6 (5 new
+ the smoke test). `npm run build` still clean. New `web/TESTING.md`
classifies this suite the way `tests/TESTING.md`/`android/TESTING.md` do
for their platforms.

**2026-08-21 (same day) — pin_weight_pct inter-module interface fixture
built.** New shared `test-vectors/pin_weight_pct_contract.json`
(`{ui_percent: 15, api_fraction: 0.15}`), the same "one file, both
languages derive their expected numbers from it" pattern as
`breakdown_cases.json`, but for a single risky convention rather than
full breakdown cases. Consumed by two new, explicitly paired tests: Python's
`tests/test_api.py::test_breakdown_endpoint_pin_weight_pct_is_a_fraction_not_the_ui_percentage`
(confirms `api_fraction == ui_percent / 100`, that the fraction produces
the documented `13,388 lb` trailer total, AND that sending the raw
unconverted `15` produces a visibly wrong *negative* weight - dividing by
`1 - 15`- rather than a quietly-off one), and Web's new
`src/api.test.ts` (mocks only `fetch`, so `api.ts`'s real
`pin_weight_pct: pinWeightPct / 100` line runs - confirms calling
`createBreakdown(..., 15)` sends `pin_weight_pct: 0.15` in the request
body). This is a stronger check than `App.interaction.test.tsx`'s
existing pin-weight test, which mocks `./api` entirely and so only proves
`App.tsx` passes the raw number *to* `api.ts`, not that `api.ts` itself
converts it correctly. `uv run pytest -q`: 87/87 (was 86). `npm test`:
7/7 (was 6). `npm run build` still clean - JSON-imports the fixture
directly (`import CONTRACT from '../../test-vectors/...json'`) rather
than via Node's `fs`, since `tsconfig.app.json`'s `types: ["vite/client"]`
doesn't include Node's ambient types and adding them project-wide felt
like the wrong tradeoff for one test file.

**2026-08-21 (same day) — recentRigs.ts/api.ts function tests written.**
New `web/src/recentRigs.test.ts` (9 cases): `loadRecentRigs`'s empty-vs-
stored-vs-corrupt-JSON-vs-non-array-JSON cases; `saveRecentRig`'s
prepend-and-persist, case-insensitive same-nickname replace-not-duplicate
(and re-ordering to the front), the 5-rig cap dropping the oldest, and -
the one genuinely interesting case - `saveRecentRig` still returns the
computed list even when `localStorage.setItem` throws (quota exceeded),
matching the source's own comment that in-memory state should keep
working even when persistence silently fails. `web/src/api.test.ts`
expanded from 1 test to 10: `createBreakdown` gained request-shape
(truck/trailer/scale pass through unchanged), success, and error-handling
(server `detail` message vs. the generic `Request failed (status)`
fallback) cases alongside its existing pin-weight-pct interface test;
`extractTruckTag` got the same success/error/request-shape coverage
(confirms it posts `FormData` containing the file); `extractTrailerTag`/
`extractScaleTicket` just confirm each hits its own distinct endpoint,
since they're thin wrappers over the same `postFile` helper
`extractTruckTag` already exercises fully - the one thing that actually
varies between the three. `npm test`: 25/25 (was 7). `npm run build`
still clean. This closes both of `web/TESTING.md`'s remaining function-
test gaps from the retrofit's original plan order.

**Not done yet**: dedicated component-level tests for `ReviewStep`/
`UploadStep`/`ResultsStep` (currently only indirect coverage via the
interaction suite). Also reconciling this Minor/Major model with
`android/TESTING.md`'s and `workers/scan-proxy/TESTING.md`'s existing
sanity/daily/weekly/release tiers (a different, earlier scheme, still
accurate for those two platforms as written).

Original sketch, superseded by `TESTING.md` but kept here for history:

- **Sanity** — a small, fast set run on every change to catch major
  breakage.
- **Module regression** — a fuller suite for the specific module touched,
  run when a change lands there.
- **Integration sanity** — a fast cross-module check.
- **Full/"weekend" regression** — every corner case, every module,
  including integrations — run periodically rather than on every change.

**Open questions from the original framing** (raised 2026-08-15):

1. **What "module" means here — partially resolved.** `TESTING.md`
   settles on module = file as the general rule, but doesn't enumerate
   this repo's specific boundaries (e.g. whether the 3 OCR readers count
   as one module or three is still an open call whenever this gets
   applied for real).
2. ✅ **What concretely distinguishes the tiers — resolved.** See
   `TESTING.md`'s Minor/Major criteria: new library or an interface/
   parameter/return-shape change triggers Major; internal-only logic
   changes stay Minor.
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
   all — would need Vitest). Streamlit: **partially resolved 2026-08-20**
   — `tests/test_streamlit_app.py` now exists as real, committed pytest
   coverage via `AppTest` (not ad-hoc hand-run scripts) — the "nothing
   committed" state described here is stale.
6. **The concrete, immediate gap regardless of how the above resolves**:
   `ExampleDocs/` real-photo verification has only ever happened via
   manual ad-hoc runs when checking a specific fix — never a committed,
   repeatable test. **Partially closed 2026-08-20** for the scale-ticket
   reader specifically — see `tests/test_scale_ticket_real_photo.py` and
   the "Follow-up" note in the predictive-spare-capacity section above
   (found and fixed a real bug this exact gap was designed to catch).
   Truck tag and trailer tag readers still have no equivalent real-photo
   test — same pattern, straightforward to replicate whenever picked up.

## 📋 Backlog: regression-tier docs + a static CI/CD-style dashboard

Raised 2026-08-19, right after `scan-proxy`'s sanity/daily tiers were
built — **not started**. Two related pieces:

1. ✅ **Document the regression tiers themselves — done for two
   platforms, 2026-08-19.** `workers/scan-proxy/TESTING.md` and
   `android/TESTING.md` both exist now, same structure: tier table +
   what each individual test covers. Remaining: Python/`hdttools` and
   Web have no test-tier docs yet (and no formal tiering at all — see
   the tiered-test-strategy idea above).
2. **A statically-generated report of regression run results**, the
   user's own framing: "something that looks similar to what a CI/CD
   dashboard might show, only statically generated in our case" — this
   repo has no CI (confirmed above), so this would be a script that runs
   a test tier and renders its results (pass/fail per test, per tier,
   maybe trended over time if run repeatedly) as a static HTML/Markdown
   page, run manually alongside the tiers themselves rather than
   triggered by CI.

**Open questions, not yet resolved:**
- Scope: piece 1 (docs) is now unblocked for the dashboard's format
  question — both `scan-proxy` and Android have tiers to design against,
  so the "don't make it scan-proxy-shaped" concern is addressed. Piece 2
  (the actual dashboard script) still hasn't been started.
- Format/tooling for the dashboard: Node's built-in test runner supports
  a `--test-reporter` flag (e.g. `tap`, `junit`, `spec`) that could feed
  a small static-site generator step, vs. hand-rolling something simpler
  directly from `node --test`'s output.
- Where results get archived (if trended over time at all) — a
  git-committed file that updates each run, or explicitly ephemeral
  (regenerated fresh each time, never versioned)?

## 🧪 Tests still outstanding

Living checklist — remove an entry (or fold it into a "✅ Done" note,
matching this file's convention) the moment its test actually gets
written. Add new entries here as soon as a gap is spotted, not just
mentioned in conversation, so it survives a machine switch. See
`Claude.md`'s "NEXT_STEPS.md Maintenance" section for the standing rule
behind this.

**Full rebuild + regression pass, all platforms — requested 2026-08-18.**
**Desktop + Web done this session; Android + `scan-proxy` still
outstanding** (not done this pass — pick up separately):

- ✅ **Desktop (Streamlit) — done 2026-08-18, nothing broken, one real
  environment gap found and fixed.** `uv run pytest -q`: 54/54 pass.
  `streamlit run` boots and serves (HTTP 200). Every individual piece of
  `app.py` (imports, `load_recent_rigs()`, `ensure_tesseract_configured()`)
  verified working in isolation via a throwaway script.
  **Real finding**: this machine had no `~/.streamlit/credentials.toml`,
  so a fresh `streamlit run` (or `AppTest`, which drives the same
  machinery) hangs *indefinitely* on Streamlit's interactive first-run
  "send usage stats?" prompt when there's no TTY to answer it — this is
  what actually consumed ~40 minutes before being caught (process
  confirmed alive but at 0% CPU, i.e. genuinely blocked, not slow).
  Fixed by writing `~/.streamlit/credentials.toml` (`email = ""`) and
  `~/.streamlit/config.toml` (`gatherUsageStats = false`,
  `server.headless = true`) — **do this on any new machine before first
  Streamlit run**, interactive or not.
  **Correction, 2026-08-20 — the "AppTest hangs on Windows" finding above
  did not reproduce.** `tests/test_streamlit_app.py` (new, see the
  skip-image feature section below) drives `AppTest.from_file(...)` through
  a full multi-step wizard flow (rig creation → three skip clicks → three
  continues → disclaimer) on this same Windows machine, no hang, ~1s total
  for both tests. Root cause of the original hang was never re-identified
  (maybe a since-fixed Streamlit bug, maybe an environment difference that
  session) — but treat "`AppTest` is broken on Windows" as stale, not
  current fact. A real `ExampleDocs/`-photo-driven `AppTest` walkthrough
  (uploading actual files, not just clicking skip/continue) is still
  untried and remains the actual open gap.
- ✅ **Web — done 2026-08-18, nothing broken.** `uv run pytest -q`
  (shared backend): 54/54 pass. `npm run build` in `web/`: clean. `npm
  run dev`: serves (HTTP 200). Real HTTP requests against the live
  FastAPI backend (`uv run uvicorn hdttools.api.main:app --port 8000`)
  using the actual `ExampleDocs/` photos through
  `/api/extract/truck-tag`, `/api/extract/trailer-tag`,
  `/api/extract/scale-ticket` — Tesseract OCR still extracts fields
  correctly. `/api/breakdown` re-confirmed the tongue-weight fix is live
  end-to-end through the real API: `"Trailer Total (GVWR)"` →
  `"14,225 lb"` for the standard test fixtures, exactly matching the fix.
- **Minor, unrelated finding**: `uv run pytest`/`uv sync` without
  `--extra streamlit` vs. with it causes `websockets` to flip between
  16.1.1 and 17.0.1 on every single invocation (visible as a "Failed to
  uninstall... missing RECORD file" warning each time) — cosmetic, tests
  pass either way, not investigated further (would mean adjusting
  dependency pins, out of scope for a regression *check*).
- **Session gotcha hit twice**: backgrounding a `uv run ...`/`streamlit
  run` process via `&` in git-bash and later `kill`-ing the *reported*
  job PID does not reliably kill the real underlying `python.exe`
  process — it can keep running orphaned, holding native `.dll`/`.pyd`
  files open and causing the *next* `uv sync` to fail with "Access is
  denied" trying to replace them. Fix each time: find and
  `Stop-Process -Force` the actual `python.exe` under this project's
  `.venv` path via PowerShell, not the bash-reported PID.
- ✅ **Android — done 2026-08-18**, as part of building Phase 3 (see the
  Android section above): `./gradlew test`/`assembleDebug` both clean,
  plus a full real on-device walkthrough well beyond what this checklist
  item originally asked for.
- ✅ **`workers/scan-proxy/` — sanity + daily tiers done 2026-08-19.**
  See the dedicated writeup below; the "already-deployed Worker still
  live" re-confirmation now belongs to the weekly/release tiers, not yet
  built (see below).

**`workers/scan-proxy` (Cloudflare Worker) — tiered test plan, sanity +
daily tiers implemented 2026-08-19:**

A full architectural review (every module's exported API, what each
existing test covered, and a gap analysis per module) preceded this —
see git history around 2026-08-19 for the analysis itself if ever needed
again. That review, plus a pass specifically for realistic
user-confusion failure modes (not just code-coverage gaps), produced a
4-tier plan: **sanity** (a handful of tagged smoke tests, <1s, run before
every commit) → **daily** (the full mocked regression suite, zero
network calls, run while actively working on this Worker) → **weekly**
(bounded real Anthropic + RevenueCat calls against a dedicated disposable
test customer) → **release** (same, against the live deployed Worker
URL, before/after every `wrangler deploy`). Manual cadence, no CI —
`npm test`/`npm run test:sanity` are the only scripts that exist so far;
`test:weekly`/`test:release` are deferred until those tiers are built.

- **A real bug found and fixed before writing any new tests**: `scan.ts`'s
  `502 extraction_failed` response always said "Credit refunded," even
  on the path where the refund call itself failed
  (`.catch(() => {})` swallowed it silently) — a user could be charged,
  see an error, and be told they were refunded when they weren't. Fixed:
  the refund's actual outcome now determines the response — a genuinely
  failed refund now returns a distinct `extraction_failed_no_refund`
  code with an honest message, instead of lying. Two tests pin this down
  (`scan.test.ts`): a thrown refund and an `ok:false`-but-not-thrown
  refund are both treated as "failed," and the message is asserted to
  *not* claim a refund happened.
- **Sanity tier**: 7 tests tagged `[sanity]` across the existing files
  plus the three new ones below (one happy-path check per critical
  module) — `npm run test:sanity`, ~0.3s.
- **Daily tier — three previously-untested modules got their first
  coverage**:
  - `http.test.ts` (new) — `json()`/`badRequest()`'s status/content-type/
    envelope shape, previously asserted only incidentally through other
    tests.
  - `claude.test.ts` (new) — mocks the real Anthropic HTTP endpoint via
    `fetch` (same technique as `revenuecat.test.ts`) rather than reaching
    into SDK internals; **the most important case here** is the one that
    `scan.ts`'s entire refund path exists to handle — no matching
    `tool_use` block in Claude's response → `extractFields` throws.
    Real gotcha hit while writing this: the Anthropic SDK's response
    parsing keys off the mocked `Response`'s `Content-Type` header — a
    mock without `application/json` set gets silently mis-parsed into
    something with no `.content`, throwing a confusing `TypeError`
    inside `extractFields` instead of ever reaching the code being
    tested.
  - `index.test.ts` (new) — the router/entry-point layer, including the
    **first tests anywhere that exercise `runScan`'s real
    `defaultScanDeps` wiring** (every `scan.test.ts` case uses fake
    deps) — required mocking `fetch` to route by URL (RevenueCat vs.
    Anthropic) rather than one canned response, since real deps means
    one mock has to stand in for both external APIs at once.
  - Extended `request.ts`/`revenuecat.ts`/`scan.ts`/`docTypes.ts` tests
    with the type-confusion, network-failure, idempotency-key-reuse, and
    field-name-contract gaps the architectural review surfaced — see git
    history for the full list; `docTypes.test.ts` now specifically
    asserts each doc type's schema still contains the exact field names
    `ScanFieldMapping.kt` on Android reads, which the older
    required-matches-properties test structurally couldn't catch.
  - Two gaps deliberately left as **documented current behavior, not
    fixed**: `spendCredit`/`fetch` rejecting outright (not just
    returning a non-ok status) propagates as an unhandled rejection
    with no `try/catch` anywhere in the chain; there's no request-level
    idempotency across client retries (each `runScan` call mints its own
    key). Both are pinned down by tests explicitly documenting today's
    behavior so a future change is a deliberate choice, not an accident.
  - Total: **47 tests, all passing, `tsc --noEmit` clean.**
- **Weekly and release tiers — not started.** Needs a dedicated
  disposable RevenueCat test customer (separate from `smoke-test-user`,
  which stays reserved for manual Android field testing) before this can
  begin — deliberately deferred until picked back up.
- **Also still flagged, not yet acted on**: no timeout on the Anthropic/
  RevenueCat `fetch` calls — a hung call currently means the Android
  loading spinner spins forever with no error, ever. Not a scan-proxy
  test gap so much as a missing feature (both here and client-side);
  raised during this review, not yet a task.

**Android app:**
- ✅ **`compute_breakdown`/`verdict_for` Kotlin port — done 2026-08-17.**
  `BreakdownTest.kt` (9 cases: the 5 from `tests/test_breakdown.py` plus 2
  zero-value edge cases it doesn't cover plus 2 for the new dynamic
  Android-only row notes), `VerdictTest.kt` (2 cases),
  `NumberFormattingTest.kt` (3 cases) — 13/13 passing, see the section
  above for detail.
- ✅ **Phase 3/4 manual on-device verification (navigation, disclaimer
  gating, results rendering, RevenueCat/scan/purchase flow) — done
  2026-08-18**, real walkthroughs against the RevenueCat Test Store and
  the live `smoke-test-user` customer (see the Phase 3/4 sections above).
  Converted into a committed, repeatable `androidx.compose.ui.test` suite
  2026-08-19 — see below.
- ✅ **`RevenueCatManager` unit test — done 2026-08-19.**
  `RevenueCatManagerTest.kt` (4 JUnit4 + MockK cases) specifically covers
  the balance-cache-invalidation bug found and fixed 2026-08-18: asserts
  `getScanCreditBalance()` calls `invalidateVirtualCurrenciesCache()`
  before reading the balance (not after), plus the balance-present,
  balance-absent, and `appUserId`-passthrough cases. New test
  dependencies: `io.mockk:mockk` 1.14.3, `kotlinx-coroutines-test` 1.10.2
  (added to the version catalog; versions verified against Maven Central
  at write time, not assumed from memory).
  **Two genuine deadlocks hit and fixed while writing this — both
  confirmed via `jstack` thread dumps, not guessed:**
  1. **`Purchases.sharedInstance` needs `mockkObject(Purchases.Companion)`,
     not `mockkStatic(Purchases::class)`.** The latter compiles and runs
     without error but silently doesn't intercept the call — `sharedInstance`
     is `Purchases.Companion.getSharedInstance()` under the hood, not a
     true `@JvmStatic` method, so the *real* getter ran every time and threw
     (`Purchases.configure()` is never called in a plain JVM unit test).
  2. **MockK's `coEvery`/`coVerifyOrder` on a suspend function deadlock
     if called from inside any coroutine builder** (`runBlocking`,
     `runTest`, doesn't matter which) — `coEvery` internally bridges into
     suspend land via its *own* `runBlocking` to record the call
     signature, and nesting that inside another coroutine on the same
     thread means both park waiting on each other. This happened twice
     (once nested in `runTest`, once nested in plain `runBlocking`) before
     the actual fix: **mock the real callback-based
     `getVirtualCurrencies(GetVirtualCurrenciesCallback)` member method
     instead of the `awaitGetVirtualCurrencies()` suspend extension
     function built on top of it** — a plain `every {...} answers {...}`
     invoking the callback synchronously, no `coEvery`/`mockkStatic` on
     the extension file needed at all. `RevenueCatManager`'s real
     (unmocked) suspend wrapper still runs and bridges the callback into a
     suspend result exactly as it does in production.
  `./gradlew test`/`assembleDebug` both clean after.
- ✅ **Compose UI test suite (daily-equivalent tier) — done 2026-08-19.**
  Full writeup in `android/TESTING.md`; summary here. 30 instrumented
  tests across 10 files (`ResultsScreenTest`, `BreakdownRowTest`,
  `DisclaimerScreenTest`, `RigPickerScreenTest`,
  `TruckTagEntryScreenTest`, `TrailerTagEntryScreenTest`,
  `ScaleTicketEntryScreenTest`, `ChooserScreenTest`,
  `CreditBalanceChipTest`, `PaywallScreenTest`) plus navigation-flow
  coverage in `RigCheckNavHostTest.kt` — `./gradlew
  connectedDebugAndroidTest`, 30/30 passing.
  - **New `CustomTestRunner.kt`** substitutes a plain `Application` for
    `RigCheckApplication` during instrumented tests, so
    `Purchases.configure()` never runs — confirmed via `adb logcat`
    showing zero `[Purchases]` SDK log lines across a full run. This
    keeps the whole suite offline and hermetic (no real network, doesn't
    touch `smoke-test-user`'s balance), needing zero production-code
    changes since `RigCheckViewModel`/`PaywallScreen`'s RevenueCat calls
    were already wrapped in `runCatching`.
  - **Real regression test added** for the recent-rig routing bug found
    2026-08-18 (`RigCheckNavHostTest.recentRigSelectionRoutesThrough...`):
    does a full checkout, goes back to `RigPicker`, selects the
    just-created recent rig, and asserts it lands on
    `Chooser(EntryModule.SCALE)` rather than skipping straight to the
    entry form — would fail if that bug reappeared.
  - **Real gotcha hit and fixed**: entry screens (`TruckTagEntryScreen`
    etc.) live inside a `verticalScroll` `Column`, and their Next/Check
    Weights buttons sit below the fold — `performClick()` doesn't
    auto-scroll a node into view before clicking, unlike Espresso.
    Fixed by chaining `.performScrollTo().performClick()`; first showed
    up as 5 failures (a "not displayed" assertion, and several button
    clicks silently not registering) across the entry-screen and
    NavHost-flow tests.
  - **Minor production change**: added `testTag` modifiers to one
    representative field per entry screen (`truck_description`,
    `trailer_description`, `scale_location`) so tests can target a
    specific `TextField` reliably — `LabeledTextField`'s existing
    `modifier` parameter already threaded through to the real field, so
    this needed no changes to the shared component itself.
  - **Weekly-equivalent tier — not started**, same blocker as
    `workers/scan-proxy`'s own weekly tier: needs the dedicated
    disposable RevenueCat test customer. Would cover: `PaywallScreen`
    rendering real Test Store offerings/prices, a real purchase
    completing and incrementing the balance, a real scan against the
    deployed Worker decrementing it. Tracked together with scan-proxy's
    weekly tier — pick both up in the same session once that customer
    exists.

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

Goal: make RigCheck portable beyond the original web+DB setup (decided:
**no shared hosted backend**, each platform self-contained). Web app
(`web/` + `src/hdttools/api/`) is now database-free — stateless
`POST /api/breakdown`, recent rigs are a client-side `localStorage` list
(`web/src/recentRigs.ts`). New self-contained Streamlit app
(`streamlit_app/`) reuses the same OCR/breakdown logic directly, no HTTP
hop, recent rigs persist to `~/.rigcheck/recent_rigs.json`. See
`streamlit_app/README.md`. `hdttools/__init__.py` now tolerates a
missing `tkinter`; `ocr_common.py`'s Tesseract path detection also
checks macOS/Linux locations. Android: high-level roadmap only at this
point (superseded by the monetization section above) — fully native, no
OCR, needs its own Android Studio/Gradle project.

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

Two logic faults were fixed: `compute_breakdown()` hardcoded a 2-axle
trailer regardless of actual axle count, and "Trailer Total (GVWR)"
always excluded tongue weight. Fix: both `axle_count` (trailer) and
`standalone_weight_lb` (truck) became optional user-typed fields with
graceful fallback to the old behavior when left blank; the tongue-weight
estimate folds into the existing "Trailer Total (GVWR)" card rather than
a new one. See `tests/test_breakdown.py` for the five tests covering all
four scenarios (default axle count, custom axle count, tongue weight
omitted/provided, clamp-at-0). All 55 backend tests pass; frontend
typechecks/builds clean.

**Explicitly deferred** (agreed as a good eventual direction, not yet
built): reading a *second* CAT scale ticket (unhitched) so
`standalone_weight_lb` comes from an actual measurement instead of a
typed number — `compute_breakdown`'s math won't need to change again for
this, only where the value comes from.

**Superseded by the tongue-weight fallback fix above**: the omitted-
stand-alone-weight fallback described here ("skip the tongue-weight
adjustment entirely") turned out to be unsafe — see that section above
for the current behavior.

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
2. **Decide on hosting** when ready to move off `localhost` for the web
   app — see the note above, or revisit if requirements have changed.
