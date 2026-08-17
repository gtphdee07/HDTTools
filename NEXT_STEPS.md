# RigCheck — where things stand

Working notes for picking this back up on another machine. Written 2026-08-13.

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

## 🤖 Android app: build started, Phase 0/1 done, Phase 2 in progress

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

**Next step:** Phase 3 (manual-entry UI — screens 1-4, 7-8, Navigation-
Compose NavHost, DataStore-based last-5-rigs persistence). Phase 2
(business logic) is fully done and the emulator is fully working end to
end — see above — so nothing blocks starting Phase 3.

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
  match real behavior (manually verified via `curl` + `wrangler tail` on
  2026-08-17: real 401/403/404/200 response shapes all matched what the
  mocks assume, including a real charge against a real customer), but
  that verification is ad-hoc, not a *committed*, repeatable test yet.
- **Live Claude-vision extraction test** — **manually verified
  2026-08-17**: a real photo (`ExampleDocs/AddieTag.jpg`) sent through
  the deployed Worker got correctly-extracted fields back from a real
  Claude Haiku call. Not yet a committed automated test.
- **End-to-end `POST /v1/scan` test** (real request through a running
  Worker, real RevenueCat + Anthropic calls) — **manually verified
  2026-08-17**, full happy path: real charge, real extraction, real
  balance decrement confirmed in the RevenueCat dashboard. See the
  progress update above for the exact steps (test customer created via
  a direct `GET /v1/subscribers/` call, no mobile app needed).

All three of the above are now **just a matter of writing the test**,
not blocked on any missing infrastructure — turning the 2026-08-17
manual `curl`/`wrangler tail` verification into real, committed
`node --test` cases (using a real but disposable RevenueCat test
customer) is the concrete remaining gap.

**Android app:**
- ✅ **`compute_breakdown`/`verdict_for` Kotlin port — done 2026-08-17.**
  `BreakdownTest.kt` (7 cases: the 5 from `tests/test_breakdown.py` plus 2
  zero-value edge cases it doesn't cover), `VerdictTest.kt` (2 cases),
  `NumberFormattingTest.kt` (3 cases) — 13/13 passing, see the section
  above for detail.
- **Still needed:** Compose UI tests (navigation happy-path, disclaimer
  once-per-session gating, results rendering), RevenueCat Android SDK
  integration tests, and purchase-flow tests (lifetime unlock + consumable
  credit packs) — none of this code exists yet (Phase 3/4).
- **Emulator-dependent tests** (Compose UI tests, live on-device scan
  test) — **unblocked 2026-08-18**, the emulator is fully working (see
  above) — blocked only on the UI/scan code itself existing (Phase 3/4).

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
