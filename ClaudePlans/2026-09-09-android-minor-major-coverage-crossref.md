# Document the Android Minor-vs-Major coverage cross-reference (item #8)

## Context

`NEXT_STEPS.md` item #8 flagged that Android's `ui.screens`/`.ui.components`/
`.ui.navigation` packages show a misleading 0% instruction coverage under
the Minor (JVM unit test) suite — expected, since no unit test targets
Compose UI directly — with a "not yet done" note to cross-reference
against the Major (instrumented) suite's real coverage before concluding
whether a genuine gap exists. That analysis is now done for real (via a
research pass against the actual, fresh JaCoCo reports on disk), and per
your scope choice, this plan is documentation-only: write the real
findings into the two files that currently carry stale/incomplete
information, so a future session doesn't need to re-derive this. Closing
the three real gaps this analysis found (`PaywallScreenKt`,
`ReferenceImageCardKt`, `RigCheckNavHostKt`) is explicitly deferred to
later, separate work — this plan only documents that they exist.

## Real findings to write in (already gathered, not to be re-derived)

**The premise holds, but Major already closes most of the gap.** Minor's
package-level totals confirm exactly 0% for all three packages (7,095/
7,095, 2,172/2,172, 1,226/1,226 instructions missed). Major's real,
fresh numbers (JaCoCo report at
`android/app/build/reports/coverage/androidTest/debug/connected/`,
generated today) tell a very different story:

- `com.rigcheck.app.ui.screens` — **84%** (1,079/7,095 missed). 18
  classes; all but one are 83%+. The one real gap: **`PaywallScreenKt`
  at 45%** (469/859 missed) — only `PaywallScreenTest.kt`'s 3 cases
  (null-balance placeholder, offline error, restore-link presence)
  exercise it directly; `PaywallScreenWeeklyTest.kt` (real Test Store
  purchase flow) is excluded from Major entirely via
  `build.gradle.kts`'s `testInstrumentationRunnerArguments["notClass"]`
  and belongs to the separate External suite — so part of this "gap" is
  deliberately tested elsewhere, not simply missing, but that
  distinction isn't visible from the number alone.
- `com.rigcheck.app.ui.components` — **89%** (238/2,172 missed). 7
  classes; 5 are 94%+ (several with no dedicated test file at all,
  covered only incidentally through the screens that render them — e.g.
  `LabeledFieldsKt` via every entry-screen test, `ScanOrManualChooserKt`
  via `ChooserScreenTest`). The one real gap: **`ReferenceImageCardKt`
  at 57%** (148/352 missed), plus its pointer-input gesture lambda
  (`ReferenceImageCardKt$ReferenceImageCard$2$1`) at a flat **0%**
  (39/39 missed) — no dedicated test file exists for this component at
  all.
- `com.rigcheck.app.ui.navigation` — **81%** (223/1,226 missed). 11
  classes (mostly trivial route/sealed-class boilerplate at 100%). The
  one real gap: **`RigCheckNavHostKt` at 80%** (223/1,140 missed) — the
  single largest raw missed-instruction count found anywhere in this
  analysis. Only `RigCheckNavHostTest.kt`'s 2 cases exist (the full
  happy-path route, and the 2026-08-18 `onSelectRecentRig` regression
  test) — real navigation logic this project has already been bitten by
  a real bug in once.

**A separate, real documentation gap found along the way**: `TESTING.md`'s
Coverage section states Android's Major baseline as a flat "71% overall
instruction coverage app-wide" without noting that this figure already
excludes `com.rigcheck.app.ui.experiments.cameraoverlay` (the camera-
overlay spike, item #18) — that exclusion and its full rationale
currently live only in `scripts/coverage_gate.py`'s
`ANDROID_EXCLUDED_PACKAGES` comment, not in `TESTING.md` itself. Worth a
one-line fix here since it's directly adjacent context found during this
exact investigation.

## Steps

1. **`android/TESTING.md`'s Coverage section**: after the existing "Major
   suite — 71%... `ResultsScreen.kt` at 100%" sentence, add:
   - A one-line note that the 71% figure excludes
     `ui.experiments.cameraoverlay` (link to `coverage_gate.py`'s
     `ANDROID_EXCLUDED_PACKAGES` for the full reason, don't duplicate
     the whole rationale here).
   - A new subsection documenting the Minor-vs-Major cross-reference for
     `ui.screens`/`.ui.components`/`.ui.navigation`: the real per-package
     Major percentages above, and the three real remaining gaps
     (`PaywallScreenKt`, `ReferenceImageCardKt`, `RigCheckNavHostKt`)
     each with its real number and a one-sentence "why" (test-file
     inventory finding, not speculation).
2. **`NEXT_STEPS.md` item #8's Android bullet**: replace the existing
   "real remaining headroom is whichever of those packages isn't already
   well covered by the Major suite's 30 instrumented tests once both
   numbers are compared side by side, not yet done" sentence with the
   real finding — point at `android/TESTING.md`'s new subsection for the
   full breakdown rather than duplicating all the numbers inline, and
   explicitly list the three real gaps as legitimate, not-yet-started
   future work so they aren't lost once this "not yet done" phrasing is
   replaced.
3. **Note the `PaywallScreenWeeklyTest.kt` documentation gap**: confirm
   whether `TESTING.md`'s existing "what each test covers" listing
   already omits it (the research pass found it does) — if so, this
   plan's step 1 edit should make that exclusion explicit in the new
   subsection's `PaywallScreenKt` note, so a future reader isn't
   surprised the number looks low despite that test file existing.

No code changes, no new tests — this plan only edits the two markdown
files named above.

## Definition of Done

- `android/TESTING.md`'s Coverage section states real per-package Major
  percentages for all three packages, and identifies the three real gaps
  by class name, real percentage, and a real (not speculative) reason —
  sufficient for a future session to act on them without re-running this
  analysis.
- `NEXT_STEPS.md` item #8 no longer contains the stale "not yet done"
  sentence for this specific cross-reference; it states the real finding
  and points at `TESTING.md` for detail, with the three gaps explicitly
  flagged as open future work.
- Every number/claim written into either file traces exactly to a real
  figure already gathered in this analysis — nothing rounded or guessed
  beyond what's confirmed above.

## Verification

- Re-read both edited files after writing and diff each new claim
  against the "Real findings" section above line by line to confirm
  nothing was transcribed incorrectly.
- `grep -n "not yet done"` (and similar stale phrasing) across both files
  afterward to confirm the specific sentence this plan targets is fully
  replaced, not just supplemented alongside the old text.
