# RigCheck — where things stand

Working notes for picking this back up on another machine. Written 2026-08-13.
Restructured 2026-08-23 into a slim, current-status core file (this one)
plus topic archives — see "History archives" below.

## 📚 History archives

This file used to carry the full narrative history in-line, which grew
past 1,900 lines and got expensive to read just to check current status.
As of 2026-08-23, detailed narrative (bugs found, gotchas, design
decisions, day-by-day build logs) lives in separate archive files instead;
this file stays limited to the roadmap and other genuinely current status.
When a roadmap item completes, its one-line summary stays here — the
play-by-play goes straight into the relevant archive file below, not into
this one.

- `ARCHIVE_ANDROID.md` — Android app build (Phases 0-4), distribution/
  sideloading, Android-specific test-suite history.
- `ARCHIVE_WEB_STREAMLIT.md` — Web + Streamlit feature history (skip-image
  entry, predictive tow-vehicle-alone weight, real-photo bug hunts).
- `ARCHIVE_MONETIZATION.md` — RevenueCat + Cloudflare Worker (`scan-proxy`)
  billing build-out and account setup.
- `ARCHIVE_TESTING.md` — how the Minor/Major/External test-category model
  was designed and built per platform, including the 2026-08-24 redesign
  that retired the old Sanity/Daily/Weekly/Release tier names.
- `ARCHIVE_DEAD_CODE.md` — the dead-code sweep: per-platform tool
  selection, the allowlist/ignore problem, real findings and closures.
- `ARCHIVE_EARLY_HISTORY.md` — the earliest (pre-Android) breakdown-logic
  fixes.
