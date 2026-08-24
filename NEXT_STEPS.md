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
- `ARCHIVE_TESTING.md` — how the Minor/Major test-category model and the
  Sanity/Daily/Weekly/Release tiers were designed and built, per platform.
- `ARCHIVE_EARLY_HISTORY.md` — the earliest (pre-Android) breakdown-logic
  fixes.

**Lookup convention**: entries in every archive lead with a bold tag —
`✅ **Real bug`, `**Decided`, `**Design correction`, `**Fix implemented`,
etc. — so `Grep` for a tag (or a keyword/error message) across the archive
files finds a specific past event without reading a whole file.

## 🗺️ Roadmap: prioritized plan (decided 2026-08-21)

Consolidated, cross-platform view of everything still genuinely open, in
the priority order agreed 2026-08-21. **Living section — update it
directly as items complete** (check off / remove), don't just add a new
dated narrative entry further down and leave this stale; the detailed
"why" for each item lives in the linked archive file, this is
deliberately just the ordered list so "what's next" never requires
reading anything else.

1. ✅ **Python interface gaps — done 2026-08-22.** New
   `tests/test_ocr_output_key_contracts.py` (7 cases): every OCR
   module's `_parse_fields()` key set checked against both real
   downstream consumers, in the direction each one actually breaks
   silently in — `schemas.py` (a `_parse_fields` key not declared there
   would be silently dropped by FastAPI's `response_model`) and
   `fields.py`'s `FIELDS` dict (a `FIELDS` name that doesn't match a real
   `_parse_fields` key would never get pre-filled by Streamlit's
   `_extract_fields`, opposite direction since `FIELDS` deliberately
   shows only a curated subset of what OCR extracts — checking the wrong
   direction here would have failed immediately on legitimate,
   by-design fields like VIN/tire-spec/the `*_kg` values that OCR
   extracts but the review form never shows). Both known manual-only
   fields (`standalone_weight_lb`, `axle_count`) excluded explicitly. No
   synthetic OCR text needed — `_parse_fields("")` still returns the full
   key set, since every field key is always populated (with `None` on no
   match), never omitted. `uv run pytest -q`: 95/95 (was 88). Both
   `tests/TESTING.md` known-gap bullets closed.
2. ✅ **`scan-proxy`'s Release tier — built 2026-08-22.** New
   `src/release/scan.release.test.ts` (4 cases), `npm run test:release`:
   `spendCredit`/`refundCredit` called directly against real RevenueCat
   (`weekly-test-user`, net zero balance change; `weekly-test-user-no-credits`
   for the real 422), and `extractFields` called directly against real
   Anthropic (a real `ExampleDocs/AddieTag.jpg` extraction, and a real
   invalid-key auth-failure case). Strict-by-default key handling: a
   missing `ANTHROPIC_API_KEY`/`REVENUECAT_SECRET_KEY` stops the whole
   run before any test executes (reported as one failed test naming
   which key is missing), not a silent skip — `-SkipKeys`/`SKIP_KEYS=1`
   explicitly opts into the permissive per-boundary-skip behavior
   instead. A key that's *present but wrong* is caught and reported as
   `"<ENV_VAR_NAME> appears invalid"` with the real error body attached,
   not a generic status-mismatch failure. Full design/verification detail
   (including the real ~$0.01 cost incurred from an ambient
   `ANTHROPIC_API_KEY` during verification) in `ARCHIVE_TESTING.md`.
   `npm test`/`npm run test:sanity` unaffected (47/7).
3. ✅ **`scan-proxy`'s Weekly tier — the rest of it, built and verified
   for real 2026-08-22.** Three new cases in `scan.weekly.test.ts`
   (4 total): a real successful scan of `ExampleDocs/AddieTag.jpg`
   against `weekly-test-user`; a real scan of a valid-but-irrelevant
   image (the WTWT logo) proving it's charged, not refunded (Claude's
   forced `tool_choice` can't refuse an off-topic photo); the same logo
   truncated to 200 bytes, undecodable, triggering the real refund path
   for free. Design-correction detail (why a normal wrong photo *can't*
   demonstrate "OCR failure" for this Worker) in `ARCHIVE_TESTING.md`.
   `npm test`/`npm run test:sanity` unaffected.
