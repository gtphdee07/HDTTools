# Android Claude-vision pool + record the dropped Tesseract/Claude build-time switch

## Context

Two separate things this session surfaced, handled together since they
came from the same conversation thread:

**1. A real gap in institutional memory.** While comparing Android's and
Python's OCR paths, it came out that Python actually has *two*
independent "read a truck tag" implementations that were never wired
together: the desktop CLI readers (`truck_tag.py`/`trailer_tag.py`/
`scale_ticket.py`, calling Claude vision via `vision_client.py`,
requiring `ANTHROPIC_API_KEY`) and the real production app (Streamlit +
FastAPI, both importing `truck_tag_ocr.py`/etc. directly, Tesseract
only, no API key). The project owner confirms the original intent was
for Streamlit and the web version to each support **either** backend as
a **build-time** choice — that decision path was dropped somewhere
during development and never recorded anywhere (confirmed by grep: zero
hits across every `.md` file in the repo). This needs recording as a
roadmap item, not designed/built today.

**2. The Android-side "duplicate" decision** (`FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md`'s
open "Cross-platform scope" question) is now resolved: build Android's
own real pass-pool/fail-pool for Claude vision, run through Android's
*actual* `PhotoEncoding.kt` resize/compress path, because Android can't
run Tesseract at all and camera-framing/compression artifacts are a
real, Android-specific risk `PhotoEncoding.kt` introduces (1600px long
edge, JPEG quality 85) that nothing in this repo currently tests — the
one existing real-vision test, `realScanDecrementsBalance`
(`PaywallScreenWeeklyTest.kt`), deliberately bypasses `PhotoEncoding.kt`
and asserts only "fields non-empty," never a real golden-value match.
Real cost is small and bounded (~$0.01/call, a couple of runs per
release cycle, per the project owner's own framing) — the QA payoff
(catching a real regression before it becomes app-store reviews) is
judged worth it.

## Part A — record the dropped build-time switch (documentation only)

Add a new `NEXT_STEPS.md` roadmap item (⬜, not started) capturing:
- The original intent: Streamlit and the web/API backend should each be
  able to choose Tesseract (free, local, no API key, but no-crop framing
  gap + narrower format robustness per item #11) or Claude vision
  (needs `ANTHROPIC_API_KEY`, real per-call cost, broader robustness per
  item #11's finding) as a **build-time** decision — not a runtime
  toggle, and not applicable to Android (no local OCR engine available
  there, so Android stays Claude-only regardless of this decision).
- Why it matters now: discovered as a real, previously-unrecorded gap
  while designing item #13's Android work — `truck_tag.py`/etc. already
  contain a full, working Claude-vision implementation, but nothing
  wires it into the production Streamlit/FastAPI path today.
- Scope of "done" (for a future session, not this one): a single
  build/env-level flag both `src/hdttools/api/main.py` and
  `streamlit_app/app.py` read to pick `truck_tag_ocr`-style Tesseract
  parsing vs. `vision_client.extract_via_claude`-style Claude parsing
  per doc_type, plus Minor/Major test coverage for both branches per
  `TESTING.md`'s existing model, per `TDD_METHODOLOGY.md`'s TDD
  requirement.

No code changes for Part A — this is a roadmap-only entry.

## Part B — Android's own real pass-pool/fail-pool

### Design

**Fixture convention**: reuse the exact same `vehicle.json` schema
Python's `scripts/vehicle_discovery.py` already established
(`{"pool": "pass", "fields": {...}}` / `{"pool": "fail",
"expected_none_fields": [...]}`, field names already confirmed
identical between Python and Android — `ScanFieldMapping.kt` consumes
the Worker's JSON verbatim, snake_case included). Bundled under
`android/app/src/androidTest/assets/scans/<bucket>/<vehicle_slug>/` —
Android's own copy, since instrumented tests read bundled APK assets,
not the repo's `ExampleDocs/` tree directly. Duplicating photo bytes
across the Python/Android boundary is already this repo's accepted
practice (`AddieTag.jpg` is already duplicated this way today).

**Two real fixtures, both zero-new-photography** (mirroring Python's own
"prove the mechanism before collecting more data" approach):
- **Pass-pool**: `scans/truck/f150_blue_goose/` — a fresh copy of the
  already-bundled `AddieTag.jpg` plus a new `vehicle.json` (fields:
  `manufacturer`/`gvwr_lb`/`front_gawr_lb`/`rear_gawr_lb`, same real
  values already in `ExampleDocs/golden_fields.json`). The existing
  top-level `android/app/src/androidTest/assets/AddieTag.jpg` used by
  `realScanDecrementsBalance` is left untouched — same "don't touch a
  legacy path with another consumer" rule Python's own migration
  followed.
- **Fail-pool**: `scans/truck/f150_blue_goose_framing_gap/` — a copy of
  `ExampleDocs/scans/truck/f150_blue_goose_uncropped/20260824_141545.jpg`,
  the one real photo item #11 already found Claude vision genuinely
  fails on (the tag's top portion is outside the frame — an
  information-theoretic gap, not a model weakness; the other 9 F-150
  photos all succeed under Claude per that same finding, so they're
  future pass-pool material, not fail-pool — noted in `NEXT_STEPS.md`
  as ready-made, zero-new-photography growth for later, not built now).
  **`vehicle.json`'s `expected_none_fields` must be determined by one
  real scan call during implementation, not guessed** — same discipline
  item #11 and the Python fail-pool both already followed. It's also
  not yet known whether the Worker returns `Success` with some null
  fields or an outright `Failure` for this photo; the real call
  resolves that, and the test/vehicle.json are written to match
  whatever is actually true.

**Discovery module** (new, test-support only — stays out of `main/`,
mirroring `scripts/pass_pool.py`'s own "test infrastructure, not
application code" rule): `FixtureFileSource` (a small interface —
`list(path): List<String>`, `readText(path): String`) lets the
discovery logic (`ScanFixturePool`, walks bucket → vehicle →
`vehicle.json` + sibling images, same shape as
`scripts/vehicle_discovery.py`) be unit-tested against a fake in-memory
implementation, with `AssetFixtureFileSource` as the thin real adapter
wrapping `AssetManager` for actual instrumented use. This repo has no
JUnit `Parameterized` anywhere (confirmed) — a single random resolve +
assert per test function (matching Python's own pass-pool/fail-pool
design) needs no new parametrization infrastructure.

All three new files live under `android/app/src/androidTest/java/com/rigcheck/app/testsupport/`:
`FixtureFileSource.kt`, `AssetFixtureFileSource.kt`, `ScanFixturePool.kt`.

**The two real tests** go into the *existing* `PaywallScreenWeeklyTest.kt`
as two new `@Test` functions, right alongside `realScanDecrementsBalance`
— not a new class. This matches this repo's own established convention
(that file already groups by *test tier*, not by feature — scan-credit
tests already live there despite not being "paywall screen" tests) and
needs zero `build.gradle.kts`/`test-weekly.ps1` wiring changes, since
that file is already the sole External-tier class both reference.
- `scanPassPoolRandomPickMatchesGoldenFields()`: resolve a random image
  via `ScanFixturePool`, copy its asset bytes to a cache file, build a
  `Uri.fromFile(...)`, run it through the real `encodePhotoForScan()`
  (the actual resize/compress path — deliberately *not* bypassed, unlike
  the existing test), call real `ScanApiClient.scan(...)`, assert
  `Success` and that every documented field matches.
- `scanFailPoolRandomPickHandlesFramingGapGracefully()`: same pipeline,
  asserting whatever the real, empirically-confirmed failure shape is
  (documented in step 3 below, not assumed here).

### Steps (TDD order)

1. **Part A**: add the `NEXT_STEPS.md` roadmap item described above.
2. **TDD `ScanFixturePool`**: write `ScanFixturePoolTest.kt` first
   (Major/instrumented tier — `androidTest/` code can't be referenced
   from the JVM-only `test/` source set, so this can't be a true
   Minor/JVM test without moving code into `main/`, which would ship
   test-support code in the app; using a fake `FixtureFileSource` still
   keeps it real-network-free and fast within that tier), covering:
   discovers a pass-pool vehicle with fields; discovers a fail-pool
   vehicle with `expected_none_fields`; ignores a non-`vehicle.json`
   stray file; random resolution picks among multiple registered
   vehicles. Watch it fail to compile (the classes don't exist yet),
   then write `FixtureFileSource.kt`/`ScanFixturePool.kt` to pass it.
3. **Determine the fail-pool's real signature**: run one real scan
   (via a throwaway instrumented test run, or manually) against the
   copied `20260824_141545.jpg` through the real pipeline, record the
   actual `Success`/`Failure` shape and whichever fields are really
   missing.
4. **Build the fixtures**: copy the two images, write both
   `vehicle.json` files (fail-pool's `expected_none_fields` set from
   step 3's real result, not guessed) plus `AssetFixtureFileSource.kt`.
5. **Add the two real `@Test` functions** to `PaywallScreenWeeklyTest.kt`.
6. **Document**: add both new cases to `android/TESTING.md`'s External
   section (matching its existing per-test-case bullet style), and
   close out `NEXT_STEPS.md` item #13 / `FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md`'s
   Android question with the real decision + what was built + the
   9-remaining-F-150-photos growth note.

## Definition of Done

- `ScanFixturePoolTest.kt` passes for real on-device, TDD'd (watched
  fail to compile first).
- Both new fixtures exist with real, empirically-confirmed golden data
  (the fail-pool signature confirmed via a real call, not assumed).
- `PaywallScreenWeeklyTest.kt`'s two new tests pass for real via
  `.\test-weekly.ps1` (run once to confirm — real money, no reason to
  re-run repeatedly beyond that during this implementation).
- `android/TESTING.md`, `NEXT_STEPS.md`, and
  `FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md` all reflect the real,
  finished state; the new Part A roadmap item exists.
- Existing Daily/Major suite (`./gradlew connectedDebugAndroidTest`)
  still passes unchanged — nothing about the existing exclusion
  mechanism needed to change.

## Verification

1. `./gradlew connectedDebugAndroidTest` — confirms the new
   `ScanFixturePoolTest` runs and passes as part of the normal Major
   suite, and nothing else regressed.
2. `.\test-weekly.ps1` — real run, confirms both new scan-pool tests
   pass for real against the real deployed Worker and real Claude.
3. Manually inspect the real `test-weekly.ps1` output for the fail-pool
   test's actual assertion path to confirm it's checking something
   real, not a tautology.
