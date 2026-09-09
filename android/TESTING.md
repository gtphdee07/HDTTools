# Android testing

Mirrors `workers/scan-proxy/TESTING.md`'s structure and the same
event-based strategy (retired the old time-cadence tier names
2026-08-24 — see the root `TESTING.md`'s "Event-based tiers, not
time-cadence tiers" section): Minor/Major suites are fully offline and
mocked/faked; the External suite makes real, bounded external calls.
This file documents current state — see `ARCHIVE_ANDROID.md` (repo
root) for the narrative history of how it got built and what bugs were
found along the way. See the root `TESTING.md`'s Minor/Major/External
sections for how this maps to that file's regression-scoping rules —
the commands below are unchanged from before the rename, only the tier
names changed.

## Categories

| Category | Status | Trigger | Network calls | Command |
|---|---|---|---|---|
| **Minor (Unit, JVM)** | ✅ built | a Minor change (internal-only) | none | `./gradlew test` |
| **Major (instrumented, offline)** | ✅ built | a Major change (public-interface/new-library) touching UI/navigation | none (no `Purchases.configure()`) | `./gradlew connectedDebugAndroidTest` |
| **External (instrumented, real RevenueCat)** | ✅ built | event-driven: before pushing a major update to the Play Store, not a calendar cadence; also diff-driven whenever a Major change touches boundary-calling code (`RevenueCatManager.kt`) | real, bounded, dedicated test customer (`weekly-test-user`) | `.\test-weekly.ps1` |

(Command names — `test-weekly.ps1` etc. — are unrenamed this pass; see
`ARCHIVE_TESTING.md` for the full narrative on the deferred mechanical
rename.)

The Major-suite instrumented category runs with `CustomTestRunner`
(`android/app/src/androidTest/java/com/rigcheck/app/CustomTestRunner.kt`),
which substitutes a plain `Application` for the real `RigCheckApplication`
so `Purchases.configure()` never runs — confirmed via a full test run
with `adb logcat` showing zero `[Purchases]` SDK log lines. Wired via
`testInstrumentationRunner` in `app/build.gradle.kts`. This is why
`RigCheckViewModel`'s credit balance and `PaywallScreen`'s offerings both
render their "not yet loaded"/error states in these tests rather than
real data — both call sites are already wrapped in `runCatching`, so an
unconfigured `Purchases.sharedInstance` fails gracefully instead of
crashing (no production-code change was needed to make this possible).

**Built and verified for real 2026-08-23** (`.\test-weekly.ps1` → `OK (3
tests)`, real network throughout), using the dedicated `weekly-test-user`
RevenueCat test customer (see `workers/scan-proxy/TESTING.md` for how it
was created). Uses the *same* `CustomTestRunner` as the Major suite, not a
second runner — AGP's manifest merger only allows one `<instrumentation>`
element per test APK, so a separately-named runner class silently loses
its identity when merged. Instead, `test-weekly.ps1` touches a
device-side marker file
(`/data/local/tmp/rigcheck_weekly_mode`) before invoking `am instrument`;
`CustomTestRunner.newApplication()` checks for that file (plain
synchronous `java.io.File.exists()` — no lifecycle-ordering dependency)
and substitutes `WeeklyTestApplication` (real `Purchases.configure()`
against `weekly-test-user`) instead of the Major suite's plain offline
`Application`. The marker is removed again afterward so a later
`./gradlew connectedDebugAndroidTest` run is unaffected either way; that
Gradle task also explicitly excludes `PaywallScreenWeeklyTest` via
`testInstrumentationRunnerArguments["notClass"]` in
`app/build.gradle.kts`, since JUnit otherwise discovers every `@Test`
class in the `androidTest` source set regardless of which category "owns"
it. Full narrative of the three approaches tried before this one worked
— including an instrumentation-args race and a main-thread requirement
for triggering the real purchase dialog — in `ARCHIVE_ANDROID.md`.

`PaywallScreenWeeklyTest.kt` covers: `PaywallScreen` rendering real Test
Store offerings/prices, a real purchase completing and incrementing the
balance (this is also the *only* place in the whole test suite that can
exercise a real purchase at all — RevenueCat's REST API has no "simulate
a purchase" endpoint, only the SDK talking to real platform billing can
do that, so any account-balance top-up via a real purchase has to happen
here, not in any scan-proxy test), a real scan against the deployed
Worker (using a copy of `ExampleDocs/AddieTag.jpg` at
`android/app/src/androidTest/assets/AddieTag.jpg`) decrementing it by
exactly 1, and (added 2026-08-23, see `ARCHIVE_MONETIZATION.md`) two
real scans sharing one `client_request_id` decrementing it by exactly
1 total, not 2 —
proving the Worker's idempotency-key wiring actually dedupes against real
RevenueCat, not just fake deps. **Real cost per full run**: two real
~$0.01 Claude calls (the scan case and the duplicate-idempotency-key
case); the purchase case is free — RevenueCat's Test Store dialog states
outright it's a dev-only purchase, confirmed hands-on by triggering one
and reading its own text.

**Not the same test as `workers/scan-proxy`'s direct-provider-boundary
External suite, despite sharing a gating trigger** — discussed and
clarified 2026-08-21. Both should be gated on the same real-world event
(deciding to push a major update to the Play Store, not a calendar), but
they test different layers: scan-proxy's External suite validates the
Worker's own contract with RevenueCat/Anthropic directly, no Android app
involved at all; this suite validates the Android app's own real integration — UI rendering,
RevenueCat SDK behavior (including client-side caching quirks a pure API
test can't see, like the credit-balance-cache bug found 2026-08-18),
navigation — layers scan-proxy's tests are structurally unable to see.

**Recommended sequencing when a shared interface change needs both**:
run scan-proxy's real-boundary tests first — cheaper, faster, and far
easier to debug (a Node test's output and `wrangler tail` logs vs. an
emulator, Compose rendering, and device state). If those pass, move to
this suite; a real failure here is harder to isolate, but a passing
scan-proxy layer first meaningfully narrows where the bug can be. See
the root `TESTING.md`'s category 4 (inter-module interface tests) for
the general version of this rule.

## Coverage

Real JaCoCo coverage numbers for the Minor and Major suites, built and
verified for real 2026-08-23 — via AGP's own built-in support, no
third-party plugin. Enabled in `app/build.gradle.kts`'s `debug {}`
build type:

```kotlin
buildTypes {
    debug {
        testCoverage {
            enableUnitTestCoverage = true
            enableAndroidTestCoverage = true
        }
    }
    release { /* ... */ }
}
```

**Nested `testCoverage { }` block, not flat properties directly on
`debug { }`** — confirmed hands-on by running a real build; AGP 9.3.1's
docs pages for this are JS-rendered SPAs that don't return real content
to a plain fetch, so this had to be resolved empirically rather than
from research. Matches this file's existing AGP-9-style nested DSL
elsewhere (`compileSdk { version = release(37) }`,
`optimization { enable = false }`).

| Command | Real report path (confirmed 2026-08-23) |
|---|---|
| `./gradlew testDebugUnitTest createDebugUnitTestCoverageReport` | `app/build/reports/coverage/test/debug/index.html` |
| `./gradlew connectedDebugAndroidTest createDebugAndroidTestCoverageReport` | `app/build/reports/coverage/androidTest/debug/connected/index.html` |
| `./gradlew createDebugCoverageReport` | Runs both of the above — an aggregator task, not a separate merged report of its own (confirmed by checking the actual output directories; no third report path exists). |

Confirmed real, non-zero coverage on first run: Minor suite — 7% overall
instruction coverage app-wide (expected; Minor only exercises business
logic, not UI), `RevenueCatManager.kt` specifically at 38% (44 of 71
instructions missed), `com.rigcheck.app.domain` (the
`compute_breakdown`/`verdict_for` port) at 99%. Major suite — 71% overall
instruction coverage app-wide (much higher than Minor, as expected — it
exercises real Compose UI), `ResultsScreen.kt` at 100%. **This 71%
figure already excludes `com.rigcheck.app.ui.experiments.cameraoverlay`**
(the item #18 camera-overlay spike, isolated and unreachable from
production) — see `scripts/coverage_gate.py`'s `ANDROID_EXCLUDED_PACKAGES`
for the full mechanism/rationale; without the exclusion the raw number
reads 64.28%, a real distortion from spike code, not a real regression.

### Minor-vs-Major cross-reference for `ui.screens`/`.ui.components`/`.ui.navigation`

Real numbers, gathered 2026-09-09, closing the "not yet done" note that
used to sit in `NEXT_STEPS.md` item #8. Minor's 0% for all three
packages is exactly as expected (no unit test targets Compose UI
directly: `ui.screens` 0/7,095, `ui.components` 0/2,172, `ui.navigation`
0/1,226 instructions covered) — but Major already closed almost all of
that gap, and this same day's follow-up work closed the three remaining
per-class gaps for real (measured before/after, not estimated):

- **`com.rigcheck.app.ui.navigation` — 81% → 91%** (223/1,226 → 108/1,226
  missed). `RigCheckNavHostKt`: **80% → 90%** (223/1,140 → 108/1,140
  missed) — `RigCheckNavHostTest.kt` grew from 2 cases to 4: tapping
  "Scan Photo" with 0 credits (`onNeedCredits`) and tapping the credit
  chip (`onOpenPaywall`) each separately drive `RigCheckRoute.Paywall`
  for the first time, with the system back button confirmed (on a real
  device) to return cleanly to the Chooser screen it came from.
  **One real flake observed, not reproduced since**: on the first full
  4-test run, `creditChipTapOpensPaywallDirectlyAndBackReturnsToChooser`
  failed a `pressBack()` assertion once; the same 4 tests then passed
  cleanly on 3 immediate reruns with no code change. Left as-is —
  documented here rather than chased further, since it didn't reproduce.
- **`com.rigcheck.app.ui.components` — 89% → 97%** (238/2,172 → 53/2,172
  missed). `ReferenceImageCardKt`: **57% → 100%** (148/352 → 0/352
  missed); its pointer-input gesture lambda
  (`ReferenceImageCardKt$ReferenceImageCard$2$1`), previously a flat
  **0%**, is now **94%** (39/39 → 2/39 missed) — a new
  `ReferenceImageCardTest.kt` (this component's first dedicated test
  file) drives `onDragStart`/`onDrag`/`onDragEnd`/`onDragCancel` for
  real via `performTouchInput`, asserting on the composed node count (1
  child idle, 2 while the zoom overlay is shown) since the component has
  no callback outputs to hook. **Real test-writing surprise, confirmed
  by running it**: a bare long-press hold (`down()` +
  `advanceEventTime(700)`, no movement) never fires `onDragStart` —
  `detectDragGesturesAfterLongPress` needs a move *after* the hold
  before it starts the drag. Fixed the test (added a `moveTo()` after
  the hold), not the production code. The 2 remaining missed
  instructions in the gesture lambda weren't tracked down to a specific
  branch — a small, plausible edge (e.g. a pointer released or cancelled
  before the long-press timeout elapses) that these tests don't attempt.
- **`com.rigcheck.app.ui.screens` — 84% → 85%** (1,079/7,095 → 1,025/7,095
  missed). `PaywallScreenKt`: **45% → 51%** (469/859 → 417/859 missed) —
  `PaywallScreenTest.kt` grew from 3 cases to 7, all still using the same
  fakes/mocks style (no real RevenueCat): a `creditBalance = null` case
  (the `?: 0` elvis operator's null branch was never actually exercised
  by the existing 7/1/0 cases), and three cases actually tapping
  "Restore purchase" — success, failure, and a busy-then-reenabled
  interaction test that holds the fake `onRestore` callback open to
  observe the button's disabled state mid-flight. **Real test-writing
  surprise, confirmed by running it**: invoking the held-open callback
  directly from the test thread threw a real
  `NullPointerException: Can't toast on a thread that has not called
  Looper.prepare()` (`PaywallScreen`'s success branch calls
  `Toast.makeText`) — fixed by wrapping the invocation in
  `composeRule.runOnUiThread { }`, not a production bug. **The rest of
  this 51% was investigated and left open on purpose, not missed**: the
  offer-list rendering, the loading spinner, and the purchase-button
  states all require `PaywallScreen`'s own internal
  `RevenueCatManager.getOfferings()` call to actually return package
  data — there's no injection point to fake it from a test, so these
  paths genuinely need real RevenueCat and stay the External tier's job
  (`PaywallScreenWeeklyTest.kt`, untouched by this work), not something
  a fake/mock could reach here.

App-wide Major-suite instruction coverage: **71.00% → 73.50%**
(`uv run scripts/coverage_gate.py`, real, PASS against the 71.00%
baseline). Full suite counts after this work: Minor 38/38, Major 57/57 —
both green, nothing else regressed.

Both suites' existing plain commands (`./gradlew test`, `./gradlew
connectedDebugAndroidTest`, no coverage tasks) are unaffected — this is
purely additive, reconfirmed at 31/31 and 39/39 respectively after
adding the flags. If any covered test fails, AGP correctly skips
generating that report rather than producing a partial one — the right
failure mode if this is ever seen, not a tooling bug.

**External-suite coverage is a deliberately deferred, documented
nice-to-have — not built.** Its marginal contribution is small
(Major/Minor already exercise most of the same non-network code paths
its own screens touch), and getting a `.ec` file out of a bare `adb
shell am instrument` invocation into AGP's report task isn't guaranteed
to plug in cleanly without its own separate investigation. Fallback
shape for whenever this is picked up: add `-e coverage true -e
coverageFile <device-path>` to `test-weekly.ps1`'s `adb shell am
instrument` line, `adb pull` the resulting `.ec` file, then either the
JaCoCo CLI directly or a small custom `JacocoReport` Gradle task pointed
at the pulled file.

**These Major-suite numbers (71% app-wide) are the enforced baseline
`scripts/coverage_gate.py` checks Android against at release time** —
see the root `TESTING.md`'s "Coverage gate" section; the gate fails only
on regression below this real baseline, not an arbitrary target.

**Structured pass-rate reporting for the README dashboard** (roadmap
item #7, new 2026-08-24): needs no new flags or scripts — AGP already
writes real JUnit XML for both `./gradlew test`
(`app/build/test-results/testDebugUnitTest/*.xml`, one file per test
class) and `./gradlew connectedDebugAndroidTest`
(`app/build/outputs/androidTest-results/connected/debug/*.xml`) with
zero config. `scripts/generate_dashboard.py` just reads whichever of
these already exist, or runs the plain command to produce them — see the
root `TESTING.md`'s "Dashboard" section.

## What each test covers

### Minor (Unit, JVM) — `./gradlew test`

- `BreakdownTest.kt`, `VerdictTest.kt`, `NumberFormattingTest.kt` — the
  `compute_breakdown`/`verdict_for` Kotlin port, ported from
  `tests/test_breakdown.py` plus Android-only edge cases (see
  `ARCHIVE_ANDROID.md` at the repo root for detail).
- `BreakdownGoldenVectorTest.kt` — runs the shared
  `test-vectors/breakdown_cases.json` cases against this port, the same
  cases `tests/test_breakdown_golden_vectors.py` runs against Python (the
  source of truth). Cases needing a capability this port doesn't have yet
  are skipped, not silently passed — the test's own console output
  reports the count every run. See the root `TESTING.md`'s cross-platform
  section and `ARCHIVE_TESTING.md` (repo root) for what running this the
  first time found (several generations of drift, including a live bug
  this exact mechanism proved and then verified fixed).
- `RevenueCatManagerTest.kt` — the balance-cache-invalidation bug fixed
  2026-08-18: `getScanCreditBalance()` must call
  `invalidateVirtualCurrenciesCache()` before reading the balance, not
  after (asserted via `verifyOrder`); balance-present, balance-absent,
  and `appUserId`-passthrough cases. Uses MockK against
  `Purchases.Companion` and the real callback-based
  `getVirtualCurrencies(...)` method — see `ARCHIVE_ANDROID.md` (repo
  root) for the two MockK deadlocks hit and worked around while writing
  this.

### Major (instrumented) — `./gradlew connectedDebugAndroidTest`

**Screen-level tests** (`ui/screens/`, `ui/components/`) — fake
parameters passed directly to each composable, no ViewModel/NavHost/
network involved:

- `ResultsScreenTest` — all-passing renders "Safe to Tow", any failure
  renders "Not Safe to Tow"; row labels/percentages display correctly;
  all-insufficient renders "Not Enough Information", a mix renders
  "Partially Checked" (added 2026-08-21 alongside the `Tone.INSUFFICIENT`
  correctness fixes below). The `EstimatedFiguresNotice` (Android port of
  Web's `PredictiveEstimateNotice.tsx`) shows when any row is `estimated`,
  hidden otherwise.
- `BreakdownRowTest` — a row's note is hidden until tapped, then appears
  (the dynamic tongue-weight-explanation feature); a note-less row's tap
  is a no-op, doesn't crash; an insufficient row renders without crashing
  and shows 0%. A real bug was found manually verifying this on-device,
  not by this test: the progress bar's *track* color didn't follow
  `Tone.INSUFFICIENT`'s mauve, only the filled portion did — invisible on
  a normal row (mostly covered by the fill) but glaring on an insufficient
  row (always 0%, all track) — fixed by setting `trackColor` explicitly.
- `DisclaimerScreenTest` — the finalized disclaimer copy renders;
  tapping "I Understand, Continue" fires `onAcknowledge`.
- `RigPickerScreenTest` — a recent-rig card tap fires
  `onSelectRecentRig` with that rig; the "Create" button is disabled
  until a nickname is typed, then fires `onStartNewRig` with it.
- `TruckTagEntryScreenTest`, `TrailerTagEntryScreenTest`,
  `ScaleTicketEntryScreenTest` — typing into the description/location
  field updates the model and blank input becomes `null` (matching each
  screen's `.ifBlank { null }` logic); the Continue/Next button fires
  `onContinue`. One representative field is tagged per screen
  (`truck_description`, `trailer_description`, `scale_location`) rather
  than every field, proportionate to what's meaningfully different per
  screen — the underlying `LabeledTextField`/`LabeledNumberField`
  wiring is shared and identical everywhere it's used.
  `TruckTagEntryScreenTest` additionally covers the predictive-estimate
  section (added 2026-08-21): the pin-weight-% slider shows only when
  `standaloneWeightLb` is unknown, hides once it's known; the "Scan
  tow-vehicle-only ticket" button opens the same Take Photo/Choose from
  Gallery dialog as `ChooserScreen`; a scan error shows the error dialog
  and dismisses on OK.
- `ChooserScreenTest` — the credit chip shows the given balance; Scan
  Photo with credits opens the Take Photo/Choose from Gallery dialog
  (dialog presence and button existence only — no Espresso-Intents, real
  capture/picker flows stay covered by manual on-device testing); Scan
  Photo with 0 credits calls `onNeedCredits` instead; Enter Manually
  fires `onChooseManual`; a scan error shows the error dialog with its
  message and dismisses on OK.
- `CreditBalanceChipTest` — null shows the "…" not-yet-loaded
  placeholder; 0/1/5 use correct singular/plural wording; `onClick`
  fires when provided.
- `ReferenceImageCardTest` (added 2026-09-09, this component's first
  dedicated test file) — idle state shows only the base image (1 child);
  a long-press-and-hold followed by a move shows the zoom overlay (2
  children), a further move updates it, and release removes it; an
  interrupted gesture (`cancel()`) also removes it. Drives
  `detectDragGesturesAfterLongPress`'s `onDragStart`/`onDrag`/
  `onDragEnd`/`onDragCancel` for real via `performTouchInput`, since the
  component has no callback outputs to assert on directly.
- `PaywallScreenTest` — the credit-balance header text (singular/plural,
  including a `null` balance's `?: 0` fallback, added 2026-09-09), the
  offline "Couldn't load offers" error state (see the `Purchases` note
  above), the Restore Purchase link's presence, and (added 2026-09-09)
  actually tapping it: a success case, a failure case, and a
  busy-then-reenabled interaction test that holds the fake `onRestore`
  callback open to observe the button disable/re-enable. Real Test Store
  offerings/pricing, the loading spinner, and the purchase-button states
  all need `PaywallScreen`'s own internal `RevenueCatManager` call to
  return real package data (no injection point to fake it here) — that
  stays the External suite's job.

**Navigation-flow tests** (`ui/navigation/RigCheckNavHostTest.kt`) — the
real `RigCheckNavHost` + `RigCheckViewModel`, offline via
`CustomTestRunner`:

- Happy path: RigPicker → Chooser → Truck/Trailer/Scale entry (manual) →
  Disclaimer (first checkout) → Results.
- **Regression test for a real bug found during 2026-08-18 manual
  testing**: selecting an existing rig from `RigPickerScreen` used to
  navigate straight to `ScaleTicketEntryScreen`, skipping the
  Scan/Manual chooser entirely. Fixed in `RigCheckNavHost.kt`'s
  `onSelectRecentRig` to route through `Chooser(EntryModule.SCALE)`
  first. This test does a full checkout, goes back to `RigPicker`,
  selects the just-created recent rig, and asserts it lands on the
  Chooser (not the entry form directly) — and separately confirms the
  disclaimer does *not* reappear on this second checkout in the same
  session.
- **Added 2026-09-09**: two tests reaching `RigCheckRoute.Paywall` for
  the first time — tapping "Scan Photo" with 0 credits (`onNeedCredits`)
  and tapping the credit chip directly (`onOpenPaywall`), each a
  separate call site in `RigCheckNavHost.kt`. Both confirm the system
  back button returns to the Chooser screen it came from.

**Test-support tests** (`testsupport/`) — real-network-free coverage for
infrastructure the External suite below depends on:

- `ScanFixturePoolTest.kt` — `ScanFixturePool`'s directory-convention
  discovery (item #13's Android pass-pool/fail-pool, mirroring
  `scripts/vehicle_discovery.py`'s design), tested against a fake
  in-memory `FixtureFileSource` rather than a real `AssetManager`. Covers
  discovering a pass-pool vehicle's `fields`, a fail-pool vehicle's
  `expected_none_fields`, that pass-pool and fail-pool vehicles for the
  *same* doc_type stay in separate pools (a real bug caught while writing
  this — an earlier version mixed them under one map keyed only by
  doc_type, so a random pick could land on either pool regardless of
  which one the caller wanted), and fail-loud errors on a malformed
  sidecar or an image-less vehicle folder.

### External (instrumented, real RevenueCat) — `.\test-weekly.ps1`

- `PaywallScreenWeeklyTest.kt` — six cases, run under the same
  `CustomTestRunner` as the Major suite but with the weekly marker file
  set (`weekly-test-user`) — see the category description above:
  - `rendersRealOfferingsFromTestStore` — fetches the real package
    directly via `RevenueCatManager.getOfferings()` first (so the
    assertion checks a concrete known value, not a guess about UI
    internals), then confirms `PaywallScreen` renders that real
    `pkg.product.title`/`price.formatted` text instead of the Major
    suite's "Couldn't load offers" error state.
  - `realPurchaseIncrementsBalance` — calls
    `RevenueCatManager.purchasePackage`/`getScanCreditBalance()`
    directly (not through the Compose button — the Major suite's
    fake-lambda `PaywallScreenTest.kt` already covers that the button
    wiring itself works; this test's value is the real network round
    trip), launched on `Dispatchers.Main` specifically — calling it from
    the instrumentation thread never triggered RevenueCat's Test Store
    confirmation dialog at all, confirmed hands-on (real button taps
    always run on main; a background-thread call silently never opened
    it, even with a 25s wait). Drives that native (non-Compose)
    `AlertDialog` via `UiDevice`/`UiAutomator`
    (`android:id/button1` — standard resource-id, screenshotted and
    confirmed hands-on before writing this). Asserts the balance
    increased, not a hardcoded amount, since the exact grant depends on
    the Test Store package's current config.
  - `realScanDecrementsBalance` — reads
    `android/app/src/androidTest/assets/AddieTag.jpg` (a copy of
    `ExampleDocs/AddieTag.jpg`), base64-encodes it directly (no need to
    route through `PhotoEncoding.kt`'s Uri/downscaling path — that
    path's own logic isn't what this test verifies), calls
    `ScanApiClient.scan(...)` directly against the deployed Worker,
    asserts a `ScanResult.Success` with non-empty fields, then asserts
    the balance dropped by exactly 1.
  - `realDuplicateScanWithSameClientRequestIdSpendsOnce` — calls
    `ScanApiClient.scan(...)` twice with the same explicit
    `clientRequestId`, asserts both succeed, then asserts the balance
    dropped by exactly 1 total (not 2) — the hands-on proof for Gap B,
    run once against the not-yet-redeployed Worker
    first (genuinely failed, 2 deductions — confirmed the fix needed a
    real `wrangler deploy`, not just a local code change) and again
    after deploying (passed for real). Full narrative in
    `ARCHIVE_MONETIZATION.md`.
  - `scanPassPoolRandomPickMatchesGoldenFields` /
    `scanFailPoolRandomPickReturnsNullForMissingFields` — item #13's
    Android pass-pool/fail-pool
    (`FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md`). Unlike
    `realScanDecrementsBalance` above, these resolve a random real photo
    per pool via `ScanFixturePool` (new test-support module,
    `android/app/src/androidTest/java/com/rigcheck/app/testsupport/`,
    directory-discovered from `androidTest/assets/scans/<bucket>/
    <vehicle_slug>/vehicle.json` — same schema as
    `scripts/vehicle_discovery.py` on the Python side), route it through
    the *real* `encodePhotoForScan()` resize/compress path
    (`PhotoEncoding.kt` — deliberately not bypassed, unlike
    `realScanDecrementsBalance`), and check real extracted field values
    against documented golden data rather than just "fields non-empty."
    Found a real bug immediately: the deployed Worker was pinned to
    `claude-haiku-4-5-20251001`, which returned confident,
    non-deterministic, wrong GVWR/GAWR values for both fixtures — fixed
    2026-08-25 by switching `claude.ts` to `claude-sonnet-5`, verified
    for real against both fixtures after redeploying. Full narrative in
    `ARCHIVE_MONETIZATION.md`. `ScanFixturePool` itself is TDD'd
    separately in `ScanFixturePoolTest.kt` (Major suite, fake
    `FixtureFileSource`, no real network) — see that file for the
    discovery-logic test cases.
  - Uses `createAndroidComposeRule<ComponentActivity>()`, not the Major
    suite's `createComposeRule()`, since `purchasePackage` needs a real
    `Activity` (`composeRule.activity`).

## Known gaps (deliberately not tested, or not yet)

- **Real camera/gallery intents** — `ChooserScreenTest` confirms the
  source-choice dialog appears and its options are present, not that
  tapping them dispatches the correct Android intent or that a real
  capture/pick completes. Low regression risk (well-understood platform
  API); real flows stay covered by manual on-device testing.
- **`android/app/src/androidTest/java/com/rigcheck/app/ExampleInstrumentedTest.kt`**
  — the unmodified AGP template test, left in place; harmless, not part
  of this suite's real coverage.
- ✅ **Predictive standalone-only truck-side estimate — implemented
  2026-08-21 ("Round 2").** Landed TDD-style: `predictive_truck_estimate`
  was added to `BreakdownGoldenVectorTest.kt`'s `SUPPORTED_CAPABILITIES`
  and `BreakdownTest.kt` gained a red case *before* `computeBreakdown`
  gained the branch itself; both went green with no changes to the tests
  once the branch (mirroring `breakdown.py`'s `elif have_standalone:`)
  landed. Golden vectors: 10/10 cases now fully supported, full parity
  with Python. The UI half landed alongside it: a `pinWeightPct` state on
  `RigCheckViewModel` (threaded into `computeBreakdown`), a "Scan
  tow-vehicle-only ticket" entry point + pin-weight-% slider on
  `TruckTagEntryScreen` (slider hidden once a stand-alone weight is
  known), and `EstimatedFiguresNotice` on `ResultsScreen` (Android port of
  Web's `PredictiveEstimateNotice.tsx`, shown whenever any row is
  `estimated` — a new `BreakdownItem.estimated` field, mirroring Python's
  `estimated`, added this round). Verified via `./gradlew
  testDebugUnitTest` (31/31), `connectedDebugAndroidTest` (39/39), and a
  full manual on-device walkthrough (truck-only standalone weight, no
  scale data at all) confirming the 8,500 lb predictive tow-vehicle total
  and the estimated-figures notice both render correctly.
