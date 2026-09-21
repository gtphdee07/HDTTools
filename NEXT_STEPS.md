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
  found.

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
   - **Web**: 91.41% statements — see `web/TESTING.md`'s Coverage section.
   - **scan-proxy**: 100% line/branch/function coverage already — see
     `workers/scan-proxy/TESTING.md`'s Coverage section. No gap to close
     here.
   - **Android**: real baseline 71.00%, currently **73.50%** Major-only
     (**78.38%** Major+External merged, informational) after real work
     2026-09-09 — see `android/TESTING.md`'s Coverage section for the
     full per-class numbers. Summary: a Minor-vs-Major cross-reference
     found and closed three real gaps (`RigCheckNavHostKt` 80%→90%,
     `ReferenceImageCardKt` 57%→100%, `PaywallScreenKt` 45%→51%); a real
     false-regression (71%→64.28%) was root-caused to item #18's
     camera-overlay spike and fixed via a `coverage_gate.py`
     `ANDROID_EXCLUDED_PACKAGES` exclusion mechanism; and External-tier
     (`PaywallScreenWeeklyTest.kt`) coverage was merged in for real
     (`PaywallScreenKt` 51%→86% once RevenueCat-dependent paths count),
     mechanism in `ClaudePlans/2026-09-09-merge-external-tier-coverage-
     paywallscreen.md`. Full narrative for all three in
     `android/TESTING.md`'s Coverage section.
   - **Python/Streamlit**: real baseline 79% (2026-08-24), currently
     **84.91%** (2026-09-09) — see `tests/TESTING.md`'s Coverage section.
     `parse_label.py` (0% coverage) confirmed dead code and removed
     (`ARCHIVE_DEAD_CODE.md`); `review_form.py` closed 31%→48% by
     extracting its Tkinter-entangled logic into pure, testable functions
     verified against real production dataclasses (`ARCHIVE_WEB_STREAMLIT.md`).

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

