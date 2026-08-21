# Android testing

Mirrors `workers/scan-proxy/TESTING.md`'s structure and the same tiered
strategy: sanity/daily tiers are fully offline and mocked/faked;
weekly/release tiers make real, bounded external calls and are built
later. This file documents current state — see `NEXT_STEPS.md` for the
narrative history of how it got built and what bugs were found along the
way.

## Tiers

| Tier | Status | Cadence | Network calls | Command |
|---|---|---|---|---|
| **Unit (JVM)** | ✅ built | every commit | none | `./gradlew test` |
| **Daily (instrumented, offline)** | ✅ built | before every commit touching UI/navigation | none (no `Purchases.configure()`) | `./gradlew connectedDebugAndroidTest` |
| **Weekly (instrumented, real RevenueCat)** | not built | weekly / before an uncertain deploy | real, bounded, dedicated test customer | none yet |

The daily-equivalent instrumented tier runs with `CustomTestRunner`
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

The weekly tier is deliberately deferred, same trigger as
`workers/scan-proxy`'s own weekly tier: it needs a dedicated disposable
RevenueCat test customer (separate from `smoke-test-user`, which is
reserved for manual Android field testing). Once that exists, it would
cover: `PaywallScreen` rendering real Test Store offerings/prices, a real
purchase completing and incrementing the balance, and a real scan
against the deployed Worker decrementing it.

## What each test covers

### Unit (JVM) — `./gradlew test`

- `BreakdownTest.kt`, `VerdictTest.kt`, `NumberFormattingTest.kt` — the
  `compute_breakdown`/`verdict_for` Kotlin port, ported from
  `tests/test_breakdown.py` plus Android-only edge cases (see
  `NEXT_STEPS.md` for detail).
- `BreakdownGoldenVectorTest.kt` — runs the shared
  `test-vectors/breakdown_cases.json` cases against this port, the same
  cases `tests/test_breakdown_golden_vectors.py` runs against Python (the
  source of truth). Cases needing a capability this port doesn't have yet
  are skipped, not silently passed — the test's own console output
  reports the count every run. See the root `TESTING.md`'s cross-platform
  section and `NEXT_STEPS.md` for what running this the first time found
  (several generations of drift, including a live bug this exact
  mechanism proved and then verified fixed).
- `RevenueCatManagerTest.kt` — the balance-cache-invalidation bug fixed
  2026-08-18: `getScanCreditBalance()` must call
  `invalidateVirtualCurrenciesCache()` before reading the balance, not
  after (asserted via `verifyOrder`); balance-present, balance-absent,
  and `appUserId`-passthrough cases. Uses MockK against
  `Purchases.Companion` and the real callback-based
  `getVirtualCurrencies(...)` method — see `NEXT_STEPS.md` for the two
  MockK deadlocks hit and worked around while writing this.

### Daily (instrumented) — `./gradlew connectedDebugAndroidTest`

**Screen-level tests** (`ui/screens/`, `ui/components/`) — fake
parameters passed directly to each composable, no ViewModel/NavHost/
network involved:

- `ResultsScreenTest` — all-passing renders "Safe to Tow", any failure
  renders "Not Safe to Tow"; row labels/percentages display correctly;
  all-insufficient renders "Not Enough Information", a mix renders
  "Partially Checked" (added 2026-08-21 alongside the `Tone.INSUFFICIENT`
  correctness fixes below).
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
- `PaywallScreenTest` — the credit-balance header text (singular/plural),
  the offline "Couldn't load offers" error state (see the `Purchases`
  note above), and the Restore Purchase link's presence. Real Test Store
  offerings/pricing is the weekly tier.

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

## Known gaps (deliberately not tested, or not yet)

- **Real camera/gallery intents** — `ChooserScreenTest` confirms the
  source-choice dialog appears and its options are present, not that
  tapping them dispatches the correct Android intent or that a real
  capture/pick completes. Low regression risk (well-understood platform
  API); real flows stay covered by manual on-device testing.
- **Real RevenueCat integration** (Paywall real offerings/pricing, a
  real purchase, a real scan against the deployed Worker) — the weekly
  tier above, deferred until the dedicated test customer exists.
- **`android/app/src/androidTest/java/com/rigcheck/app/ExampleInstrumentedTest.kt`**
  — the unmodified AGP template test, left in place; harmless, not part
  of this suite's real coverage.
- **Predictive standalone-only truck-side estimate** — the one remaining
  capability the Kotlin port doesn't have yet ("Round 2" in
  `NEXT_STEPS.md`). **Deliberately red as of 2026-08-21, not skipped**:
  `predictive_truck_estimate` was added to `BreakdownGoldenVectorTest.kt`'s
  `SUPPORTED_CAPABILITIES` and `BreakdownTest.kt` gained a new case
  (`tow vehicle total estimates from standalone weight when no hitched
  reading exists`) *before* `computeBreakdown` gained the branch itself —
  both currently fail with clean, informative diffs (not crashes/compile
  errors), TDD-style: tests written and landed first, against an
  already-agreed spec (Python's existing behavior), implementation to
  follow. `./gradlew testDebugUnitTest`: 31 tests, exactly these 2 fail.
