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

## Running tests

| Level | Command |
|---|---|
| One file | `./gradlew testDebugUnitTest --tests com.rigcheck.app.domain.BreakdownTest` (run from `android/`) |
| Whole context (JVM, no device) | `./gradlew testDebugUnitTest` |
| Full release | `.\release.ps1` (run from `android/`) |

From PowerShell use `.\gradlew` (or `gradlew.bat`) instead of `./gradlew`.
Both run the JVM unit tests only; no emulator or device is needed. Device
tests (`connectedDebugAndroidTest`) and the weekly External suite are never
part of either command. A command check
(`tests/test_context_test_commands.py`, #52) reads Gradle's dry-run task
graph and confirms no device task is in it.

### Release run (#63)

`.\release.ps1` is the one command for a Play Store push: it runs the JVM
suite, the instrumented suite on an attached device, the stale surfaces in
Android's chain (including the Worker's, since the old weekly suite below
depends on a freshly deployed Worker) and the old weekly suite, in that
order, stopping on the first failure. A missing device or emulator
(`adb devices` reports none) fails the run outright — it is never silently
skipped. The old weekly suite both redeploys the Worker and makes two real
Claude calls, so it asks the owner to confirm (naming both) before it runs
and counts against a shared paid-call budget
(`scripts/paid_call_budget.py`, the same module the Worker's own
`workers/scan-proxy/release.ps1` uses) declared with `-MaxPaidCalls`
(default 2); a confirmation that would
exceed the budget aborts the run instead of spending further. The step
order, the missing-device failure and the confirmation/counting/abort
behaviour are unit-tested with a fake runner and a fake device list in
`tests/test_android_release.py` and `tests/test_paid_call_budget.py` — no
real device, deploy or network call happens in those tests.

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
  **One real flake observed here, explained in #125**: on the first full
  4-test run, `creditChipTapOpensPaywallDirectlyAndBackReturnsToChooser`
  failed a `pressBack()` assertion once; the same 4 tests then passed
  cleanly on 3 immediate reruns with no code change. Cause and fix: see
  "Why the nav tests flaked (#125)" under *Navigation-flow tests* below.
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