13. 🔶 **Constrained-random real-image regression testing for OCR/vision
    extraction — designed 2026-08-25, core design fully built and
    verified for real.** Pass-pool, fail-pool, interface-contract suite,
    and directory-convention auto-discovery (`scripts/vehicle_discovery.py`)
    all done and passing; Android built its own duplicate pass-pool/
    fail-pool (decision + rationale in `FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md`'s
    "Cross-platform scope" section) rather than inheriting Python's, which
    immediately caught a real bug (`ARCHIVE_MONETIZATION.md`). Grown
    twice since with
    ready-made real photos — Android's pass-pool (2026-09-08) and
    Python's `scale_ticket` pool (2026-09-09). Full design, every
    completed step, and the real numbers behind each are in
    `FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md`. **Still genuinely open**:
    new-manufacturer/format *truck_tag*/*trailer_tag* photos on the
    Python side — blocked on new real photos existing, not on any
    further code/design work.

16. ✅ **Build-time OCR-backend choice for Streamlit/web (Tesseract vs.
    Claude vision) — done 2026-09-09.** `HDTTOOLS_OCR_BACKEND` env flag
    (default `"tesseract"`, `"claude"` the only other valid value, fail
    loud otherwise), read by both `main.py` and `app.py`'s per-doc-type
    dispatch; `vision_client.extract_via_claude` refactored to take
    bytes instead of a path; new headless `extract_*_fields` functions
    per doc type; new first-ever Python External-tier test
    (`test_claude_vision_external.py`), all 3 doc types passing for real.
    Along the way, surfaced and fixed a real `golden_fields.json` ground-
    truth gap: `AddieTag.jpg`'s documented `manufacturer` value matched
    Tesseract's own imprecision (a dropped trailing period) rather than
    the physical label — corrected to `"FORD MOTOR CO."` with a
    `known_ocr_limitations` entry. Full narrative, including the real
    `ANTHROPIC_API_KEY`-ambient-env gotcha found on this machine, in
    `ARCHIVE_WEB_STREAMLIT.md`.

18. 🔶 **Android: guided-scan camera overlay (framing guide before
    capture) — spiked 2026-08-27, paused 2026-08-29 (no test phone
    available).** A "fix framing before capture" complement to item #11's
    and BoundOCR's (`ClaudePlans/2026-08-26-boundocr-report-session-summary.md`)
    "fix cropping after capture" findings — CameraX preview +
    Compose bounding-box overlay, isolated under
    `.../ui/experiments/cameraoverlay/`, not wired into production nav.
    Permission flow, portrait alignment, and JPEG capture all confirmed
    working; two real bugs (a preview-rotation timing bug, an
    EXIF-orientation bug) found and fixed. **One real risk left open,
    still needs a physical device to resolve**: landscape capture
    appeared rotated at the pixel level on the emulator's virtual
    camera — can't tell emulator artifact from real bug without real
    hardware. **Recommendation: conditional go** once that's confirmed.
    Two hardware-independent hardening tests added since (2026-09-08,
    don't need a phone) and a coverage-exclusion fix (2026-09-09, this
    spike was silently dragging Android's whole-app coverage number
    down). Full narrative in `ARCHIVE_ANDROID.md`; original spike/results
    in `ClaudePlans/2026-08-27-android-camera-overlay-spike*.md`.

20. ⬜ **Shared accounts + paywall across Android and Web — sequencing
    reversed 2026-09-20 (Android now ships first, not the web beta).**
    Original build-scope facts below are unchanged (`HDTTOOLS_OCR_BACKEND=claude`
    still has no cost-gating anywhere in this backend if turned on
    publicly — confirmed while planning the web beta, see
    `ClaudePlans/2026-09-18-web-beta-deployment.md`), but the *sequencing*
    and *account-sharing* decisions below supersede that plan's framing.
    **What changed 2026-09-20**: instead of the free Tesseract-only web
    beta shipping first and accounts/paywall following later as a
    web-only feature, Android now ships first as an informal/sideload
    beta (explicitly *not* a Play Store production release — see
    `ARCHIVE_ANDROID.md`), and everything below gets built as ONE shared
    system used by both platforms from the start. Real fix needed
    regardless of sequencing: Android's RevenueCat Test Store config and
    hardcoded `smoke-test-user` identity must swap to production
    (~1-2 days, already flagged in `ARCHIVE_ANDROID.md`).
    **Decided** (2026-09-20, via direct discussion + `AskUserQuestion`,
    captured in `ClaudePlans/2026-09-20-screen-flow-specification.md`):
    - One shared account system across Web and Android (not two
      independent ones) — the harder path, chosen deliberately.
    - Sign Up/Log In support email+password plus "Continue with
      Google"/"Continue with Apple."
    - No account-linking/migration screen yet — deferred until early
      Android beta testers (who exist under anonymous RevenueCat IDs
      today) actually need reconciling into the shared system.
    - Full screen inventory + designer-ready mockups exist:
      `DESIGN_BRIEF.md` (repo, canonical) plus 4 published Artifacts — a
      design system ("Wandering Trails Wagging Tails": teal/purple/orange
      palette, Outfit/DM Sans/Sacramento type) and three interactive
      canvases (RigCheck Web, RigCheck Android, a marketing Homepage)
      covering every existing + new screen. See item #21 below for the
      token-level port of that palette into both codebases.
    **Still the single biggest unresolved risk, not decided**:
    entitlement source-of-truth — does RevenueCat stay Android's (and
    the shared system's) system of record with Stripe added for Web and
    a reconciliation layer between them, or does one system become the
    single source of truth for both?
    **Rough scope, comparable to Android's whole Phase 4 monetization
    build** — not a quick bolt-on:
    - **Accounts/auth**: nothing exists in either stack today. A hosted
      provider (Clerk, Supabase Auth, Auth0) is days of work; hand-rolled
      (sessions, password reset, email verification) is ~1-2 weeks and
      adds real security surface. Add ~1-2 weeks on top to make it work
      identically across both platforms.
    - **A real database**: the web backend is 100% stateless today (no
      DB anywhere — unlike the CLI tool's local SQLite). Needed for
      users, credit balances/subscriptions, usage history, on both
      platforms once shared.
    - **Payments**: Stripe for Web (RevenueCat is mobile-IAP-first),
      RevenueCat stays for Android — hence the entitlement
      source-of-truth question above.
    - **Server-side cost-gating**: deduct a credit/check quota before
      every Claude-vision call. `workers/scan-proxy/`'s *pattern* (charge
      before calling Claude) is the right mental model, but its code
      isn't reusable as-is — tightly wired to RevenueCat customer IDs
      and Android's purchase flow.
    - **Services to register for**: Stripe; an auth provider, or Supabase
      alone (bundles Postgres + Auth in one signup, covering two needs
      at once); the Anthropic key already exists.
    **Other open questions, unchanged**: credits-per-scan (matches how
    Android already thinks about it) vs. a monthly subscription; the
    real per-scan Claude cost and what price/credit-count recovers it
    with margin (the same question already deferred for Android's own
    pricing); whether a paid tier changes the "experimental, not
    certified" liability framing the README currently leans on; whether
    free Tesseract stays available forever as a lower tier.
    **Estimates** (focused-work, not calendar time — full breakdown in
    `ClaudePlans/2026-09-20-screen-flow-specification.md`): Android live
    as an informal beta in ~1-2 days; the full shared-account system
    still costs ~5-6 weeks total either way — going Android-first just
    moves a migration step for early beta testers to the end instead of
    an architecture-validation step at the start, judged acceptable
    since the beta group is small.

21. ✅ **UI/UX color/font refresh ported into both codebases — done
    2026-09-21.** The new "Wandering Trails Wagging Tails" teal/purple/
    orange palette + Outfit/DM Sans/Sacramento type (from item #20's
    design system Artifact) replaces the old sunset-orange/trail-green
    palette in `web/src/design-system/tokens.css` and
    `android/.../ui/theme/{Color,Theme,Type}.kt`; `npm run build` and
    `./gradlew compileDebugKotlin` both pass clean. Caught and fixed one
    real accessibility bug while porting: the brand's own tokens forbid
    white text on top of orange or teal, but the old Button/Badge/
    chooser-badge components hardcoded white-on-primary-accent —
    switched to the brand's `on-orange`/`on-teal` (ink) tokens instead.
    **Not done yet**: matching each screen's layout to the fuller visual
    treatment shown in the Artifact canvases — this was a token-level
    port (colors/fonts/shadows/radius), not a re-skin of every
    component's layout.

**Deliberately not on this list**: pricing/pack sizes (intentionally
deferred until real cost/fee data is in hand, not a gap — see
`ARCHIVE_MONETIZATION.md`); React/FastAPI web-app hosting/deployment
(deferred by your own explicit choice, local dev only for now, not a gap
either — Streamlit is hosted, see below).

## 🧪 Tests still outstanding

Living checklist — remove an entry the moment its test actually gets
written; add new entries here as soon as a gap is spotted, not just
mentioned in conversation, so it survives a machine switch. See
`Claude.md`'s "NEXT_STEPS.md Maintenance" section for the standing rule
behind this. Most items that used to live in this section are now either
done (moved to the roadmap above as ✅ entries, several since fully
archived and swept out per the "History archives" note above) or
captured as roadmap items #7-#8 above — check there first.

- **Android guided-scan camera overlay** (item #18) — the two
  hardware-independent tests (guide-rectangle math, EXIF-orientation
  regression) are done; a permission-denied/full-capture-flow
  instrumented test and the landscape-rotation risk itself both still
  need a physical Android test device. Detail in `ARCHIVE_ANDROID.md`.

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
  **Investigated for real, 2026-08-26/27 (BoundOCR)**: automated
  auto-crop (contour/quad detection) was built and tested, and failed
  three separate, real ways across two vehicles; hand-crop diagnostics
  also showed OCR *recognition* quality — not just cropping — is a real,
  unresolved bottleneck for this label style (Tesseract near-total
  garbage regardless of crop quality; EasyOCR better but still blocked
  by small glyph misreads). The fix is still not shipped — see
  `ClaudePlans/2026-08-26-boundocr-report-session-summary.md` for full
  results and remaining options (fix `locate_label`, wire in EasyOCR, or
  a manual crop-box UI).

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
- **Streamlit is deployed to Streamlit Community Cloud** (confirmed
  2026-09-18) — the React/FastAPI web app is still local dev only, by
  explicit choice (see the roadmap's "Deliberately not on this list").
  Since the FastAPI backend is stateless (no database), hosting it too
  would be simple whenever this is picked up — no managed Postgres/
  persistence question to answer, just getting the process running
  somewhere with `apt-get install tesseract-ocr` available.
  - **Real bug found and fixed 2026-09-18**: the Streamlit Cloud deploy
    crashed at import time (`libtk8.6.so` missing — that image has no
    tkinter system library). See `ARCHIVE_WEB_STREAMLIT.md` for the fix.

## Natural next steps, roughly in order

1. **Try it against more real labels.** Only one truck-tag manufacturer
   (Ford) and one trailer manufacturer (Brinkley RV) have been tested.
   Other manufacturers' compliance labels will have different layouts —
   expect to extend `truck_tag_ocr._parse_fields` /
   `trailer_tag_ocr._parse_fields` with more pattern variants as you feed
   it real photos of your actual rig.
2. **Decide on hosting for the React/FastAPI web app** when ready to move
   it off `localhost` too — see the note above, or revisit if
   requirements have changed.
