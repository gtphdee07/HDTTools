# Android testing

Mirrors `workers/scan-proxy/TESTING.md`'s structure and the same tiered
strategy: sanity/daily tiers are fully offline and mocked/faked;
weekly/release tiers make real, bounded external calls and are built
later. This file documents current state — see `ARCHIVE_ANDROID.md` (repo
root) for the narrative history of how it got built and what bugs were
found along the way. See the root `TESTING.md`'s "Reconciling with per-platform network/
cadence tiers" section for how this tiering relates to that file's
Minor/Major regression-scoping rules — the two are independent axes, not
alternatives to choose between.

## Tiers

| Tier | Status | Cadence | Network calls | Command |
|---|---|---|---|---|
| **Unit (JVM)** | ✅ built | every commit | none | `./gradlew test` |
| **Daily (instrumented, offline)** | ✅ built | before every commit touching UI/navigation | none (no `Purchases.configure()`) | `./gradlew connectedDebugAndroidTest` |
| **Weekly (instrumented, real RevenueCat)** | not built, blocker resolved | before pushing a major update to the Play Store, not a calendar cadence | real, bounded, dedicated test customer | none yet |

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

**The blocker is resolved (2026-08-21)** — `weekly-test-user` and
`weekly-test-user-no-credits` exist (see `workers/scan-proxy/TESTING.md`
for how they were created), usable from Android too, not just
scan-proxy's own Node tests. The test code itself is still not written.
Once built, it would cover: `PaywallScreen` rendering real Test Store
offerings/prices, a real purchase completing and incrementing the
balance (this is also the *only* place in the whole test suite that can
exercise a real purchase at all — RevenueCat's REST API has no
"simulate a purchase" endpoint, only the SDK talking to real platform
billing can do that, so any account-balance top-up via a real purchase
has to happen here, not in any scan-proxy test), and a real scan against
the deployed Worker decrementing it.

**Not the same test as `workers/scan-proxy`'s Release tier, despite
sharing a gating trigger** — discussed and clarified 2026-08-21. Both
should be gated on the same real-world event (deciding to push a major
update to the Play Store, not a calendar), but they test different
layers: scan-proxy's Release tier validates the Worker's own contract
with RevenueCat/Anthropic directly, no Android app involved at all; this
tier validates the Android app's own real integration — UI rendering,
RevenueCat SDK behavior (including client-side caching quirks a pure API
test can't see, like the credit-balance-cache bug found 2026-08-18),
navigation — layers scan-proxy's tests are structurally unable to see.

**Recommended sequencing when a shared interface change needs both**:
run scan-proxy's real-boundary tests first — cheaper, faster, and far
easier to debug (a Node test's output and `wrangler tail` logs vs. an
emulator, Compose rendering, and device state). If those pass, move to
this tier; a real failure here is harder to isolate, but a passing
scan-proxy layer first meaningfully narrows where the bug can be. See
the root `TESTING.md`'s category 4 (inter-module interface tests) for
the general version of this rule.

## What each test covers

### Unit (JVM) — `./gradlew test`

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

### Daily (instrumented) — `./gradlew connectedDebugAndroidTest`

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