**External-suite coverage is now built and real, 2026-09-09** — the
"marginal contribution is small" assumption above turned out wrong for
`PaywallScreenKt` specifically, and real numbers now contradict it (see
`ClaudePlans/2026-09-09-merge-external-tier-coverage-paywallscreen.md`
for the full mechanism). `test-weekly.ps1`'s `adb shell am instrument`
call now passes `-e coverage true -e coverageFile
/data/data/com.rigcheck.app/coverage-external.ec` (app-private storage —
`/sdcard` and the app's own external-files dir were tried first and
confirmed hands-on to silently fail to write under this app's scoped-
storage config) and pulls the result via `run-as` + `adb exec-out`
piped through `cmd /c ... >`, not PowerShell's own redirection —
confirmed hands-on that PowerShell's native `>`/`Set-Content` corrupts
binary stdout (a spurious UTF-8 BOM, non-UTF8 bytes replaced with
U+FFFD), while `cmd.exe`'s redirection round-trips it byte-for-byte.
`android/app/build.gradle.kts` applies the plain Gradle `jacoco` plugin
fresh (AGP's own `testCoverage` block only wires its internal,
non-extensible `JacocoReportTask`) and defines
`jacocoMergedCoverageReport`, a real `JacocoReport` task that merges
Major's `coverage.ec` with External's pulled one against the same
non-instrumented compiled-classes/source dirs AGP's own report reads
from. **Verified structurally for free first**: merging Major's own
`.ec` with a byte-identical copy of itself round-tripped to the exact
same percentage as Major alone (66.4773% app-wide, unfiltered) before
the real External run was ever spent. **Real merged result,
`PaywallScreenKt`: 51% → 86%** (417/859 → 116/859 missed instructions —
same 859-instruction total as the Major-only report, confirming the two
reports' class/source inputs genuinely match) — confirming the
RevenueCat-dependent paths (offer-list rendering, the loading spinner,
purchase-button states) really were the rest of this class's gap.
**App-wide Major+External merged: 73.50% → 78.38%** (excluding the
camera-overlay spike, same exclusion as the Major-only number above;
70.83% unfiltered). This second number is informational only —
`scripts/coverage_gate.py`'s `get_android_merged_result()` returns it as
a `PlatformResult(gated=False, baseline=None)`; like the Major number, it
gates nothing (see "What gates the release" below).

### What gates the release (changed in #130)

**The Android coverage gate is a JVM floor on decision logic.** The
device-based Major numbers above (71% and later 73.5% app-wide) no longer
gate anything; they and the Major+External merged number stay as
informational numbers that `scripts/coverage_gate.py` prints.

`scripts/coverage_gate.py` instead reads the JVM report from
`./gradlew testDebugUnitTest createDebugUnitTestCoverageReport` (about
20 s, no device) and fails below **95.0%** aggregate instruction coverage
over the classes listed in `coverage-logic.toml` in this directory — the
Breakdown and Verdict math, Scan rules, field mapping and account rules,
where an untested branch is a real risk. It was about 97% when set
(2026-10-18). The same file lists the classes that are deliberately not
measured, each with a one-line reason.

**Compose screens, navigation, view-model wiring and provider wrappers
have no coverage number.** Device tests (Major) and External tests verify
them. A class in `domain`, `data` or `ui` that is on neither list is
printed as *unclassified* (a warning); an allow-listed class missing from
the report fails the gate. Add a new decision-logic class to `allow`, or
waive it with a reason. See the root `TESTING.md`'s "Coverage gate"
section.

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
  cases `tests/test_breakdown_golden_vectors.py` runs against Python (the fixture,
  not Python, is the source of truth). A case needing a capability this port doesn't
  have fails (it is never skipped), and notes, badges, headline and subline are
  asserted too (`note_android` overrides `note` for the two rows Android words
  differently; the badge is compared for checked rows only). See the root `TESTING.md`'s cross-platform
  section and `ARCHIVE_TESTING.md` (repo root) for what running this the
  first time found (several generations of drift, including a live bug
  this exact mechanism proved and then verified fixed).
- `RevenueCatManagerTest.kt` — the balance-cache-invalidation bug fixed
  2026-08-18: `getScanCreditBalance()` must call
  `invalidateVirtualCurrenciesCache()` before reading the balance, not
  after (asserted via `verifyOrder`); balance-present, balance-absent,
  and `isAnonymous`-passthrough cases. Uses MockK against
  `Purchases.Companion` and the real callback-based
  `getVirtualCurrencies(...)` method — see `ARCHIVE_ANDROID.md` (repo
  root) for the two MockK deadlocks hit and worked around while writing
  this.

- `AccountManagerTest.kt` (#22) — the Account ↔ RevenueCat link, with fake
  Supabase and RevenueCat behind `AccountBackend`/`BillingIdentity`: a
  restored or new session logs the account id in to RevenueCat once (not on
  token refresh), a different account replaces it, sign-out logs out only if
  an account was logged in, a failed RevenueCat login leaves the user signed
  in but not billing-linked until `ensureBillingLinked()` succeeds, and
  failures/exceptions become messages, not crashes.
- `GoogleSignInTest.kt` (#22) — the Google nonce (Supabase gets the raw
  nonce, Google its SHA-256 hex) and cancel/missing-account messages.
- `ScanApiClientTest.kt` (#22) — scan requests carry
  `Authorization: Bearer <account token>` and no `app_user_id`.
- `ScanHttpTest.kt` (#122) — how the Scan client reads the Worker's reply,
  against a MockWebServer (no live Worker, no network, no money): one test
  per Worker error code (`insufficient_credits`, `unauthorized`,
  `auth_unavailable`, `extraction_failed`, `extraction_failed_no_refund`,
  `billing_error`, `bad_request`) asserting the code and message returned; a
  dropped connection is `network_error`; an empty, non-JSON or non-object
  reply, an `ok` that is not a boolean and `fields` that is not an object are
  `parse_error`; a success returns its fields, or an empty set when there are
  none; `ok: false` with no code, or no `ok` at all, is a failure. Writing it
  found that the last two `parse_error` cases used to throw inside the OkHttp
  callback and leave the Scan waiting forever. (#117) A read that never
  answers, with a short read limit and a stalled fake server, is a `timeout`,
  not a `network_error`.
- `ScanFailureTest.kt` (#79, rewritten by #117) — what the user is shown, and
  which next steps the error dialog offers, when a Scan does not deliver, one
  test per case of `docs/research/scan-failure-handling.md` (R1 rows 1 to 8, 10,
  11, the sign-in gate and the stand-alone ticket's no-weight answer). The
  Worker's replies (401, 503, 402, 502 in its three forms, 400) and the
  client's own `network_error`, `parse_error` and `timeout` come from a
  MockWebServer through the real `ScanHttp`; `photo_unsendable` and
  `not_signed_in` from the constants the view model returns without a Worker.
  Each message is asserted as the literal words the user reads (whether a Scan
  Credit was used, whether it was refunded, whether a retry costs another, the
  next step), with the Worker's own text never shown. Try again is offered only
  after `auth_unavailable`, `extraction_failed`, `extraction_failed_no_refund`,
  `billing_error`, `network_error`, `parse_error` and `timeout`; a different
  photo after `bad_request` and `photo_unsendable`; typing it in or a different
  photo, and no Try again, after the no-weight answer; an unknown code claims
  nothing and offers nothing. Also drives `reportScanFailure`, the one function
  both of the view model's Scan entry points end in, with a fake show, a fake
  balance read and a fake balance set, to pin that after `insufficient_credits`
  the balance is set to 0 with no read, and after every other failure it is read
  again and never set.
- `ScanRetryTest.kt` (#117) — "Try again" sends the last Scan's photo again
  through the same entry point (a document's Scan or the stand-alone
  ticket's), over a fake Scan client and a real `ScanAttempts`: after a lost
  answer the retry carries the same photo and the same `client_request_id`,
  after a refunded failure a new id; with no Scan started it sends nothing; and
  it follows the latest Scan, not an earlier one.
- `ScanSessionTest.kt` (#118) — one Scan at a time per check, and what becomes
  of an answer for a check that has ended, over a delayed fake Scan client (each
  Scan waits on a `CompletableDeferred` the test completes, so the test decides
  what happens while it is in flight; no network): a second Scan while one is out
  does nothing and sends nothing; an answer for the check it started in is the
  current one and frees the lock; starting a rig, or showing another screen
  (leaving it, or moving on to the next screen of the same rig), sends the
  answer to `onGone` and never `onCurrent`; showing the same screen again (as
  after turning the device) ends nothing; the next check can scan while the old
  Scan is still out, and the old answer neither reaches it nor frees its lock;
  a late answer reaches `onGone` as it came, delivered or failed; the stand-alone
  ticket's screen follows the same rules; a Scan whose client throws frees the
  lock. `LateScanReportTest.kt` (#118) — what the user is told for a late answer
  (the "result wasn't used, it used a Scan Credit" sentence for a delivered
  Scan, the failure's own message with no next steps otherwise) and that the
  balance is read again, or set to 0 after `insufficient_credits`, as for a
  current Scan. The report is given no way to change the rig.

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
  (the dynamic pin-weight-explanation feature); a note-less row's tap
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
  Gallery dialog as `ChooserScreen` with a balance above zero, and (#79) calls
  `onNeedCredits` with none, or none loaded, instead of opening it; a scan
  error shows the error dialog and dismisses on OK, and (#79, #117) offers
  "Sign in", "Buy more Scans", "Try again" or "Choose a different photo" beside
  OK when the failure has that next step (and none otherwise): Try again is
  passed on, Choose a different photo closes the error and opens the Take
  Photo/Choose from Gallery dialog, and (#126) a rejected request, a photo
  that cannot be sent and the stand-alone ticket's no-weight answer each offer
  "Type it in" (closes the error and leaves the fields usable) and "Choose a
  different photo" with no Try again. `ChooserScreenTest` covers the same
  buttons on its dialog, where "Type it in" also opens manual entry (the
  Enter Manually callback) with no photo scanned and no step passed on.
- `ChooserScreenTest` — the credit chip shows the given balance; Scan
  Photo with credits opens the Take Photo/Choose from Gallery dialog
  (dialog presence and button existence only — no Espresso-Intents, real
  capture/picker flows stay covered by manual on-device testing); Scan
  Photo with 0 credits calls `onNeedCredits` instead; Enter Manually
  fires `onChooseManual`; a scan error shows the error dialog with its
  message and dismisses on OK, and (#117) a bad request or a photo that cannot
  be sent offers a different photo and not Try again, and a different photo with
  no Scans left goes to the paywall instead of the photo choice.
  (#118) With a Scan in flight the loading overlay absorbs taps: Enter Manually
  and Scan Photo under it do nothing. `TruckTagEntryScreenTest` (#118): the
  stand-alone ticket button is disabled while it reads and enabled otherwise.
- `LateScanDialogTest` (#118) — the dialog for a Scan that answered after its
  check ended shows its message with OK only (no Try again, Sign in or photo
  step), and OK dismisses.
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

- `AccountScreenTest` (#22) — the sign-in / create-account screen with fake
  callbacks: all three methods present, submit disabled until a valid
  email + password, sign-in vs sign-up wiring (trimmed email), failure and
  "check your email" messages, Apple's "finish in your browser" note, a
  cancelled chooser shows nothing, the form disables while a call is in
  flight, forgot-password, Not now.
- `PaywallScreenTest` also covers (#22) the "Buying for <account>" row and
  its Sign out button.

**Navigation-flow tests** (`ui/navigation/RigCheckNavHostTest.kt`) — the
real `RigCheckNavHost` + `RigCheckViewModel`, offline via
`CustomTestRunner`. Since #22 a signed-out visit to the Paywall route shows
the sign-in screen first (the two Paywall-entry tests assert that, and a
third checks "Not now" returns to the Chooser).

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
- **#79**: a signed-out tap on "Scan tow-vehicle-only ticket" lands on the
  sign-in screen with no photo source offered, and "Not now" returns to the
  Truck Tag form. (The tap used to open the camera and fail afterwards with a
  dead-end "Sign in to scan." dialog.)
- **Added 2026-09-09**: two tests reaching `RigCheckRoute.Paywall` for
  the first time — tapping "Scan Photo" with 0 credits (`onNeedCredits`)
  and tapping the credit chip directly (`onOpenPaywall`), each a
  separate call site in `RigCheckNavHost.kt`. Both confirm the system
  back button returns to the Chooser screen it came from.

**Why the nav tests flaked (#125).** `creditChipTapOpensPaywallDirectlyAndBackReturnsToChooser`
and its sibling `scanPhotoWithoutCreditsRoutesToPaywallAndBackReturnsToChooser`
failed with `'Truck Tag' ... is not displayed` on the line after `pressBack()`.
It was the test, not the app: **the injected Back never reached navigation,
the soft keyboard took it.**

- *What fails.* Every nav test types a nickname first. Typing focuses the
  field, which asks the IME to show the keyboard. On a freshly booted
  emulator Gboard is slow to start, and its window can appear 2-3 s after
  the request, after the test has already pressed Create and moved on. The
  app's own state says "keyboard hidden" until Gboard's window actually
  shows (the insets API and `closeSoftKeyboard()` both read it), so
  `closeSoftKeyboard()` does nothing, the late keyboard appears over the
  sign-in screen (a signed-out Paywall visit shows sign-in first, #22), and
  the Back press is spent closing it. The screen then stays on the sign-in
  screen (checked 3 s later: activity `RESUMED`, not finishing, still the
  sign-in texts).
- *Why only sometimes.* It depends on how slow the keyboard is that run:
  a warm emulator brings it up in under a second and never fails; right
  after a cold boot the first 5 class runs gave 3 passes, 1 failure of this
  kind and 1 emulator crash. (A temporary diagnostic probe that dumped the
  screen before Back made the single test fail 6 of 6 cold runs; the probe
  was removed and is not in the code.) So it hit full or multi-class runs
  on a fresh emulator, never a single test run on a warm one, which is the
  pattern #79, #116 and #117 saw. It still reproduced on `MPSkills` with
  #117's `goBack()` already in place (the first cold-boot loop ran exactly
  that code), so that change was not the whole story. The #117
  `goBack()` helper fixed the same family (Back with the keyboard visibly
  open) but could not fix this one, because here the keyboard is not yet
  visible when `closeSoftKeyboard()` runs.
- *What showed it.* Cold-booting the emulator before each run (the loop that
  turned the flake red), then `adb logcat`: `ImeTracker` shows the show
  request, then `closeSoftKeyboard` ending in `PHASE_CLIENT_ALREADY_HIDDEN`,
  then the key event, then Gboard's `onWindowShown` about 100 ms *after* the
  Back and an `ImeTracker ... HIDE_SOFT_INPUT_REQUEST_HIDE_WITH_CONTROL
  fromUser true` (the keyboard handling Back). Adding a 6 s sleep before
  Back made the test pass 4 of 4 cold runs, which confirmed the cause.
- *The fix.* `enterNickname()` in the test: type, wait until the keyboard is
  really visible, close it, wait until it is really gone. Back then always
  means "go back". Use it in any nav test that types and later presses Back
  (it is used for every nickname entry in the class, since a show request can
  be in flight after any of them). It assumes the emulator shows a soft
  keyboard: with a hardware keyboard attached or `show_ime_with_hard_keyboard`
  off, the keyboard never appears and `enterNickname()` fails after 30 s
  rather than passing silently.
  No assertion changed. After the fix: `RigCheckNavHostTest` passed 6 of 6
  cold-boot runs and 10 of 10 warm runs, and the full offline suite (97
  tests) passed 5 of 5 runs, each after a cold emulator boot. Two things
  that do NOT work: `performTextReplacement`
  (it also focuses the field and shows the keyboard), and `closeSoftKeyboard()`
  alone.
- *Not this flake.* A run that dies mid-way with `INSTRUMENTATION_ABORTED`,
  `System has crashed` or `Can't find service: activity` is the emulator
  itself falling over (seen right after a cold boot with ANRs in Google
  apps). Read the failure text before counting a run.

**Scan-in-flight navigation tests** (`ui/navigation/ScanInFlightNavigationTest.kt`, #118)
— the real `MainActivity`, nav host and view model, with the view model's Scan
answered by the test through `RigCheckViewModel.scanSender` (null in the app), so a
Scan is held open and answered when the test chooses; no Worker, no Scan Credit,
offline like the rest of this suite. A second Scan while one is out sends
nothing; a Scan answered on the check it started in fills it and opens the entry
screen; one answered after **turning the device** (`scenario.recreate()`) still
opens the entry screen and keeps the app (it used to crash: the answer's callback
held the NavController of the destroyed activity, now the view model records the
delivered Scan and the live nav host navigates); one answered after **backing out
to the Rig Picker** or after **another rig was started** is not used (the rig's
data is unchanged, nothing opens) and the user is told in the late-Scan dialog;
the next check can scan while the old Scan is still out, and the old Scan's late
answer leaves the new check's loading state (`scanState` stays `Loading`) and
error state alone; leaving a check clears its loading state at once; a **late
failure** shows its own message with OK only (no Try again, no "Scan failed"
title). The **stand-alone ticket Scan** has its own tests on the Truck Tag
screen: a second tap sends nothing, an answer on that screen fills
`standaloneWeightLb`, and one answered after leaving the screen or starting
another rig is not written and is reported. The tests
fail without the change: breaking the rig-start signal, the screen-change signal
or the in-flight guard each turns several of them red. `enterNickname` here is the
#125 recipe (keyboard really closed before a Back).

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

- **The External suite can't authenticate its real scans yet (#22).** The
  Worker now needs an account token (#21); `testsupport/WeeklyAccessToken.kt`
  fails loudly until `test-weekly.ps1` signs in a funded Supabase test user
  and the suite buys against that account id instead of `weekly-test-user`.
  Not run.
- **Google sign-in is untested against the real provider.** The Supabase
  project had it disabled on 2026-10-07; `scripts/wizard_android_sign_in.sh`
  sets it up. Email sign-in against real Supabase is also not exercised by
  an automated Android test.
- **Apple sign-in is built but hidden** (`APPLE_SIGN_IN_ENABLED = false`) and
  untested against Apple; deferred to #77 with the iOS port.

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