4. ✅ **Android's Weekly-equivalent tier + Unit/Daily coverage tooling —
   both parts done and verified for real, 2026-08-23.** Part A:
   `.\test-weekly.ps1` → `OK (3 tests)`, real RevenueCat Test Store +
   real Worker call, `weekly-test-user`'s balance moved both ways for
   real. Part B: real JaCoCo coverage via AGP's built-in support (Unit
   7% app-wide / `RevenueCatManager.kt` 38%; Daily 71% app-wide /
   `ResultsScreen.kt` 100%), zero regression (31/31 unit, 39/39 daily
   unaffected); Weekly-tier coverage deliberately deferred (documented
   nice-to-have, not built). Full narrative for both parts — three
   rejected mechanisms for routing a second Application class into one
   test APK, a real main-thread-only purchase-trigger bug, the coverage
   DSL's nested-block form confirmed only by a real build since AGP's
   own docs pages didn't render — in `ARCHIVE_ANDROID.md`; real report
   paths and task names in `android/TESTING.md`'s new "Coverage"
   section.
4a. ⬜ **Wire up Python coverage reporting** — decided 2026-08-23, right
   after #4. Nearly free: `pytest-cov` is already a dev dependency and
   `pyproject.toml`'s `[tool.coverage.run]` already scopes to
   `src/hdttools`; just needs `--cov` actually wired into a run command
   (`uv run pytest --cov` or a new script), which isn't the case today —
   `uv run pytest -q` never invokes it, so no coverage numbers exist yet
   anywhere in this repo. Doing this right after Android's item #4 means
   every Python test written for items #5 onward shows up as a visible
   coverage delta instead of everything getting measured retroactively.