- `ARCHIVE_BREAKDOWN_SWEEP.md` — the structured combinatorial sweep added
  for `compute_breakdown`/`verdict_for` and the two real crash bugs it
  found (roadmap item #12).

**Lookup convention**: entries in every archive lead with a bold tag —
`✅ **Real bug`, `**Decided`, `**Design correction`, `**Fix implemented`,
etc. — so `Grep` for a tag (or a keyword/error message) across the archive
files finds a specific past event without reading a whole file.

**If a roadmap item number cited elsewhere (a `TESTING.md` file, a code
comment) doesn't appear in the numbered list below**: it was old,
fully closed, and swept out of this file once its full narrative was
safely archived — the archive is the authoritative source, not this
file's own now-removed one-liner. `Grep` the archives above for the
item's number or its topic; there's no separate index of "item number →
which archive" beyond that.

## 🛠️ Dev environment reference

**`DEV_ENVIRONMENT.md`** — this machine's real tool paths and run
commands (Android SDK/emulator/AVD name, Tesseract, Node, `uv`) across
every product line. Machine-specific info that doesn't survive a context
compaction if it's only ever rediscovered ad hoc — check this file
before re-discovering a path via `Get-Command`/`where`/hunting through
env vars again.

## 🗺️ Roadmap: prioritized plan (decided 2026-08-21)

Consolidated, cross-platform view of everything still genuinely open, in
the priority order agreed 2026-08-21. **Living section — update it
directly as items complete** (check off / remove), don't just add a new
dated narrative entry further down and leave this stale; the detailed
"why" for each item lives in the linked archive file, this is
deliberately just the ordered list so "what's next" never requires
reading anything else.

7. ⬜ **Lower priority — pick up when there's spare capacity, no
   evidence of a real bug behind any of these**:
   - `web/`'s `Dashboard.tsx`'s own logic beyond the verdict badge — no
     dedicated Module test yet.
   - "Option C" (Pydantic JSON-Schema export) for the
     `TruckTagOut`/`TrailerTagOut`/`ScaleTicketOut` interface gap — full
     write-up in `FUTURE_API_SCHEMA_VALIDATION.md`.
   - ✅ **The README-embedded regression-status dashboard — closed
     2026-08-24** (`dashboard.svg`, `uv run scripts/generate_dashboard.py`).
     Full narrative in `ARCHIVE_TESTING.md`.
8. ⬜ **Increase test coverage across the board** — now that real
   coverage tooling exists for all four platforms (Android, Python/
   Streamlit, Web and scan-proxy — see `ARCHIVE_TESTING.md`/
   `ARCHIVE_WEB_STREAMLIT.md` for how each got built), use those real
   numbers to find and close the biggest gaps rather than just having
   the tooling in place with nothing acted on. No target percentage
   decided yet —
   prioritize by where coverage is lowest and where a gap plausibly hides
   a real bug, not an arbitrary global number.
   - **Web's initial real baseline (2026-08-24)** — see `web/TESTING.md`'s
     Coverage section. 91.41% statements overall; weakest files
     `UploadStep.tsx` (85.71%) and `App.tsx` (86.95%).
   - **scan-proxy's initial real baseline (2026-08-24)** — see
     `workers/scan-proxy/TESTING.md`'s Coverage section. 100% line/
     branch/function coverage already — the Major suite's 57 tests
     already exercise every line; no gap to close here today.
   - **Android's initial real baseline (2026-08-23)** — see
     `android/TESTING.md`'s Coverage section for the full reference.
     Minor suite: 7% instruction coverage app-wide (expected low, Minor
     only covers business logic, not UI); `RevenueCatManager.kt`
     specifically at 38%; the `compute_breakdown`/`verdict_for` port
     (`com.rigcheck.app.domain`) at 99%. Major suite: 71% instruction
     coverage app-wide; `ResultsScreen.kt` at 100%. Biggest visible gap:
     `com.rigcheck.app.ui.screens`/`.ui.components`/`.ui.navigation` all
     show 0% under the Minor suite alone (expected — no unit test targets
     Compose UI directly); real remaining headroom is whichever of those
     packages isn't already well covered by the Major suite's 30
     instrumented tests once both numbers are compared side by side, not
     yet done. **Real regression found and fixed, 2026-09-09**: a fresh
     `--refresh` run measured 64.28% — a real `FAIL` against this 71%
     baseline. Root cause, confirmed via the actual per-package JaCoCo
     numbers, not assumed: item #18's camera-overlay spike
     (`ui.experiments.cameraoverlay`, 1,790 instructions, only 8%
     covered) lives inside `app/src/main/`, so JaCoCo counts its
     deliberately-isolated, unreachable-from-production code against the
     whole app — the same class of distortion Python's own
     `src/experiments/BoundOCR/` avoids by sitting outside
     `coverage.py`'s `source`. Fixed by extending
     `scripts/coverage_lib.py`'s `parse_android_report` with an
     `exclude_packages` parameter (TDD'd, `tests/test_coverage_lib.py`)
     and wiring `coverage_gate.py`'s new `ANDROID_EXCLUDED_PACKAGES`
     constant through it — add a new entry there, not a baseline change,
     the moment another such spike lands. Re-measured with the fix: real
     coverage is **71.04%**, a real `PASS` — the app's actual shippable
     code never regressed at all. `dashboard.svg` regenerated to match.
   - **Python/Streamlit's initial real baseline (2026-08-24)** — see
     `tests/TESTING.md`'s Coverage section. 79% total (`src/hdttools` +
     `streamlit_app`); `streamlit_app/app.py` 80%, `fields.py` 100%,
     `recent_rigs.py` 79%. ✅ **`parse_label.py`'s 0% coverage — confirmed
     dead code and removed, 2026-08-24**: a stray
     prototype file, never imported anywhere, already git-excluded before
     removal — see `ARCHIVE_DEAD_CODE.md`. **`review_form.py` closed
     from 31% to 48%, 2026-09-09**: rather than driving a real Tkinter
     window (no headless harness exists for it, unlike Streamlit's own
     `AppTest`), extracted the two genuinely pure pieces of logic that
     were entangled with live widgets — `_leaf_fields` (walks a
     dataclass, including nested ones like `TireSpec`, to the same leaf
     paths `add_fields` used to build widgets from) and
     `_rebuild_from_values` (reconstructs a dataclass from a flat
     `{path: raw_string}` dict, mirroring what `rebuild()` used to do
     directly against live `tk.StringVar`s). TDD'd
     (`tests/test_review_form_rebuild.py`, 7 cases including a real
     round-trip test), then verified for real against the actual
     production `TruckTagData`/`TireSpec` dataclasses (23 real leaf
     fields, nested tire specs included) — not just synthetic test
     dataclasses. What's left uncovered is genuinely thin GUI glue
     (`tk.Tk()` setup, the widget-creation loop, button wiring,
     `mainloop()`) — the same class of gap this project already accepts
     for other real-window/shell-out code. **Re-measured 2026-09-09
     (both real improvements together): 84.91%** (up from the
     2026-08-24 baseline of 79%, and from 84.01% before this specific
     fix — see item #13 for the `scale_ticket` portion of the earlier
     jump).

11. ✅ **Real-photo OCR robustness investigation: Tesseract vs. Claude
    vision — closed 2026-08-24.** 10 real photos of the same physical
    Ford tow-vehicle tag, one clear shot plus 9 at varying angle/shadow/
    sun-glare quality (now at `ExampleDocs/scans/truck/f150_blue_goose_uncropped/`,
    renamed 2026-08-25 — see item #13), run through both
    backends this project maintains. Found two real, different-shaped
    gaps — Tesseract needs a crop it never gets, Claude vision doesn't
    need one but has zero real-photo test coverage today. Full narrative
    in `ARCHIVE_WEB_STREAMLIT.md`; no test code added this session (see
    "Tests still outstanding" below for what's deferred).

12. ✅ **Structured combinatorial sweep for `compute_breakdown`/
    `verdict_for` — closed 2026-08-24.** New
    `tests/test_breakdown_combinatorial_sweep.py`: `itertools.product`
    over the known present/absent/zero/boundary value classes already
    implied by the code (378 combinations), asserting invariants (never
    crashes, tone/status always a valid enum member, `estimated` never
    leaks on an insufficient row, `pct` stays in `[0, 100]`) rather than
    exact values, which the existing hand-written/golden-vector tests
    already cover. Found **two real bugs**, both fixed on Python and
    Kotlin with regression tests on both plus two new shared golden-vector
    cases (`zero_rated_limit_is_insufficient_not_a_crash`,
    `pin_weight_pct_of_one_does_not_crash` in
    `test-vectors/breakdown_cases.json`): an explicit `0` rated limit
    crashed Python with `ZeroDivisionError` (Kotlin: silently produced a
    false "over limit" warning instead); `pin_weight_pct` of exactly
    `1.0` crashed Python the same way (Kotlin: silently produced
    `Infinity`) - both reachable from a real, unvalidated caller
    (`POST /api/breakdown`). Full narrative in `ARCHIVE_BREAKDOWN_SWEEP.md`.

13. 🔶 **Constrained-random real-image regression testing for OCR/vision
    extraction — designed 2026-08-25, core design (pass-pool, fail-pool,
    interface-contract suite) all built and passing for real.** Full
    design in
    `FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md`: a "pass-pool" (real
    images randomly selected at test time, resolved against per-vehicle
    golden truth — a failure means a real extraction-API regression), a
    "fail-pool" (known-illegible images with an expected failure
    signature, testing the graceful-degradation path), and an
    interface-contract suite spanning both, manually run whenever
    Tesseract/Claude/a library changes (no automated trigger — the user
    is the event, by explicit choice). Real correction along the way:
    `vision_client.py`'s `claude-sonnet-5` does **not** need a
    dated-snapshot pin — verified via Anthropic's real `/v1/models` list
    that the current model generation has no dated variant at all (only
    superseded generations do), so there was nothing to fix there.
    **Pass-pool schema + resolver done, 2026-08-25**: `golden_fields.json`
    gained a `pass_pool` section grouping existing `"photos"` entries by
    real vehicle per doc_type (`truck_tag` → `f150_blue_goose` →
    `AddieTag.jpg`; `trailer_tag` → `brinkley_goose` → `GooseTag.jpg`) —
    a membership index only, no duplicated field data, so golden values
    can't drift between the two sections. `scripts/pass_pool.py`'s
    `resolve_pass_pool_image(doc_type, rng=...)` picks one registered
    image at random and returns its full `"photos"` entry (fields + any
    `known_ocr_limitations`, carried through rather than stripped —
    `GooseTag.jpg`'s digit-drop limitation still resolves with it).
    TDD'd in `tests/test_pass_pool.py` (written first, watched fail with
    `ModuleNotFoundError`, then made to pass). **First real regression
    test done, 2026-08-25**: `tests/test_pass_pool_regression.py` calls
    the resolver with an *unseeded* `Random()`, runs real Tesseract, and
    asserts the mismatched-field set equals the documented
    `known_ocr_limitations` set (catching drift in either direction —
    a new mismatch or an unexpected improvement) — run for real (not
    assumed) several times to rule out flakiness in the random-pick
    path; passed clean every time. **Fail-pool done, 2026-08-25**:
    reuses the 10 F-150 photos from item #11 (still on disk, never
    re-added to `"photos"`) as a
    self-contained `fail_pool` section in `golden_fields.json` — unlike
    `pass_pool`, no reference into `"photos"` needed, since the golden
    truth here *is* the failure signature itself (`expected_none_fields:
    ["manufacturer", "gvwr_lb", "front_gawr_lb", "rear_gawr_lb"]`,
    confirmed for real against all 10 photos, not assumed).
    `scripts/fail_pool.py`'s `resolve_fail_pool_image` mirrors
    `pass_pool.py`'s shape. `tests/test_fail_pool_regression.py`
    (TDD'd — watched fail with `ModuleNotFoundError` before the module
    existed) proves both that the `None` signature still holds under
    real Tesseract, and that it funnels into `compute_breakdown`'s real
    `"insufficient"`/"Not Enough Information" path — generalizing
    `test_blank_rig_reports_not_enough_information_not_a_false_pass`'s
    hand-written `{}` case to a real garbled-OCR photo, closing the
    "Tesseract's no-auto-crop limitation" test gap this file used to
    track as "no test exists for this yet." Re-run 5x to confirm
    stability across different random picks from the 10-image pool;
    full suite clean (543 passed, 3 xfailed). **Interface-contract
    suite done, 2026-08-25** — per the FUTURE doc's own scoping
    decision, this needed no new code: `DEV_ENVIRONMENT.md` now
    documents the combined command
    (`uv run pytest -q tests/test_pass_pool_regression.py
    tests/test_fail_pool_regression.py -v`), run for real to confirm it
    works, with a note to re-run it a few times on a real dependency
    bump since each run samples one random image per pool/doc_type.
    All three core pieces of item #13's design are now done.
    **Directory-convention auto-discovery done, 2026-08-25**: per the
    project owner's own request ("drop in some images, and some sort of
    file that provides the expected OCR data, and have the test cases
    automatically pick up the new images"), new `scripts/vehicle_discovery.py`
    walks `ExampleDocs/scans/<truck|trailer|scale>/<vehicle_slug>/` for a
    `vehicle.json` (`pool: "pass"/"fail"` + `fields`/`expected_none_fields`)
    plus sibling image files (auto-globbed, `.jpg`/`.jpeg`/`.png` —
    adding one more photo of an already-registered vehicle needs zero
    file edits at all). TDD'd in `tests/test_vehicle_discovery.py` (10
    cases: discovery, ignored non-image/unknown-bucket files, and
    fail-loud `ValueError`s on a malformed sidecar or an image-less
    vehicle folder). `pass_pool.py`/`fail_pool.py` merge discovered
    vehicles into the same in-memory structure the legacy
    `golden_fields.json` entries already use, and both gained a
    `registered_doc_types()` helper so the two regression tests
    parametrize from the merged view. **Real live proof, not just a
    unit test**: the fail-pool's F-150 vehicle was actually migrated —
    `ExampleDocs/scans/truck/f150/` → `.../f150_blue_goose_uncropped/`
    with a real `vehicle.json`, its `golden_fields.json` JSON entry
    deleted — and `tests/test_fail_pool_regression.py` still passes,
    now sourced entirely from the directory. The pass-pool half (no
    spare unentangled real photo to migrate the same way — `AddieTag.jpg`/
    `GooseTag.jpg` both feed other tests) got a real integration test
    instead: copies `CatScale-GooseOnly.jpg`'s real bytes into an
    isolated `tmp_path` tree, proving `resolve_pass_pool_image` and real
    Tesseract both work against a directory-discovered vehicle
    end-to-end. Full suite clean (554 passed, 3 xfailed). **Android
    pass-pool grown, 2026-09-08**: the other 9 F-150 photos
    (`f150_blue_goose_uncropped/`, item #11 confirmed all 9 extract
    perfectly via real `claude-sonnet-5` calls) are now duplicated into
    Android's own pass-pool as a second registered vehicle — zero Kotlin
    changes needed (`resolveRandom` already picks randomly across all
    registered vehicles), verified via two real `.\test-weekly.ps1` runs
    with different random picks, both clean (a real, distinct bug found
    while checking this is tracked separately as item #19). Python's side
    of this item (new-manufacturer photos) is still genuinely blocked on
    new real photos existing.
    **Android decision made and built, 2026-08-25: duplicate, not inherit** —
    Android builds its own real Claude-vision pass-pool/fail-pool rather
    than trusting Python's (Tesseract-only) pools to stand in for it,
    specifically to exercise `PhotoEncoding.kt`'s real resize/compress
    path (1600px long edge, JPEG quality 85), which the one existing
    real-vision test (`realScanDecrementsBalance`) deliberately bypasses
    and never golden-value-checks. New `ScanFixturePool` (TDD'd,
    `android/app/src/androidTest/java/com/rigcheck/app/testsupport/`)
    mirrors `scripts/vehicle_discovery.py`'s directory convention against
    `androidTest/assets/scans/...`. Two new `PaywallScreenWeeklyTest.kt`
    cases (`scanPassPoolRandomPickMatchesGoldenFields`,
    `scanFailPoolRandomPickReturnsNullForMissingFields`) run the real
    pipeline end-to-end and passed for real via `.\test-weekly.ps1`
    (6/6 tests). **This immediately caught a real, previously-unknown bug
    — see item #15.** Full narrative in `android/TESTING.md`/
    `ARCHIVE_MONETIZATION.md`. **Python's `scale_ticket` pass-pool grown
    for real, 2026-09-09**: a new real CAT Scale ticket (Willis TX,
    different weighing event than the two legacy scale tickets) filed at
    `ExampleDocs/scans/scale/brinkley_goose_willis_tx/` — the first real
    `scale_ticket` vehicle registered via the directory-convention
    mechanism (previously exercised only by a synthetic `tmp_path` test).
    Real Tesseract run first to establish honest golden truth before
    writing `vehicle.json`: 5 of 6 tracked fields extract exactly right,
    `location_name` hits the same real two-column-layout jumbling
    limitation already documented for `CatScale-GooseOnly.jpg`, recorded
    via `known_ocr_limitations` rather than guessed. Required registering
    `scale_ticket` in `tests/test_pass_pool_regression.py`'s parser
    dispatch (previously unmapped, since no real `scale_ticket` pass-pool
    vehicle existed yet) and updating one now-stale negative-case test in
    `tests/test_pass_pool.py` that had used `scale_ticket` specifically
    *because* it had no pool yet. Full suite clean (555 passed, 3
    xfailed), pass-pool regression re-run 5x clean. **Still genuinely
    not started**: new-manufacturer/format *truck_tag*/*trailer_tag*
    photos on the Python side still need new real photos that don't
    exist yet.

15. ✅ **Real bug: the deployed Worker was pinned to an unreliable model
    for label extraction — found 2026-08-25, fixed same day.** Found by
    item #13's new Android pass-pool test, not assumed:
    `workers/scan-proxy/src/claude.ts` used `claude-haiku-4-5-20251001`
    (chosen for cost, ~$0.01/scan vs ~$0.03 on Sonnet 5) — real calls
    against it returned confident, non-deterministic, **wrong** GVWR/GAWR
    numbers for `AddieTag.jpg`, the easiest, previously-"known good"
    fixture in the whole repo (two calls, two different wrong answers).
    Ruled out a stale deploy first (redeployed, same wrong results,
    matching this repo's own documented stale-Worker precedent from
    2026-08-23 — this wasn't that). A direct call to `claude-sonnet-5`
    with the identical prompt/schema/image got every field exactly
    right, confirming the model itself was the cause — Python's
    `vision_client.py` (the basis for item #11's "Claude vision is
    robust" finding) had always used `claude-sonnet-5`; nobody had
    validated whether the cheaper model deployed to the actual Worker
    performed anywhere near as well. Fixed by switching `claude.ts` to
    `claude-sonnet-5`; scan-proxy's 3 hardcoded-model test assertions
    updated to match (57/57 pass); redeployed; re-verified for real
    against both the pass-pool and fail-pool fixtures (now correct).
    No production impact — confirmed with the project owner that the app
    isn't deployed/has no real users yet, still in testing/development.
    Full evidence (the wrong responses, the redeploy ruling out staleness,
    the Sonnet-5 confirmation call) in `ARCHIVE_MONETIZATION.md`.

16. ⬜ **Build-time OCR-backend choice for Streamlit/web (Tesseract vs.
    Claude vision) — recorded 2026-08-25, not started.** Real gap in
    institutional memory, surfaced while designing item #13's Android
    work: `src/hdttools/truck_tag.py`/`trailer_tag.py`/`scale_ticket.py`
    already contain a complete, working Claude-vision implementation
    (via `vision_client.extract_via_claude`) — but nothing in the actual
    shipped app (Streamlit + the FastAPI backend, both of which import
    `truck_tag_ocr.py`/`trailer_tag_ocr.py`/`scale_ticket_ocr.py`
    directly) ever calls it. The original intent, per the project owner
    directly, was for Streamlit and the web/API backend to each support
    **either** backend as a **build-time** decision (not a runtime
    toggle) — that path was dropped somewhere during development and
    was never recorded anywhere before now (confirmed: zero hits
    grepping every `.md` file in the repo for this). Does not apply to
    Android — no local OCR engine is available there, so Android stays
    Claude-only regardless of what this item decides. Scope of "done":
    a single build/env-level flag both `src/hdttools/api/main.py` and
    `streamlit_app/app.py` read to choose Tesseract-style parsing vs.
    Claude-vision-style parsing per doc_type, plus Minor/Major test
    coverage for both branches per `TESTING.md`'s existing model, built
    per `TDD_METHODOLOGY.md`'s TDD requirement. Not designed further
    than this yet — pick up fresh in a future session. **Real evidence
    now exists bearing on this decision** — see item #17's Claude-vision
    ceiling check (100% correct on every real photo tested, vs. real,
    unresolved local-OCR limits).

17. ✅ **BoundOCR: free/local OCR alternative to Claude vision —
    investigated 2026-08-26/27, closed 2026-08-29. Decision: stick with
    Claude vision for truck data-plate OCR; no local-OCR replacement is
    currently good enough.** Across two vehicles and three photos
    (including a deliberately careful retake), automated localization
    failed three distinct ways and local OCR recognition (Tesseract,
    EasyOCR) hit real, unresolved accuracy limits even on hand-verified
    crops, while real Claude-vision calls scored 100% correct on every
    photo tested. `src/experiments/BoundOCR/` stays in the repo as an
    isolated, inert historical record (nothing there was ever wired into
    `hdttools/`) in case it's worth revisiting later. Full narrative,
    every real number, and the closure decision in
    `ClaudePlans/2026-08-26-boundocr-report-session-summary.md`.

18. 🔶 **Android: guided-scan camera overlay (framing guide before
    capture) — spiked 2026-08-27, paused 2026-08-29 (no test phone
    available).** Research + feasibility spike (not production code —
    isolated under `android/app/src/main/java/com/rigcheck/app/ui/
    experiments/cameraoverlay/`, unreachable from `MainActivity`/
    `RigCheckNavHost`/`ChooserScreen`, launched only via `adb shell am
    start`) for a CameraX-based live preview with a bounding-box overlay
    guiding users to frame the compliance tag correctly before capture —
    a "fix framing before capture" complement to items #11/#17's
    "fix cropping after capture" findings. Real result: permission flow,
    portrait preview/overlay alignment, and JPEG capture all confirmed
    working; found and fixed a real CameraX/Compose preview-rotation
    timing bug and a real EXIF-orientation bug (`encodePhotoForScan`
    doesn't consult EXIF, so an unrotated production pipeline would have
    saved sideways photos) via `normalizeExifOrientation()`. **One real
    risk left open, not fixed**: landscape capture appeared genuinely
    rotated at the pixel level on the emulator's virtual camera — might
    be an emulator-only artifact, might be a real bug, cannot be told
    apart without a physical device. **Recommendation: conditional go**
    (add as an additional "Guided Scan" option, not a `ChooserScreen`
    replacement) once that risk is confirmed on real hardware. **Paused,
    not abandoned** — the isolated spike code, the CameraX/EXIF
    dependencies, and the full findings stay in the repo as-is; resume by
    testing landscape capture on a real device the moment one is
    available. **Two hardware-independent hardening tests added,
    2026-09-08** (no phone needed, don't require the open landscape
    question to be resolved first): a Minor/JVM test
    (`GuideRectMathTest`, 5 cases) for the overlay's guide-rectangle
    sizing math, extracted from the Canvas draw block into a pure
    `computeGuideRect` function specifically to make this testable
    without Robolectric; and a Major/instrumented test
    (`CameraOverlaySpikeExifTest`, 2 cases) proving `normalizeExifOrientation()`
    really bakes a 90° EXIF rotation into pixels and leaves an
    already-normal image untouched — a synthesized JPEG with a known EXIF
    tag, no live camera or physical device involved. Both caught real,
    honest mistakes in the tests' own assumptions before passing (a wrong
    height-bound test scenario; `ORIENTATION_UNDEFINED` vs. `_NORMAL`
    after `Bitmap.compress()` strips EXIF) — see the test files' comments
    for detail. Full existing Minor (7 files) and Major (48 tests) suites
    still pass clean. **Still open, still needs a phone**: the
    permission-denied/full-capture-flow instrumented tests, and the
    landscape-rotation risk itself. Full plan and results in
    `ClaudePlans/2026-08-27-android-camera-overlay-spike.md` and
    `ClaudePlans/2026-08-27-android-camera-overlay-spike-results.md`.

19. ✅ **Real bug: `android/test-weekly.ps1`'s pass/fail detection was
    blind to real test failures — found and fixed 2026-09-08.**
    Found while verifying item #13's Android pass-pool growth:
    `realPurchaseIncrementsBalance` failed for real on two consecutive
    `.\test-weekly.ps1` runs (visible in the script's own printed JUnit
    text — "FAILURES!!! Tests run: 6, Failures: 1"), yet
    `scripts/dashboard_data/external_status.json` still recorded
    `"passed": true`, and the script itself did not exit non-zero.
    **Root cause, confirmed empirically, not assumed**: `adb shell am
    instrument`'s own process exit code does not reflect an internal
    JUnit failure — a deliberately-failing scratch test
    (`assertTrue(false)`), run the exact same way, printed
    "FAILURES!!! Tests run: 1, Failures: 1" but still returned
    `$LASTEXITCODE = 0`. `test-weekly.ps1` (line 95) captures this
    unreliable `$LASTEXITCODE` as `$testExitCode`, then both exits with
    it (line 105) and passes it straight to
    `scripts/record_external_result.py` (line 103) — so both the
    script's own exit status and the dashboard's recorded status are
    currently meaningless as pass/fail signals; only reading the raw
    printed test-runner text (as this session did, not by trusting the
    exit code) reveals a real failure. Separately confirmed the specific
    `realPurchaseIncrementsBalance` failure itself did not reproduce when
    re-run in isolation on a freshly-booted emulator - looks like real
    UI-timing flakiness under a loaded/long-running emulator, not a
    deterministic regression, but that's a distinct question from the
    exit-code bug and wasn't investigated further. **Fixed and verified,
    2026-09-08**: `test-weekly.ps1` now captures `am instrument`'s printed
    output (via `Tee-Object`, so it still prints live exactly as before)
    and checks the real summary text for `"OK (N tests)"` vs.
    `"FAILURES!!!"`, falling back to the harness's own exit code only for
    an infra-level failure (e.g. `INSTRUMENTATION_FAILED` — separately
    confirmed that *does* exit non-zero on its own). Validated against
    both a deliberately-failing scratch test (correctly detected as
    failed despite exit code 0) and a real passing run (correctly
    detected as passed) before editing the real script; then ran the
    real, fixed script end-to-end — 6/6 real tests passed this time
    (confirming the original `realPurchaseIncrementsBalance` failure
    really was transient emulator-load flakiness, not a regression), exit
    code 0, and `scripts/dashboard_data/external_status.json` recorded
    the accurate result. **Confirmed no second instance**: scan-proxy's
    `test-weekly.ps1`/`test-release.ps1` run `npm run test:weekly`/
    `test:release` (vitest), whose exit codes are reliable — this bug was
    specific to `am instrument`'s exit-code semantics.

**Deliberately not on this list**: pricing/pack sizes (intentionally
deferred until real cost/fee data is in hand, not a gap — see
`ARCHIVE_MONETIZATION.md`); Web hosting/deployment (deferred by your own
explicit choice, local dev only for now, not a gap either).

## 🧪 Tests still outstanding

Living checklist — remove an entry the moment its test actually gets
written; add new entries here as soon as a gap is spotted, not just
mentioned in conversation, so it survives a machine switch. See
`Claude.md`'s "NEXT_STEPS.md Maintenance" section for the standing rule
behind this. Most items that used to live in this section are now either
done (moved to the roadmap above as ✅ entries, several since fully
archived and swept out per the "History archives" note above) or
captured as roadmap items #7-#8 above — check there first.

- **Android guided-scan camera overlay** (item #18) — ✅ **the
  guide-rectangle sizing math (Minor/JVM, `GuideRectMathTest`) and the
  EXIF-orientation regression (Major/instrumented,
  `CameraOverlaySpikeExifTest`) were written 2026-09-08** — turned out
  neither actually needed a physical device or the landscape question
  resolved first, since both are independent of the camera-capture UI
  flow itself (a synthesized JPEG with a known EXIF tag stands in for a
  real capture). **Still genuinely blocked**: a permission-denied/
  full-capture-flow instrumented test (exercises the real Compose screen
  + camera binding, more entangled with the promotion-to-production
  decision) and confirming the open landscape-rotation risk (finding
  #3) — both still need a physical Android test device, per the same
  reasoning as before.

- **Tesseract's no-auto-crop limitation** (item #11) — needs either an
  auto-crop/tag-isolation preprocessing step in `ocr_common.py`, or
  documented in-app guidance telling users to photograph just the tag
  closely, before Tesseract-path OCR can handle a realistic, un-cropped
  phone photo. The fix itself is still not started — still a real,
  separate gap. ✅ **Test now exists, 2026-08-25**: item #13's fail-pool
  (`tests/test_fail_pool_regression.py`) tests *around* this limitation
  rather than fixing it — it reuses the same 10 F-150 photos to prove
  the app degrades gracefully to "Not Enough Information" instead of
  silently accepting garbage, which is what a regression test can prove
  without a fix in hand. It would need updating (not removing) once an
  actual auto-crop/guidance fix ships, since some of these 10 photos
  would then be expected to start succeeding.
  **Investigated for real, 2026-08-26/27 (item #17, BoundOCR)**:
  automated auto-crop (contour/quad detection) was built and tested, and
  failed three separate, real ways across two vehicles; hand-crop
  diagnostics also showed OCR *recognition* quality — not just
  cropping — is a real, unresolved bottleneck for this label style
  (Tesseract near-total garbage regardless of crop quality; EasyOCR
  better but still blocked by small glyph misreads). The fix is still
  not shipped — see item #17 for full results and remaining options
  (fix `locate_label`, wire in EasyOCR, or a manual crop-box UI).

Full historical detail for everything that used to be tracked here
(sanity/daily tier builds, real bugs found while testing, per-platform
regression-pass results) is in `ARCHIVE_TESTING.md` and
`ARCHIVE_ANDROID.md`.

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

**Android** (`android/`): native Kotlin/Compose app, fully built through
Phase 4 (manual entry + optional paid Claude-vision scan feature) — see
`ARCHIVE_ANDROID.md` for the build history, `android/TESTING.md` for its
test tiers.

Both web-app processes are already set up in `.claude/launch.json` in the
**RVSafetyCheck** directory (not this repo) if you're continuing in that
same Claude Code session/workspace — otherwise just run the commands
above.

Full pipeline is verified end-to-end against the real photos in
`ExampleDocs/` (not synthetic data): upload → OCR extract → editable
review → computed pass/fail verdict → shows up in session History/
Dashboard.

## Fresh-machine setup checklist

On a machine that hasn't run this before:
1. `brew install uv tesseract node` (macOS) — all three were missing on
   the Mac this checklist was first written from; don't assume they're
   present. On Windows, install `uv`/Node/Tesseract via their own
   installers (see the "System Tool Installs" standing rule in
   `Claude.md` before installing anything system-wide).
2. `cd HDTTools && uv sync` (Python deps) and `cd web && npm install` (JS
   deps).
3. **Before the first `streamlit run` (or anything that drives
   `AppTest`)**: write `~/.streamlit/credentials.toml` (`email = ""`) and
   `~/.streamlit/config.toml` (`gatherUsageStats = false`,
   `server.headless = true`). Without these, a fresh Streamlit run can
   hang indefinitely on an interactive first-run prompt with no TTY to
   answer it — cost ~40 minutes to diagnose the first time this was hit
   (2026-08-18), see `ARCHIVE_TESTING.md` for the full story.
4. If `streamlit run` ever fails with `ImportError: cannot import name
   '__version__' from 'websockets'`, the package got corrupted by a
   `uv sync` file-lock quirk — delete `.venv/Lib/site-packages/websockets*`
   and let `uv sync --extra streamlit` reinstall clean.
5. `git pull` to get the latest commit if you're setting up a second
   machine.

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
  - **The Tesseract path needs a tight, isolated crop of just the tag —
    confirmed 2026-08-24 (item #11)**: a realistic, un-cropped phone
    photo (the tag as one region within a wider dashboard/door-jamb
    shot) fails to extract *any* of the three weight fields, regardless
    of lighting/angle quality — `preprocess_image()` never crops, and
    `--psm 6` can't isolate the tag's text from surrounding visual
    clutter. The Claude-vision path (`vision_client.py`) does not share
    this limitation — see `ARCHIVE_WEB_STREAMLIT.md`.
- **No mobile layout, no drag-and-drop upload** on the web app (click-to-
  browse file input only) — matches the original design handoff's stated
  scope. (The native Android app is the mobile answer instead.)
- **Not hosted anywhere yet** — local dev only, by explicit choice (see
  the roadmap's "Deliberately not on this list"). Since the backend is
  stateless (no database), hosting it would be simple whenever this is
  picked up — no managed Postgres/persistence question to answer, just
  getting the process running somewhere with `apt-get install
  tesseract-ocr` available.

## Natural next steps, roughly in order

1. **Try it against more real labels.** Only one truck-tag manufacturer
   (Ford) and one trailer manufacturer (Brinkley RV) have been tested.
   Other manufacturers' compliance labels will have different layouts —
   expect to extend `truck_tag_ocr._parse_fields` /
   `trailer_tag_ocr._parse_fields` with more pattern variants as you feed
   it real photos of your actual rig.
2. **Decide on hosting** when ready to move off `localhost` for the web
   app — see the note above, or revisit if requirements have changed.
