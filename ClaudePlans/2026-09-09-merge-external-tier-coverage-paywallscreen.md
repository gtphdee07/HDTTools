# Merge External-tier coverage into PaywallScreenKt's real number

## Context

Item #8's Android coverage sweep just closed three real gaps (item #8,
`NEXT_STEPS.md`/`android/TESTING.md`, 2026-09-09): `RigCheckNavHostKt`
80%→90%, `ReferenceImageCardKt` 57%→100%, `PaywallScreenKt` 45%→51%.
`PaywallScreenKt`'s remaining ~49% gap was investigated for real and
found to be specifically the code paths that need real RevenueCat data
(offer-list rendering, the loading spinner, purchase-button states) —
exactly what `PaywallScreenWeeklyTest.kt` (the External tier,
`test-weekly.ps1`, excluded from the Major suite entirely) already
exercises for real. Right now that real testing exists but isn't
reflected in any coverage number, so `PaywallScreenKt` looks far worse
than it actually is.

`android/TESTING.md`'s existing Coverage section already anticipated
this exact feature as a deferred fallback, but justified deferring it
with "Its marginal contribution is small (Major/Minor already exercise
most of the same non-network code paths its own screens touch)" — a
claim this session's real investigation just contradicted for
`PaywallScreenKt` specifically. Worth building now, and worth correcting
that stale assumption in the docs regardless.

This session deferred starting the implementation to let a manual
context compaction happen cleanly first — this file is the handoff so a
fresh session doesn't need to re-derive the mechanism below.

## The real mechanism (already worked out, don't re-derive)

1. **Major's own coverage file already exists**, written automatically
   by `connectedDebugAndroidTest` (since `enableAndroidTestCoverage =
   true` instruments the whole debug build variant, not per test class):
   `android/app/build/outputs/code_coverage/debugAndroidTest/connected/medium_phone(AVD) - 16/coverage.ec`
   (confirmed real path, 2026-09-09).
2. `test-weekly.ps1`'s raw `adb shell am instrument` call currently
   requests no coverage output. Add `-e coverage true -e coverageFile
   <on-device-path>` to that line — the already-instrumented APK needs
   no rebuild, just the two extra flags — then `adb pull` the resulting
   `.ec` file off the device after the run. Confirm the on-device path
   is actually pullable (app-private storage may need `run-as` or a
   world-readable path — verify this for real, don't assume).
3. **Merge the two `.ec` files** — JaCoCo's own merge capability (either
   `jacococli.jar` directly, or a small custom Gradle `JacocoReport`
   task with both files as `executionData`) combines them into one
   coverage session before generating the report. This is a real merge
   (any instruction either suite touched counts as covered), not an
   average.
4. **Report it as a second, separately-labeled number** — "Major" vs.
   "Major+External" — rather than replacing the existing baseline/gate.
   `coverage_gate.py`'s release-gate check should keep checking
   Major-only (the free, no-real-money tier); the merged number is
   informational, showing what real full coverage (including the paid
   tier) actually is. Needs a new function in `scripts/coverage_lib.py`
   (or an extension of `parse_android_report`) and a new call site in
   `coverage_gate.py`/`generate_dashboard.py`.
5. **Update the stale `TESTING.md` assumption**: its "External-suite
   coverage... marginal contribution is small" paragraph should be
   corrected once this is built (or even before, if this is deferred
   further) — `PaywallScreenKt` is real, concrete evidence against it.

## Real cost/iteration caveat

`test-weekly.ps1` triggers a real (sandboxed, but real) RevenueCat Test
Store purchase every run, plus a real Cloudflare Worker redeploy. Steps
2-3 above (the flag, the pull, the merge tooling) will likely need a few
iterations to get right (unfamiliar territory — no existing precedent in
this codebase, unlike the three-gap closure's well-established
Compose-test pattern). **Validate the merge mechanism cheaply first**:
merge Major's own `.ec` file with a copy of itself (a trivial, free,
repeatable dry run) to prove the merge/report pipeline works before
spending a real `test-weekly.ps1` run on it. Only run the real External
tier once the mechanism is proven to work structurally.

## Recommended execution

Same shape as the three-gap closure: **one background subagent**
(Android instrumented testing needs exclusive emulator access, so this
can't run in parallel with anything else touching the emulator anyway).
Brief it with this file's "real mechanism" and "cost caveat" sections
verbatim — don't make it re-derive the `.ec` file path or re-discover
the dry-run-first strategy. Have it report back with real before/after
numbers (`PaywallScreenKt`'s Major-only % vs. Major+External merged %)
before anything is committed, matching this session's established
review-before-commit pattern.

## Definition of Done

- `test-weekly.ps1` produces a real, pulled `.ec` file from an actual
  External-tier run.
- A real, verified merge of Major's + External's `.ec` files produces a
  combined report, cross-checked against the dry-run (self-merge) proof
  first.
- `coverage_gate.py`/`generate_dashboard.py` report both numbers,
  clearly labeled, with the release gate still checking Major-only.
- `TESTING.md`'s stale "marginal contribution is small" claim is
  corrected with the real merged number for `PaywallScreenKt`.
- `NEXT_STEPS.md` item #8 reflects the real before/after.

## Verification

- Confirm the dry-run (self-merge) round-trips to the exact same number
  as Major alone, before trusting the real merge.
- After the real merge, confirm `PaywallScreenKt`'s combined percentage
  by hand against the JaCoCo HTML report, not just the script's printed
  number.