5. ✅ **Two real production gaps in `workers/scan-proxy` — closed and
   verified for real, 2026-08-23.** Gap A: `claude.ts`'s Anthropic client
   now times out at 20s (`ANTHROPIC_TIMEOUT_MS`), `revenuecat.ts`'s
   `fetch()` at 10s (`AbortSignal.timeout`); `scan.ts`'s `spendCredit`
   call site now catches a rejection (what a real timeout produces) and
   maps it to `billing_error` instead of letting it propagate uncaught —
   closing a gap `scan.test.ts` had explicitly pinned down as known-but-
   unfixed. Gap B: new optional `client_request_id` field
   (`request.ts`/`ScanRequest`) reused as the RevenueCat idempotency key
   in `scan.ts`; Android's `RigCheckViewModel.performScan`/
   `performStandaloneScan` generate one UUID per tap, threaded through
   `ScanApiClient.scan(...)`. 57/57 `scan-proxy` unit tests (was 46),
   4/4 real Weekly-tier, deployed to Cloudflare
   (`2743feea-fe1c-40d0-b9a3-4471a6b8839d`). **Real hands-on
   verification** (new `PaywallScreenWeeklyTest.realDuplicateScan...`):
   first run against the *not-yet-redeployed* Worker genuinely spent
   twice (53→52 expected, got 51) — confirming the local fix alone
   wasn't the whole story; a `wrangler deploy` was required before the
   client-side fix actually took effect. After deploying, the same test
   passed for real: two scans sharing one `client_request_id` moved
   `weekly-test-user`'s balance by exactly 1. Zero regression: Android
   Unit 31/31, Daily 39/39, Weekly 4/4 (one transient RevenueCat network
   blip and one transient Compose-timeout on `RigCheckNavHostTest` both
   reproduced clean on an isolated re-run — the already-documented
   emulator-screen-sleep gotcha, not a real regression). Full narrative
   in `ARCHIVE_MONETIZATION.md`.

   **✅ Two process gaps this verification exposed, both closed
   2026-08-23** (user-prompted: "shouldn't the test script catch this
   itself?"). (1) The stale-deploy near-miss above was a real script
   bug, not just a one-off mistake — `workers/scan-proxy/package.json`
   now has a `pretest:weekly` hook (npm's own pre-script convention) that
   runs `typecheck` then `deploy` before `test:weekly` ever runs, so the
   deployed Worker structurally can't go stale again; `test-weekly.ps1`
   got the equivalent explicit step. (2) The screen-sleep gotcha is now
   automated away too, not just documented: `wakeEmulatorForInstrumentedTests`,
   a Gradle `Exec` task `connectedDebugAndroidTest` depends on, wakes the
   emulator before every Daily-tier run regardless of invocation.
   Verifying the wake-task fix surfaced a second, unrelated real
   infrastructure issue (the emulator's own launcher ANR'd and its
   dialog was stealing window focus, after `system_server` itself
   crashed from a long session's cumulative load) — full story in
   `ARCHIVE_TESTING.md`, not a regression from either fix.
6. ⬜ **Streamlit: a real `ExampleDocs/`-photo-driven `AppTest`
   walkthrough** — flagged as the actual open gap for a long time; same
   proven pattern that already found a real bug elsewhere (the
   scale-ticket real-photo test — see `ARCHIVE_WEB_STREAMLIT.md`).
   **Bundle in widening Python coverage's scope to include
   `streamlit_app/`** (decided 2026-08-23) — today's `[tool.coverage.run]`
   only covers `src/hdttools`, so Streamlit's own code isn't measured at
   all yet even once #4a turns coverage on. Doing this alongside the new
   walkthrough test means its real coverage contribution is visible
   immediately, not measured cold with nothing to compare against.
7. ⬜ **Lower priority — pick up when there's spare capacity, no
   evidence of a real bug behind any of these**:
   - `web/`'s `Dashboard.tsx`'s own logic beyond the verdict badge — no
     dedicated Module test yet.
   - The statically-generated regression-results dashboard script — the
     docs half of this old backlog item is done for every platform now;
     the script itself was never started.
   - "Option C" (Pydantic JSON-Schema export) for the
     `TruckTagOut`/`TrailerTagOut`/`ScaleTicketOut` interface gap — full
     write-up in `FUTURE_API_SCHEMA_VALIDATION.md`.
   - Coverage tooling for `web/` (Vitest's built-in `coverage` provider)
     and `workers/scan-proxy` (Node's `--experimental-test-coverage`) —
     neither raised explicitly yet (2026-08-23 discussion was scoped to
     Android/Python/Streamlit specifically), flagged here so the gap
     doesn't get lost before a paid release.
   - Truck tag / trailer tag real-photo OCR pytest coverage — the scale
     ticket reader already has this (`tests/test_scale_ticket_real_photo.py`,
     see `ARCHIVE_WEB_STREAMLIT.md`); truck tag and trailer tag readers
     don't yet. Same pattern, straightforward to replicate.
8. ⬜ **Increase test coverage across the board** — now that real
   coverage tooling exists for Android (#4) and is coming for Python
   (#4a) and Streamlit (#6), use those real numbers to find and close
   the biggest gaps rather than just having the tooling in place with
   nothing acted on. No target percentage decided yet — prioritize by
   where coverage is lowest and where a gap plausibly hides a real bug,
   not an arbitrary global number.
   - **Android's initial real baseline (2026-08-23)** — see
     `android/TESTING.md`'s Coverage section for the full reference.
     Unit tier: 7% instruction coverage app-wide (expected low, Unit
     only covers business logic, not UI); `RevenueCatManager.kt`
     specifically at 38%; the `compute_breakdown`/`verdict_for` port
     (`com.rigcheck.app.domain`) at 99%. Daily tier: 71% instruction
     coverage app-wide; `ResultsScreen.kt` at 100%. Biggest visible gap:
     `com.rigcheck.app.ui.screens`/`.ui.components`/`.ui.navigation` all
     show 0% under the Unit tier alone (expected — no unit test targets
     Compose UI directly); real remaining headroom is whichever of those
     packages isn't already well covered by the Daily tier's 30
     instrumented tests once both tiers' numbers are compared side by
     side, not yet done.

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
items #4-#7 above — check there first. The one item below isn't yet
represented anywhere else:

- **Truck tag / trailer tag real-photo OCR tests** — same real-`ExampleDocs/`-
  photo pattern already proven for the scale-ticket reader (found a real
  bug there, see `ARCHIVE_WEB_STREAMLIT.md`), not yet built for the other
  two readers. Also tracked in roadmap item #7.

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
