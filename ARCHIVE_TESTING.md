# Archive: testing-strategy and regression-tier history

Detailed narrative for how this project's testing methodology and
per-platform regression tiers were designed and built out, moved out of
`NEXT_STEPS.md` 2026-08-23 to keep that file's current-status section
cheap to read. Current status/roadmap lives in `NEXT_STEPS.md` — this
file is history, not a place to look for "what's next." The methodology
itself (Minor/Major categories, Sanity/Daily/Weekly/Release tiers) is
documented for actual day-to-day use in the root `TESTING.md` and each
platform's own `TESTING.md` — this file is *how those got built*, not a
substitute for reading them.

**Entry-tag convention** (for `Grep`-based lookup instead of reading this
whole file): entries lead with `✅ **Real bug`, `**Decided`, `**Design
correction`, or similar bold tags — grep for those to filter by type.

---

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
Two more gaps identified but **not yet closed at the time** (later closed
2026-08-22, see `NEXT_STEPS.md`'s roadmap item #1): the truck/trailer
OCR-output-keys-vs-schema contract, and the OCR-output-keys-vs-Streamlit's-
`FIELDS`-dict contract — both lower-risk (a mismatch shows up as a `None`
field, not silently wrong math, unlike the breakdown case). `uv run pytest
-q`: 75/75.

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
case — the live bug — was deliberately left unskipped per the user's
explicit call: it fails for real, `expected:<14225> but was:<11380>`, an
honest, reproducible proof the bug is live on the shipped Android app, not
just a missing feature. Confirmed via a real `./gradlew testDebugUnitTest`
run (not just `test`, which isn't a valid task name for this Android
module — use the variant-specific task). Full Android suite after: 22
tests, exactly that 1 expected failure, nothing else regressed.

**Deliberately not done as part of this**: fixing `Breakdown.kt` itself
(porting the missing features, fixing the live bug) — this was
infrastructure only, per the user's choice to build the mechanism before
doing the port. That's real, separate feature/bugfix work, done in the
Round 1/2 entries below.

**2026-08-21 (same day) — Round 1 correctness fixes done.** Per the
user's "correctness fixes first" call: `Breakdown.kt` now mirrors Python's
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

  **✅ Automated, 2026-08-23** (prompted by the user asking, after this
  gotcha bit a real run again during roadmap item #5's verification, "why
  isn't this just part of the test script?"). `android/app/build.gradle.kts`
  now has a `wakeEmulatorForInstrumentedTests` task (an `Exec` task -
  not a `doLast { project.exec {} }` block, which isn't
  configuration-cache-compatible) that `connectedDebugAndroidTest`
  `dependsOn`, resolving `adb` from `ANDROID_SDK_ROOT`/`ANDROID_HOME` or
  `local.properties`' `sdk.dir` and running the same wake + stay-awake
  commands automatically before every Daily-tier run, however it's
  invoked - a raw `./gradlew connectedDebugAndroidTest` is covered too,
  not just a wrapper script. `test-weekly.ps1` got the equivalent
  explicit step for its own raw `adb shell am instrument` invocation.
  Verified hands-on: wiring confirmed via `--dry-run` (task appears
  immediately before `connectedDebugAndroidTest` in the graph), then via
  a real run with zero "No compose hierarchies found" failures.

  **A second, unrelated failure mode found and fixed during that same
  verification pass**: after several consecutive full instrumented runs
  in one session, the emulator's `system_server` genuinely crashed
  (`INSTRUMENTATION_ABORTED: System has crashed`), and even after an
  in-place `adb reboot` recovered it, one specific test
  (`RigCheckNavHostTest.recentRigSelectionRoutesThroughTheChooserAndSkipsTheDisclaimerSecondTime`)
  kept failing with `RootViewWithoutFocusException` ("window focus" never
  granted) - a different signature from the screen-sleep one, so the new
  wake task alone didn't explain it. `adb shell dumpsys window | grep
  mCurrentFocus` showed why: the emulator's Pixel Launcher itself had
  ANR'd ("Pixel Launcher isn't responding"), and its own ANR dialog was
  holding window focus system-wide, starving every other window
  (confirmed visually via `adb exec-out screencap`). Dismissing it
  (`adb shell input tap` on "Close app") immediately restored normal
  focus and the test passed clean. Root cause of the crash/ANR itself
  was never pinned down precisely - most likely cumulative resource
  exhaustion from a long session of repeated full builds - and a full
  cold restart of the AVD (not just `adb reboot`) was what actually
  brought total suite runtime back from 27 minutes to under 2. Recorded
  here since "a test window loses focus and times out" is exactly the
  kind of failure that looks like a real bug but is actually emulator
  infrastructure state - check `dumpsys window`'s `mCurrentFocus` before
  assuming otherwise.
- Golden-vector status after Round 1: **8 of 10 cases fully supported**
  by the Kotlin port (was 4 of 9 before Round 1 — the standalone-zero fix
  above didn't change this count, it was caught by `BreakdownTest.kt`,
  not the golden vectors). The 2 still skipped both need
  `predictive_truck_estimate` — Round 2.

**2026-08-21 (same day) — Round 2 tests written and landed red, on
purpose.** Per the user's TDD request: wrote and committed the predictive
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

**2026-08-21 (same day) — ReviewStep/UploadStep/ResultsStep component
tests written, plus a real harness gotcha found and fixed.** New
`src/wizard/UploadStep.test.tsx` (8 cases), `src/wizard/ReviewStep.test.tsx`
(10 cases), `src/wizard/ResultsStep.test.tsx` (7 cases) — all fake props,
no `App`/network involved, the same Module category Android's screen-level
Compose tests (`ChooserScreenTest` etc.) already use. Notably:
`UploadStep`'s scale-vs-non-scale branch (the extra hint text, second
skip button, and first skip button's label swap) is exercised for the
first time; `ReviewStep`'s scan-loading ("Reading…", disabled) and
scan-error states are new coverage `App.interaction.test.tsx` never hit
(it only exercises the resolved-scan path); `ResultsStep`'s
estimated-figures-notice show/hide is new too, since
`App.interaction.test.tsx`'s `RESULT` fixture is always non-estimated.

**Real gotcha, found writing `UploadStep.test.tsx`**: React Testing
Library's automatic `afterEach(cleanup)` only self-registers when it
detects a global `afterEach` — this project's `vite.config.ts` doesn't
set `test.globals: true`, so without an explicit `cleanup()` call, every
test's render stayed mounted, and later tests in the same file matched
stale elements from earlier ones (`getByRole`/`getByText` "multiple
elements found" errors, not silent false-passes - the failure mode was
loud, just initially confusing). `App.interaction.test.tsx` had
already worked around this per-file with its own `afterEach(cleanup)`;
fixed properly this time by moving `afterEach(cleanup)` into
`src/setupTests.ts` once, and removed the now-redundant per-file copies.
`npm test`: 51/51 (was 25). `npm run build` still clean. This was the
last item on `web/TESTING.md`'s known-gaps list at the time — every gap
identified when the retrofit started 2026-08-21 was closed by this point.

**2026-08-21 (same day) — Minor/Major reconciled with the sanity/daily/
weekly/release tiers.** New "Reconciling with per-platform network/
cadence tiers" section in the root `TESTING.md`, cross-referenced from
`android/TESTING.md` and `workers/scan-proxy/TESTING.md`. Turned out not
to need a merge or a rewrite of either scheme — they're independent axes
answering different questions: Minor/Major decides *which test
categories* a specific change's diff calls for; sanity/daily/weekly/
release decides *which network-dependency tier* a test belongs to (and
how often that tier's real-world exposure runs at all), a property of the
test itself, not of any one session's diff. Minor/Major only ever governs
the already-offline tiers (Android's Unit+Daily, scan-proxy's
Sanity+Daily); the real-network tiers (Android's Weekly, scan-proxy's
Weekly/Release) sit outside Minor/Major entirely, on their own fixed
cadence regardless of what changed, since what they guard against - a
live integration/credential/environment failure - isn't something a
diff's scope can predict. This was the last item on the tiered-test-
strategy backlog; the framework itself (categories + Minor/Major scoping)
is now fully documented and reconciled across every platform's own
testing doc (`tests/TESTING.md`, `android/TESTING.md`,
`workers/scan-proxy/TESTING.md`, `web/TESTING.md`). Applying it as a
lived per-session discipline going forward remains ongoing, not a
one-time task - not "done," just no longer blocked on anything.

**2026-08-21 (same day) — web/ coverage audit against the reconciled
framework, a real duplicated bug found and fixed, four more component
tests written.** Went through every remaining untested file in
`web/src` against the four categories and found: `wizard/RigStep.tsx`
(the one wizard step left without a Module test, same shape as the three
just written), `screens/History.tsx` (zero coverage, direct or indirect
— no test anywhere even navigated to it), and `components/DisclaimerModal.tsx`
(one real callback, only exercised via the full App happy path).

**Real bug, not just a missing test**: auditing `History.tsx` surfaced
that it rendered any verdict other than a literal `'pass'` as "Over
Limit" with a warning badge — a `partial` or `insufficient` check
(missing data, not an actual over-limit reading) got the same alarming
mislabel as a genuine failure, and `App.tsx`'s `continueReview` genuinely
can push a partial/insufficient entry into history. The identical bug
was independently duplicated in `Dashboard.tsx`'s "Recent Checks" list.
Fixed TDD-style: `History.test.tsx` written first, confirmed red against
the live bug (two failing cases, `partial` and `insufficient` both
showing "Over Limit"), then fixed by extracting a shared
`src/verdictBadge.ts` (`VERDICT_BADGE` map: `pass`→"Safe to Tow"/success,
`fail`→"Over Limit"/warning, `partial`→"Partially Checked"/insufficient,
`insufficient`→"Not Enough Info"/insufficient) both files now read from,
so the same mislabeling can't drift independently in each file again.
Added a small `Dashboard.test.tsx` scoped to the same fix.

New test files: `wizard/RigStep.test.tsx` (7 cases — recent-rig
cards, the manufacturer-subtitle join and its omission, click dispatch,
disabled-until-non-blank *and* the nickname gets trimmed before reaching
`onStartNew`), `components/DisclaimerModal.test.tsx` (2 cases),
`screens/History.test.tsx` (6 cases, including the bug-fix regression),
`screens/Dashboard.test.tsx` (3 cases, the same fix). `npm test`: 69/69
(was 51). `npm run build` still clean.

**Flagged, not built at the time**: no test proves the hand-written JSON
fixtures used across this whole suite (`BreakdownItem`, `VerdictInfo`,
`TruckTagData`, every `mockFetchOk(...)` body) still match what the real
Python API returns — every web test mocks `fetch`/`./api`, so a real
field rename on the Python side would never surface here. Same risk
shape as the `estimated` field gap and `pin_weight_pct` fixture already
closed, but for the full response shapes generally. Recorded in
`web/TESTING.md`'s known gaps; partly closed by "Option B" below.
Also flagged and deliberately deferred: `Dashboard.tsx`'s own logic
beyond the verdict badge (the recent-rigs grid, its subtitle join, the
click targets) still has no dedicated Module test, only indirect
coverage via `App.interaction.test.tsx` — see `NEXT_STEPS.md`'s roadmap
item #7.

**2026-08-21 (same day) — the flagged API-shape-drift gap: a parked
"Option C" doc, and "Option B" implemented for the two highest-traffic
shapes.** Discussed three approaches for proving `web/`'s hand-written
fixtures (`BreakdownItem`, `VerdictInfo`, `TruckTagData`, etc.) still
match what the real Python API returns, since nothing did — every
`web/` test mocks `fetch`/`./api`. Chose to park the most thorough
option (a Pydantic `.model_json_schema()` export, validated against on
the Web side with `ajv`) rather than build it now, since it's more
machinery than the gap has earned yet: written up in a new root-level
`FUTURE_API_SCHEMA_VALIDATION.md` (requirements, open decisions, when to
actually pick it up), cross-referenced from `web/TESTING.md`'s known
gaps and the root `TESTING.md`'s cross-platform section, specifically so
it doesn't need to stay loaded in day-to-day context to not be lost.

Then built "Option B" for `BreakdownItemOut`/`VerdictOut` (the two
highest-traffic shapes, used across most of `web/`'s test fixtures): a
third shared key-list fixture,
`test-vectors/breakdown_response_shape_contract.json`, consumed by two
paired tests. `tests/test_api.py::test_breakdown_response_matches_the_shared_api_contract`
is the "ground truth" half — a real, unmocked `/api/breakdown` call
asserting the response's keys match the shared file exactly.
`web/src/apiShape.test.ts` is the "does our mirror still match" half —
doesn't touch a real response, just proves `types.ts`'s
`BreakdownItem`/`VerdictInfo` interfaces currently have exactly those
keys, via a typed object literal. TypeScript's excess-property checking
on that literal does real work: add a field to the interface without
updating the literal and the build fails (missing property) before the
test even runs; remove one without updating the literal and the build
fails too (excess property) — either way a human is forced to touch the
test file, whose own assertion then forces the shared contract (and the
paired Python test) to be updated in step. Not a fully-derived contract
(both sides can still drift if a human forgets to update the shared
file itself) but a real tripwire on both known-risky ends, the same
pattern that already worked for `pin_weight_pct`. `TruckTagOut`/
`TrailerTagOut`/`ScaleTicketOut` remain uncovered by this — extending
Option B to them would mean three more hand-maintained fixture files,
exactly the scaling problem Option C is written up to eventually solve.
`uv run pytest -q`: 88/88 (was 87). `npm test`: 71/71 (was 69). `npm run
build` still clean.

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
   per run and adds non-determinism. In practice, the Weekly/Release
   tiers built 2026-08-21/22 answered this with real, bounded, explicitly
   opt-in-cadence real calls rather than a blanket policy either way.
4. **Automation vs. checklist.** No CI exists anywhere in this repo (no
   GitHub Actions, nothing) as of 2026-08-23. The tiers are a documented
   checklist a human runs periodically, not CI — this hasn't been
   revisited since.
5. **One scheme across four different test runners, or four idiomatic
   ones.** pytest (backend/OCR/breakdown), `node --test` (scan-proxy
   Worker), Vitest (web, installed 2026-08-21), `AppTest` (Streamlit,
   since 2026-08-20) — resolved in practice as four idiomatic runners
   under one shared Minor/Major + tier framework, not one shared runner.
6. **The concrete, immediate gap regardless of how the above resolves**:
   `ExampleDocs/` real-photo verification only happened via manual ad-hoc
   runs for a long time. **Closed for the scale-ticket reader** 2026-08-20
   — see `ARCHIVE_WEB_STREAMLIT.md`'s "real tow-vehicle-only photo added"
   entry (found and fixed a real bug this exact gap was designed to
   catch). Truck tag and trailer tag readers still have no equivalent
   real-photo test as of 2026-08-23 — see `NEXT_STEPS.md`'s "Tests still
   outstanding" section.

## 📋 Backlog: regression-tier docs + a static CI/CD-style dashboard

Raised 2026-08-19, right after `scan-proxy`'s sanity/daily tiers were
built. Two related pieces:

1. ✅ **Document the regression tiers themselves — done for all
   platforms.** `workers/scan-proxy/TESTING.md`, `android/TESTING.md`,
   `tests/TESTING.md`, and `web/TESTING.md` all exist (built across
   2026-08-19 through 2026-08-21), same structure: tier table + what
   each individual test covers.
2. **A statically-generated report of regression run results** — not yet
   built as of 2026-08-23, see `NEXT_STEPS.md`'s roadmap item #7. The
   user's own framing: "something that looks similar to what a CI/CD
   dashboard might show, only statically generated in our case" — this
   repo has no CI, so this would be a script that runs a test tier and
   renders its results (pass/fail per test, per tier, maybe trended over
   time if run repeatedly) as a static HTML/Markdown page, run manually
   alongside the tiers themselves rather than triggered by CI.

**Open questions, not yet resolved:**
- Format/tooling for the dashboard: Node's built-in test runner supports
  a `--test-reporter` flag (e.g. `tap`, `junit`, `spec`) that could feed
  a small static-site generator step, vs. hand-rolling something simpler
  directly from `node --test`'s output.
- Where results get archived (if trended over time at all) — a
  git-committed file that updates each run, or explicitly ephemeral
  (regenerated fresh each time, never versioned)?

## 🧪 Tests still outstanding — historical detail (superseded items)

Everything below was originally tracked in `NEXT_STEPS.md`'s living
"Tests still outstanding" checklist and has since been either fully
completed or folded into that file's roadmap section — moved here
2026-08-23 as historical detail, not because it's still open. Check
`NEXT_STEPS.md`'s roadmap first for what's actually still open.

**Full rebuild + regression pass, all platforms — requested 2026-08-18,
fully done by 2026-08-19/22 across every platform:**

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
  `server.headless = true`) — see `NEXT_STEPS.md`'s "Fresh-machine setup
  checklist" for the do-this-first version of this note.
  **Correction, 2026-08-20 — the "AppTest hangs on Windows" finding above
  did not reproduce.** `tests/test_streamlit_app.py` drives
  `AppTest.from_file(...)` through a full multi-step wizard flow (rig
  creation → three skip clicks → three continues → disclaimer) on this
  same Windows machine, no hang, ~1s total for both tests. Root cause of
  the original hang was never re-identified (maybe a since-fixed
  Streamlit bug, maybe an environment difference that session) — but
  treat "`AppTest` is broken on Windows" as stale, not current fact.
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
  pass either way, not investigated further.
- **Session gotcha hit twice**: backgrounding a `uv run ...`/`streamlit
  run` process via `&` in git-bash and later `kill`-ing the *reported*
  job PID does not reliably kill the real underlying `python.exe`
  process — it can keep running orphaned, holding native `.dll`/`.pyd`
  files open and causing the *next* `uv sync` to fail with "Access is
  denied" trying to replace them. Fix each time: find and
  `Stop-Process -Force` the actual `python.exe` under this project's
  `.venv` path via PowerShell, not the bash-reported PID.
- ✅ **Android — done 2026-08-18**, as part of building Phase 3 (see
  `ARCHIVE_ANDROID.md`): `./gradlew test`/`assembleDebug` both clean,
  plus a full real on-device walkthrough well beyond what this checklist
  item originally asked for.
- ✅ **`workers/scan-proxy/` — sanity + daily tiers done 2026-08-19,
  Weekly + Release tiers done 2026-08-22 (see `NEXT_STEPS.md`'s roadmap
  items #2/#3).**

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
URL, before/after every `wrangler deploy`). Manual cadence, no CI.

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
  plus three new ones (one happy-path check per critical module) —
  `npm run test:sanity`, ~0.3s.
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
    field-name-contract gaps an architectural review surfaced — see git
    history for the full list; `docTypes.test.ts` now specifically
    asserts each doc type's schema still contains the exact field names
    `ScanFieldMapping.kt` on Android reads, which the older
    required-matches-properties test structurally couldn't catch.
  - Two gaps deliberately left as **documented current behavior, not
    fixed** as of this writing: `spendCredit`/`fetch` rejecting outright
    (not just returning a non-ok status) propagates as an unhandled
    rejection with no `try/catch` anywhere in the chain; there's no
    request-level idempotency across client retries (each `runScan` call
    mints its own key). Both are pinned down by tests explicitly
    documenting the behavior — see `NEXT_STEPS.md`'s roadmap item #5
    (still open as of 2026-08-23).
  - Total: **47 tests, all passing, `tsc --noEmit` clean.**

**2026-08-21 (same night) — design discussion: what's actually left for
Weekly/Release, and how the two platforms' real-network tiers relate.**
Worked through four design questions before building either tier for
real (both are now built — see `NEXT_STEPS.md`'s roadmap items #2/#3):

1. **The Test Store purchase, to make `weekly-test-user` self-
   sustaining.** Confirmed: yes, build it. Real technical constraint:
   RevenueCat's REST API has no "simulate a purchase" endpoint; only the
   SDK talking to real platform billing can complete one. So this piece
   can only live in Android's own weekly-equivalent test, not in any
   scan-proxy Node test — scan-proxy's real-scan-and-charge case just
   draws down whatever balance exists, replenished by Android's test
   running separately. Still true, still unbuilt on the Android side as
   of 2026-08-23 — see `NEXT_STEPS.md`'s roadmap item #4.
2. **A real OCR-failure/refund-path test** — resolved 2026-08-22, see
   `ARCHIVE_WEB_STREAMLIT.md`'s scan-proxy Weekly tier work (the WTWT-
   logo design correction).
3. **Release tier redesign** — proposed real API calls at the actual
   service-provider boundaries (RevenueCat, Anthropic directly, not
   mocks, not the deployed Worker as an intermediary), error conditions
   included, gated on deciding to push a major Play Store update rather
   than a calendar or `wrangler deploy`. Built 2026-08-22 — see
   `NEXT_STEPS.md`'s roadmap item #2.
4. **Is Android's Weekly-equivalent tier the same thing as scan-proxy's
   redesigned Release tier?** Clarified: same *gating trigger* (both
   should fire on "about to push a major update," not a clock). But
   different *content* — scan-proxy's Release tier validates the
   Worker's own contract with RevenueCat/Anthropic, no Android app
   involved; Android's tier validates the app's own real integration
   (UI, RevenueCat SDK behavior including client-side caching quirks a
   pure API test can't see — the credit-balance-cache bug found
   2026-08-18 is the concrete example — navigation). Two suites under one
   gating philosophy, not one test with two names.

**Also decided: a sequencing principle for when a shared-interface
change needs validating across both platforms** — run scan-proxy's real
boundary tests first (a Node process, precise HTTP-level failures,
`wrangler tail` for logs), and only proceed to Android's real-integration
tests if those pass. Doesn't make the Android layer optional (some real
bugs, like the balance-cache one, live entirely above what scan-proxy's
tests can see) — it narrows where a failure in the expensive, hard-to-
debug layer can be coming from. Documented in the root `TESTING.md`'s
category 4 — this is the one piece of this whole section still actively
governing day-to-day decisions, not just history.
