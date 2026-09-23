# Agent handoff — RigCheck/HDTTools project state (2026-09-22)

This is a resume-from-scratch briefing for a fresh agent picking up this
project with no prior context. It is not a plan awaiting approval — it's
a snapshot of where things actually stand, written after a session that
did a web re-skin, found and diagnosed a real bug, planned a Tesseract
removal, locked in a permanent architecture decision, and swept four
closed roadmap items out of `NEXT_STEPS.md`. Read this first, then read
the specific files it points to — don't re-derive history that's already
written down.

## What this project is

**RigCheck** (repo: `HDTTools`) is a tow-rig safety-check calculator: a
user photographs or manually enters a truck's tag data, a trailer's tag
data, and a CAT scale ticket, and the app computes a pass/fail weight
breakdown (GVWR/GAWR/GCWR margins) against the actual measured weights.
It exists as **three separate product surfaces**, each with a different
purpose and a different OCR backend policy (this split is now a
permanent, decided architecture — see below):

1. **Streamlit** (`streamlit_app/`) — a free, public-service demo,
   already deployed to Streamlit Community Cloud. Self-contained, no
   separate backend process. Uses **Tesseract OCR by default, forever**
   (`HDTTOOLS_OCR_BACKEND` env var, default `"tesseract"`, opt-in
   `"claude"` for manual dev-time comparison only). Will never get
   accounts, credits, or Claude-vision scanning — it is not a lower tier
   of the paid product, it has nothing to migrate to.
2. **Web** (`web/` React+Vite+TS frontend, `src/hdttools/api/` FastAPI
   backend) — the paid-product-in-progress web surface. Local dev only
   today (`localhost:5173` / `localhost:8000`), not hosted anywhere.
   Currently still defaults to Tesseract too (same env var), but that is
   **planned to change** — see item #22 below — because Tesseract
   returns null on realistic un-cropped phone photos and Claude vision
   doesn't.
3. **Android** (`android/`) — native Kotlin/Compose app, fully built
   through Phase 4 (manual entry + optional paid Claude-vision scan).
   Never had a Tesseract path at all — Claude vision only, gated by
   RevenueCat purchases via a Cloudflare Worker (`workers/scan-proxy`).

