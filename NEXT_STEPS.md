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
- `ARCHIVE_DEAD_CODE.md` — the dead-code sweep (roadmap item #10):
  per-platform tool selection, the allowlist/ignore problem, real
  findings and closures.
- `ARCHIVE_EARLY_HISTORY.md` — the earliest (pre-Android) breakdown-logic
  fixes.
- `ARCHIVE_BREAKDOWN_SWEEP.md` — the structured combinatorial sweep added
  for `compute_breakdown`/`verdict_for` and the two real crash bugs it
  found (roadmap item #12).

**Lookup convention**: entries in every archive lead with a bold tag —
`✅ **Real bug`, `**Decided`, `**Design correction`, `**Fix implemented`,
etc. — so `Grep` for a tag (or a keyword/error message) across the archive
files finds a specific past event without reading a whole file.

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

1. ✅ **Python interface gaps — done 2026-08-22.**
   `tests/test_ocr_output_key_contracts.py` (7 cases): every OCR module's
   key set checked against both real consumers (`schemas.py`,
   `fields.py`'s `FIELDS`). `uv run pytest -q`: 95/95 (was 88).
2. ✅ **`scan-proxy`'s Release tier — built 2026-08-22.**
   `npm run test:release` (4 cases): `spendCredit`/`refundCredit`/
   `extractFields` against real RevenueCat/Anthropic, strict-by-default
   key handling. Full detail in `ARCHIVE_TESTING.md`.
3. ✅ **`scan-proxy`'s Weekly tier — built and verified for real,
   2026-08-22.** `scan.weekly.test.ts` (4 cases): real successful scan, a
   valid-but-irrelevant photo (charged not refunded), a corrupted photo
   (real refund path). Full detail in `ARCHIVE_TESTING.md`.
4. ✅ **Android's Weekly-equivalent tier + Unit/Daily coverage tooling —
   done 2026-08-23.** `.\test-weekly.ps1` — real RevenueCat + Worker
   round trip; real JaCoCo coverage (Unit 7%, Daily 71% app-wide). Full
   narrative in `ARCHIVE_ANDROID.md`; real numbers in
   `android/TESTING.md`.
4a. ✅ **Python coverage reporting wired up — 2026-08-24.**
   `uv run pytest --cov --cov-report=term-missing`; real numbers in
   `tests/TESTING.md`.
5. ✅ **Two real production gaps in `workers/scan-proxy` closed —
   2026-08-23** (outbound timeouts, request-level idempotency), including
   a genuine stale-deploy bug the hands-on verification itself caught.
   Full narrative in `ARCHIVE_MONETIZATION.md`/`ARCHIVE_TESTING.md`.
6. ✅ **Streamlit: real four-photo `AppTest` walkthrough — closed
   2026-08-24.** `ExampleDocs/golden_fields.json` backs a real walkthrough
   + parametrized OCR-accuracy test; two real regex bugs found and fixed.
   `streamlit_app/` coverage now real (80%). 116 tests (was 95). Full
   narrative in `ARCHIVE_WEB_STREAMLIT.md`.
7. ⬜ **Lower priority — pick up when there's spare capacity, no
   evidence of a real bug behind any of these**:
   - `web/`'s `Dashboard.tsx`'s own logic beyond the verdict badge — no
     dedicated Module test yet.
   - "Option C" (Pydantic JSON-Schema export) for the
     `TruckTagOut`/`TrailerTagOut`/`ScaleTicketOut` interface gap — full
     write-up in `FUTURE_API_SCHEMA_VALIDATION.md`.
   - ✅ **The README-embedded regression-status dashboard — closed
     2026-08-24.** `dashboard.svg` (generated by `uv run
     scripts/generate_dashboard.py`) embedded at the top of `README.md`;
     real per-platform Minor/Major pass-rate (JUnit XML, run fresh),
     External status (persisted last-real-run, via the new
     `scripts/record_external_result.py` hook on each External wrapper
     script), and coverage (reusing `coverage_gate.py`'s own retrieval,
     via extracted `scripts/coverage_lib.py`). Full narrative in
     `ARCHIVE_TESTING.md`.
8. ⬜ **Increase test coverage across the board** — now that real
   coverage tooling exists for all four platforms (Android #4, Python/
   Streamlit #4a/#6, Web and scan-proxy #9), use those real numbers to
   find and close the biggest gaps rather than just having the tooling in
   place with nothing acted on. No target percentage decided yet —
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
     yet done.
   - **Python/Streamlit's initial real baseline (2026-08-24)** — see
     `tests/TESTING.md`'s Coverage section. 79% total (`src/hdttools` +
     `streamlit_app`); `streamlit_app/app.py` 80%, `fields.py` 100%,
     `recent_rigs.py` 79%. ✅ **`parse_label.py`'s 0% coverage — confirmed
     dead code and removed, 2026-08-24** (roadmap item #10): a stray
     prototype file, never imported anywhere, already git-excluded before
     removal — see `ARCHIVE_DEAD_CODE.md`. Biggest remaining visible gap:
     `review_form.py` 31% (tkinter UI, same class of gap as Android's
     uncovered Compose screens — not easily unit-testable, likely needs
     the same kind of interaction-level test `test_streamlit_app.py`
     already uses for Streamlit's own UI).

9. ✅ **Testing nomenclature redesign: event-based Minor/Major/External
   replacing time-based Sanity/Daily/Weekly/Release, plus a cross-platform
   coverage-gate script — closed 2026-08-24.** Every platform's
   `TESTING.md` now describes only Minor/Major/External (old tier tables
   retired, not kept in parallel); `web/` and `workers/scan-proxy` both
   gained real coverage tooling for the first time. `scripts/coverage_gate.py`
   (`uv run scripts/coverage_gate.py`) enforces a baseline-floor for
   Android (71%), Python (79%), and scan-proxy (100%), and reports Web
   (91%) until it has a real release event. Full narrative, including how
   the terminology confusion was found and unpacked, in
   `ARCHIVE_TESTING.md`.
10. 🔶 **Dead-code sweep: one real, low-false-positive tool per
    platform, plus an allowlist for framework-wired/intentionally-public
    code** — started 2026-08-24. Plan saved to
    `ClaudePlans/2026-08-24-dead-code-sweep.md`; full narrative in
    `ARCHIVE_DEAD_CODE.md`.
    - ✅ Closed the one already-known candidate (`parse_label.py`, see
      item #8's Python baseline bullet above).
    - ✅ Python: `vulture` (`uv run vulture src/hdttools streamlit_app
      vulture_whitelist.py`) — 65 real findings, all false positives
      (FastAPI route handlers, Pydantic/dataclass fields, the deliberate
      public library API), documented in `vulture_whitelist.py`. Zero
      genuine dead code found.
    - ✅ Web + `scan-proxy`: `knip` (`npm run check:dead-code` in each) —
      4 real findings total, all the same "genuinely used but
      unnecessarily `export`ed" shape, fixed by tightening visibility
      (no deletions needed). Zero genuine dead code found.
    - ✅ Android: `detekt` 1.23.8, scoped to `UnusedPrivateMember`/
      `UnusedImports` — 3 real findings (unused imports), fixed. Needed
      a real fix for a Gradle daemon/JDK25 incompatibility first
      (`./gradlew updateDaemonJvm --jvm-version=21`, git-committed,
      portable); full story in `REPORT_KOTLIN_DETEKT_TOOLCHAIN.md`.

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
    end-to-end. Full suite clean (554 passed, 3 xfailed). **Still not
    started**: actually adding new manufacturer/format photos (the
    mechanism is ready; no new real photos exist yet) and the Android
    inherit-vs-duplicate decision.

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
done (moved to the roadmap above as ✅ entries) or captured as roadmap
items #4-#9 above — check there first.

- ✅ **Superseded 2026-08-25** by item #13's fuller design: the real
  Claude-vision regression test idea below is now the "pass-pool" piece
  of `FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md`, with a concrete agreed
  starting point — see that file rather than treating this bullet as the
  current plan.
  - ~~A real Claude-vision regression test using the F-150 photo set —
    unlocks once this project decides where a real-money-per-run test
    belongs (an External-tier equivalent for Python).~~
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