Web and Android are being built toward **one shared accounts/paywall
system** (item #20, not started) — Streamlit is explicitly and
permanently outside that system.

## Standing project rules (read before touching anything)

These live in `CLAUDE.md` at the repo root and apply for the whole
session, not just this handoff:

- **`uv` for all Python** — never bare `pip`/`python`. `uv add`/`uv
  remove`/`uv run`.
- **TDD is required** for new code and bug fixes — failing test first,
  watch it fail, then minimum code to pass. See `TDD_METHODOLOGY.md`.
  `TESTING.md` governs how tests get categorized (Minor/Major/External)
  and which suites a change needs to re-run.
- **Every question that needs a real answer before proceeding** —
  including "should I commit this?" — goes through `AskUserQuestion`,
  not plain text. Plain-text questions get missed.
- **Planning Procedure**: any time the user asks for a plan, build it in
  Plan Mode with Context/Goal/Steps/Definition of Done/Verification, and
  the instant it's approved, save the full content to
  `ClaudePlans/YYYY-MM-DD-<short-title>.md` before doing anything else.
  This is a standing step of planning itself, not a separate ask.
- **Plan approval ≠ go-ahead to execute.** This user paces execution of
  approved plans against their own usage budget and says explicitly when
  to proceed. Don't start implementing an approved plan just because it
  was approved — item #22 below is a live example of this: fully
  planned, explicitly not started.
- **Never commit without being explicitly asked.** Doc edits, code
  changes, sweeps — all of it sits uncommitted until the user says
  "commit" (or "commit and push").
- **`NEXT_STEPS.md` maintenance discipline** (full detail in
  `CLAUDE.md`'s "NEXT_STEPS.md Maintenance" section): it's a status/
  roadmap file, not a history log. A completed item collapses to one
  terse ✅ line pointing at the matching `ARCHIVE_*.md` for the full
  narrative — full narrative never sits inline for long. Deleting a
  closed item's line entirely (not just collapsing it) requires the
  7-step "Sweeping fully-closed items out entirely" procedure — grep the
  whole repo for citations first, fix living-doc pointers, re-grep to
  confirm zero remain, only then delete, and leave a numbering gap
  (never renumber). This was just done for items #11/#16/#21/#23 this
  session — see below.
- **System tool installs** (winget, standalone installers, Android
  Studio, JDKs) need explicit permission + a location decision (prefer
  non-C: drives) before installing — this does NOT apply to routine
  package-manager installs (`uv add`, `npm install`), which are always
  fine without asking.
- **Human-written content markers** (`<!-- HUMAN-WRITTEN ... -->` /
  `<!-- END HUMAN-WRITTEN -->`) — never edit, reformat, or move text
  between these markers in any file, for any reason.

Also relevant from the user's global (cross-project) memory — see
`MEMORY.md` in the memory store for the full index, but the two most
load-bearing entries for this project right now:
- **TDD and honest failure**: real failures over silent skips, real
  execution over mocked, pause at Red before jumping to Green for
  discussion, report results honestly (no forced xfail).
- **Calibrate urgency to deployment status**: don't use production/
  user-safety framing for a bug before confirming what's actually
  deployed where. Streamlit is live (2026-09-18); Web is local-dev-only.
  A Web bug is not a live incident; a Streamlit bug would be.

## Current git state

Clean working tree on `main` as of this handoff. Most recent commits:

```
50703c4 Plan Web-only Tesseract removal; decide Streamlit keeps it forever; sweep NEXT_STEPS
a8e50bd Re-skin Android and Web screens to match the design canvases (item #23)
2f3a08c Add entitlement/scan-gating research planning docs (item #20)
a692bb1 Gitignore AuditReports/ and locally-fetched skill payloads; commit skills-lock.json
9a2594c Port Wandering Trails Wagging Tails color/font refresh into web and Android
```

Nothing is mid-flight — no dev servers running, no uncommitted changes.

## `NEXT_STEPS.md` — current live roadmap (read this file directly, it's
short and current)

Remaining numbered items (gaps are intentional, never renumber):
**7, 8, 13, 18, 20, 22, 24.** Items #11, #16, #21, #23 were closed and
swept out entirely this session (2026-09-21) — their full history is now
only in `ARCHIVE_ANDROID.md`/`ARCHIVE_WEB_STREAMLIT.md`, not in
`NEXT_STEPS.md` at all. If any doc still cites one of those numbers by
mistake, treat the archive as the source of truth, not a stale citation.

The two items with real, unstarted work and enough context to act on
immediately:

### Item #22 — Drop Tesseract for the Web app (fully planned, not implemented)

- **Decision**: permanent, confirmed 2026-09-21. Web's FastAPI backend
  will always use Claude vision, never Tesseract, regardless of
  `HDTTOOLS_OCR_BACKEND`. Android is unaffected (never had Tesseract).
  Streamlit is explicitly, permanently excluded — see below.
- **Full approved plan**: `ClaudePlans/2026-09-21-drop-tesseract-web-api-only.md`.
  Read it before touching `main.py` — it has the exact file-by-file
  steps, Definition of Done, and Verification checklist already worked
  out. Summary: rewrite `src/hdttools/api/main.py`'s `_extract_fields` to
  drop the `get_ocr_backend()`-driven branch and always call
  `_CLAUDE_EXTRACTORS`; remove `_ocr_upload`/`_TESSERACT_PARSERS`/dead
  imports; add a clear fail-fast error for a missing/invalid
  `ANTHROPIC_API_KEY` (today it's optional since Tesseract is the
  default — once Tesseract is gone, Web can't run without a real key);
  update `tests/test_api.py` (remove 3 Tesseract-branch tests + dead
  monkeypatches + the invalid-env-value test, drop redundant
  `monkeypatch.setenv` lines, collapse duplicate tests, add one for the
  new fail-fast error); update `tests/test_scale_ticket_real_photo.py`
  (remove the real-endpoint-through-Tesseract test, keep the direct
  Tesseract-pipeline test since Streamlit still uses that pipeline);
  update `tests/TESTING.md`'s `test_api.py` row.
- **Explicitly untouched, forever**: `streamlit_app/app.py`,
  `src/hdttools/ocr_common.py`, `truck_tag_ocr.py`/`trailer_tag_ocr.py`/
  `scale_ticket_ocr.py`, the Tesseract install step in the fresh-machine
  checklist.
- **Not started** — per the usage-pacing rule, wait for an explicit
  "implement this" / "let's do item #22" before touching `main.py`.
  Don't infer permission to implement just because the plan exists and
  is approved.
- **Real reproduction case to verify against once implemented**: POST
  `ExampleDocs/scans/truck/f150_blue_goose_uncropped/20260824_141527.jpg`
  to `/api/extract/truck-tag`. Today, with `HDTTOOLS_OCR_BACKEND` unset
  (defaulting to Tesseract), this comes back with every field null — a
  real bug reproduced live 2026-09-21, traced end-to-end (not guessed):
  the API call genuinely succeeds (200 OK), the frontend flow works
  mechanically, and the failure is specifically Tesseract's inability to
  isolate tag text from an un-cropped photo's surrounding clutter
  (`preprocess_image()` never crops; `--psm 6` can't segment it out).
  Claude vision reads the same photo correctly with zero preprocessing.
  Full trace in `ARCHIVE_WEB_STREAMLIT.md`'s matching 2026-09-21 entry.
  Once item #22 ships, the same request (with any/no env var set) should
  come back fully correct — that's the Definition of Done's core check.

### Item #24 — Scanning-animation + double-check confirm step (idea only, not planned)

Surfaced directly from the same #22 bug hunt: today a legitimate
Tesseract null-result and a UI no-op look identical to the user — both
land on a blank Review form with zero signal that OCR even ran. Two
asks, useful separately or together:
- Web's `ProcessingStep.tsx` should show a real "scanning your photo"
  animation (moving dot / swishing color) instead of a static spinner
  ring, so a slow real OCR call doesn't look hung. (Android's processing
  state may want the same treatment — not yet looked at.)
- After extraction, before the plain editable Review form, show an
  explicit "double-check what we read off your photo" confirm
  step/banner — forcing acknowledgment that values came from OCR and may
  need correction.

**This has no plan yet.** No file list, no decision on whether it's a
new wizard sub-step or a banner on the existing screens, and no decision
on whether it needs real per-field OCR confidence data (which doesn't
exist anywhere in the Web pipeline today — see
`ARCHIVE_WEB_STREAMLIT.md`'s item #23 entry). If picked up, run the
Planning Procedure on it first rather than jumping to code.

### Item #20 — Shared accounts + paywall, Android+Web (biggest item, not actively worked)

Full current detail is already written out in `NEXT_STEPS.md` itself —
read it there rather than duplicated here, since it's long and already
current. The short version: Android ships first as an informal sideload
beta; one shared account system (not two) gets built for Android+Web
together; screen mockups exist (`DESIGN_BRIEF.md` + 4 published
Artifacts, one of which — "Wandering Trails Wagging Tails" — is now the
locked-in visual design, already ported into both codebases' token
files). **The single biggest unresolved risk**: entitlement
source-of-truth (does RevenueCat stay Android's system of record with
Stripe reconciled in for Web, or does one system become authoritative
for both?) — two analysis documents exist
(`ClaudePlans/2026-09-21-research-web-hosting-and-entitlement-tradeoffs.md`,
`ClaudePlans/2026-09-21-entitlement-and-scan-gating-unification-impacts.md`)
with recommendations but no decision yet. The user is getting outside
help on this specific question and said it "may take a while" — **don't
proactively chase this one**, wait for the user to bring it back.

Also folded into item #20 this session: the Tesseract-drop decision
(item #22) and its permanent Streamlit exclusion — both recorded there
in full, cross-referenced above.

### Items #7, #8, #13, #18 — lower priority, still open, unchanged this session

Read their entries directly in `NEXT_STEPS.md` if picked up — #7 is
low-priority miscellaneous test/schema gaps, #8 is general coverage
improvement (real current numbers: Web 91.41%, scan-proxy 100%, Android
73.5% Major-only, Python/Streamlit 84.91%), #13 is the constrained-random
OCR regression-testing framework (core built, blocked only on new real
photos existing for new manufacturers), #18 is the Android camera-overlay
spike (paused, needs a physical test phone to resolve one open risk).
None of these were touched this session.

## Recent session narrative (chronological, 2026-09-21)

For anyone who wants the "how did we get here" behind the current state
(not required reading to resume work, but useful if something looks
surprising):

1. Executed the Web half of the screen re-skin (item #23) — built a new
   `Footer.tsx`, restyled `Header.tsx`/`StepPills.tsx`/`Dashboard.tsx`/
   `History.tsx`/5 wizard screens to match the "RigCheck Web" design
   Artifact, preserving all existing interaction behavior (visual re-skin
   only, confirmed as a standing constraint via `AskUserQuestion` before
   starting). Verified via `npx tsc -b`, `npx vitest run` (71/71 pass),
   `npm run build`, and a live `puppeteer-core` walkthrough against the
   real running app (installed ad hoc into the session scratchpad,
   pointed at the machine's real Chrome — no Chromium download needed).
   Gotcha hit: Vite must run on port 5173 exactly, because FastAPI's CORS
   allow-list in `main.py` hardcodes that origin.
2. User reported a real truck-tag scan came back blank. Diagnosed (not
   guessed) end-to-end: ruled out the frontend/backend plumbing first via
   a clean-photo puppeteer walkthrough, then found the real cause was
   Tesseract's total failure on an un-cropped photo (see item #22 above
   for the full trace). Fixed only as a session-only
   `HDTTOOLS_OCR_BACKEND=claude` env override for the user's immediate
   retest — explicitly communicated as temporary, not a real fix. The
   requested UX improvement (scanning animation + confirm step) was
   logged as item #24 rather than implemented, per the user's own
   instruction to just track it for now.
3. User confirmed the app looked good on retest; both dev servers were
   shut down, and the re-skin + entitlement-research docs were committed
   and pushed (`a8e50bd`, `2f3a08c`).
4. Ran the Planning Procedure for item #22 (drop Tesseract). During
   planning, surfaced a real cost-exposure risk via `AskUserQuestion`
   (dropping Tesseract everywhere would make every Streamlit scan an
   unbounded-cost Claude API call on a service that's live and public
   with zero cost gating) — user narrowed scope to Web-only. Plan
   approved, saved to `ClaudePlans/2026-09-21-drop-tesseract-web-api-only.md`.
   Code implementation explicitly not started (usage-pacing rule).
5. User asked an exploratory question about permanently keeping
   Streamlit on Tesseract (pros/cons, impacts) — answered as analysis,
   not implementation. User then confirmed it as a real, permanent
   decision: Streamlit was always meant to be a free public-service demo,
   never a lower tier of the paid product. This required updating every
   downstream doc that had encoded the old "Web-only for now, blocked on
   item #20" framing — `NEXT_STEPS.md` items #16/#20/#22, the "Tests
   still outstanding"/"Known limitations" sections, and the already-saved
   `ClaudePlans` plan file itself.
6. User confirmed closing out items #11/#16/#21/#23 in `NEXT_STEPS.md`.
   Ran the full 7-step sweep procedure: confirmed all four were already
   archived (item #21 had no prior archive narrative anywhere, so new
   matching entries were written into `ARCHIVE_ANDROID.md`/
   `ARCHIVE_WEB_STREAMLIT.md` first, reconstructed from `git show` on the
   commit that did that work); grepped every `.md` file in the repo for
   citations; rewrote ~13 prose citations across
   `FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md` and `tests/TESTING.md`
   (including two, #11 and #16, that a *prior* session had explicitly
   deferred rewriting as "not worth it" — this time done because the user
   asked for pointers to be updated, not just items removed); re-grepped
   to confirm zero remaining living-doc citations; deleted the four
   `NEXT_STEPS.md` lines, leaving numbering gaps. Also caught and fixed
   three stale "uncommitted, pending approval" claims left over in the
   archives from before this session's earlier commits landed.
7. Wrote a full session-state snapshot into durable memory
   (`project_android_web_release_sequencing.md` in the memory store) and
   committed/pushed the sweep changes (`50703c4`).

## Where to look for detail, by topic

- **Exact current roadmap**: `NEXT_STEPS.md` (read directly — it's the
  living source of truth, this handoff summarizes it but isn't a
  substitute for it if you're about to edit it).
- **Full Web/Streamlit narrative history** (bug hunts, the re-skin, the
  Tesseract decision): `ARCHIVE_WEB_STREAMLIT.md`.
- **Full Android narrative history**: `ARCHIVE_ANDROID.md`.
- **Test methodology and per-platform coverage numbers**: `TESTING.md`
  (root), `web/TESTING.md`, `android/TESTING.md`,
  `workers/scan-proxy/TESTING.md`, `tests/TESTING.md`.
- **TDD workflow specifics per platform**: `TDD_METHODOLOGY.md`.
- **Machine-specific tool paths** (Android SDK/emulator/AVD name,
  Tesseract, Node, `uv`): `DEV_ENVIRONMENT.md`.
- **Screen mockups / design system**: `DESIGN_BRIEF.md` (repo, canonical
  screen inventory) plus 4 published Artifacts referenced there and in
  the memory file (design system "Wandering Trails Wagging Tails", plus
  RigCheck Web / RigCheck Android / Homepage design canvases).
- **All approved plans, chronological**: `ClaudePlans/*.md` — this
  directory. The two most relevant to resuming right now are
  `2026-09-21-drop-tesseract-web-api-only.md` (item #22) and
  `2026-09-21-screen-reskin-refresh-screens.md` (item #23, now fully
  shipped — reference only, not active).
- **Session-durable memory** (for the agent's own recall across
  sessions, not part of the git repo): the memory store's
  `project_android_web_release_sequencing.md` has the same narrative as
  this handoff plus older sequencing decisions (Android-first, shared
  accounts) in more depth; `MEMORY.md` in that store is the index of
  every memory file.

## Immediate next actions, in likely priority order

1. If the user says to proceed on item #22: read
   `ClaudePlans/2026-09-21-drop-tesseract-web-api-only.md` in full, follow
   TDD (write/adjust the failing tests described in its Steps section
   first), then implement `main.py`'s rewrite, then run its Verification
   checklist exactly as written (including the live re-POST of the
   reproduction photo with the env var both unset and explicitly set to
   `tesseract`, and the Streamlit-unaffected check).
2. If the user wants to move on item #24: run the Planning Procedure
   first — this has no plan yet, don't start editing
   `ProcessingStep.tsx`/`ReviewStep.tsx` without one.
3. If the user brings back item #20's entitlement question: re-read the
   two analysis docs listed above before responding — don't re-derive
   the tradeoffs from scratch, they're already worked out in detail.
4. Otherwise, this project has no pending asks — treat any new request
   as a fresh task against the state described above.
