# RigCheck — where things stand

Working notes for picking this back up on another machine. Written 2026-08-13.

## 🗣️ Open thread: Android monetization (unresolved — pick up here)

Started planning the Android app's implementation. First topic was whether
to charge for an optional Claude-vision-powered "scan instead of type"
feature (as opposed to the native app's default manual-entry-only flow,
which stays free and fully offline per `ANDROID_DESIGN_BRIEF.md`). Not
decided yet — the clarifying questions below were asked and dismissed
without an answer, so this is genuinely open, not settled.

**Cost baseline** (documented pricing, not a measured count): a full
3-photo check (truck tag + trailer tag + scale ticket) via Claude vision
costs roughly **$0.01 on Haiku 4.5** or **$0.03 on Claude Sonnet 5** in raw
API spend — each image is a small extraction task (~1,600 image tokens at
standard resolution + a short prompt + compact JSON output), not a
high-res/reasoning-heavy call. Haiku 4.5 is very likely sufficient for
this — structured field extraction from a printed label is squarely its
use case. This is compute cost only; doesn't include Play Store fees or
your own margin.

**Toolkit options surveyed:**
- **Google Play Billing Library** (mandatory Billing Library v8 by
  2026-08-31 for anyone using it) — required historically, but as of
  **2026-06-30** Google now permits external payment methods for US/UK/EEA
  developers (post Epic v. Google), so this is no longer the only
  compliant path.
- **RevenueCat** — wraps Play Billing (+ Apple StoreKit), handles
  entitlement/receipt validation for you. Built for subscription gating,
  not fine-grained metered usage.
- **Stripe / Stripe Billing** — now legitimate on Play Store per the above
  policy change; Stripe Billing specifically supports true metered/
  usage-based charges if you want pay-per-scan pricing instead of a flat
  subscription.

**The part that matters more than the billing rail:** `ANTHROPIC_API_KEY`
can never ship inside the Android app (trivially extracted from the APK).
Enabling Claude-vision scanning requires a backend that holds the key,
checks entitlement, and proxies the request — reopening the "no backend"
decision in `ANDROID_DESIGN_BRIEF.md`.

**My recommendation, not yet accepted or rejected:**
- Flat monthly subscription (not metered pay-per-scan) — simpler, Play
  Billing/RevenueCat handle it natively; metering adds real complexity for
  a cost difference that's probably marginal at likely volume (~$0.01–0.03
  per check).
- Scan is an **optional paid add-on**, not a rework of the whole app — the
  native manual-entry flow stays the default, free, fully-offline path;
  a backend exists only for this one feature.
- Google Play Billing (via RevenueCat to cut plumbing) for the
  subscription, with a small backend (could reuse the FastAPI pattern from
  `src/hdttools/api/`) that just checks entitlement before proxying to
  Claude.

**Next step:** resume this conversation — decide flat-vs-metered and
optional-addon-vs-architecture-rework before writing any Android code.

## ⏭️ Next up: fix the tongue-weight fallback assumption (web + Streamlit)

Discovered while reviewing the Android design handoff (`android/design/`,
not version-controlled — see its `README.md` for the full screen list):
the Android design's blank-field fallback for stand-alone weight assumes
`trailer_axle_lb` is **80% of the trailer's actual total weight** (a
standard fifth-wheel/gooseneck pin-weight rule of thumb — pin weight is
commonly cited as 15–25% of trailer weight). The web/Streamlit apps'
current fallback — when stand-alone weight is blank, just skip the
tongue-weight adjustment entirely — isn't merely less accurate, **it's
wrong in the unsafe direction**: it implicitly assumes tongue weight is
0%, which can make an overweight trailer look compliant on the "Trailer
Total (GVWR)" check. Tongue weight physically transfers onto the truck's
axles when hitched and never appears in `trailer_axle_lb` — so comparing
`trailer_axle_lb` alone against the trailer's GVWR (a *total*-weight
rating) understates the real number whenever tongue/pin weight isn't
separately supplied.

**Decided fix**: adopt the Android design's 80% assumption as the correct
default everywhere, not a platform quirk to reconcile away.

- `src/hdttools/api/breakdown.py`'s `compute_breakdown()`: when
  `standalone_weight_lb` is blank, replace "use `trailer_axle_lb` alone"
  with `trailer_total_actual = trailer_axle_lb / 0.8` (an *estimate* of
  total trailer weight from the axle reading). Note text should say so
  plainly, e.g. "Estimated total weight — assumes the axle reading is 80%
  of actual trailer weight; enter your truck's stand-alone weight for an
  exact figure." The exact-figure path (`standalone_weight_lb` provided)
  stays as already implemented — computed tongue weight added to
  `trailer_axle_lb`, clamped at 0.
- Worth pulling `0.8` out as a named constant (e.g.
  `DEFAULT_AXLE_TO_TOTAL_RATIO`) rather than a magic number, since
  Android's eventual Kotlin port of `compute_breakdown` will need the same
  value — a single documented source of truth is easier to keep in sync
  than a comment in two languages.
- `tests/test_breakdown.py`'s "tongue weight omitted" case currently
  asserts the old (unsafe) unadjusted behavior — needs updating to expect
  the `/0.8` estimate instead. Add a case confirming the *provided*
  stand-alone-weight path is unaffected by this change.
- Streamlit imports `compute_breakdown` directly (no separate copy of this
  logic) — fixing `breakdown.py` fixes both web and Streamlit in one
  place, nothing platform-specific to duplicate.
- Android's design already bakes in this behavior as the intended default
  — nothing to change there once built, just make sure the eventual
  Kotlin port uses the same ratio.
- Re-verify against the real `ExampleDocs/` photos after: leave
  stand-alone weight blank, confirm "Trailer Total (GVWR)" now shows the
  inflated estimate and the new note wording, instead of today's
  unadjusted `trailer_axle_lb`.

## ✅ Done: portability pass (implemented 2026-08-13)

Full plan at `~/.claude/plans/i-would-like-to-toasty-dusk.md` on the
machine that ran it (won't exist elsewhere — summarized here). Goal:
make RigCheck portable to additional hosting types (Streamlit, eventually
Android), decided as **no shared hosted backend** — each platform is
self-contained.

- **Web app (`web/` + `src/hdttools/api/`) is now database-free.**
  `api/store.py` and the SQLite `rigs`/`checks` tables are gone.
  `POST /api/checks` became stateless `POST /api/breakdown` (no `rig_id`,
  no persistence). Rigs are now a client-side "last 5" list
  (`web/src/recentRigs.ts`, `localStorage`, keyed by a user-typed
  nickname, storing the full reviewed truck/trailer data so picking a
  remembered rig skips straight to the Scale Ticket step). Check history
  is session-only (gone on refresh) — this was a deliberate simplification,
  not an oversight.
- **New self-contained Streamlit app** (`streamlit_app/`) — same wizard
  flow, single Python process, no FastAPI/HTTP hop, imports
  `hdttools`'s OCR-parsing and breakdown logic directly. Recent rigs
  persist to `~/.rigcheck/recent_rigs.json` instead of a database. See
  `streamlit_app/README.md`.
- **`hdttools/__init__.py`** now tolerates a missing `tkinter` (wraps the
  desktop CLI reader imports in try/except) since it isn't always present
  on headless/minimal Python builds — relevant if Streamlit or the API
  ever runs somewhere without it.
- **`ocr_common.py`**'s Tesseract path detection now also checks common
  macOS/Linux install locations, not just Windows.
- **Android**: high-level roadmap only, not started. Decided: fully
  native (Kotlin/Compose), no OCR at all — reference images + manual
  entry instead, no network/API-key dependency. Needs its own
  Android Studio/Gradle project (doesn't exist in this repo).
  `compute_breakdown`/`verdict_for` would need a Kotlin port —
  `tests/test_breakdown.py`'s scenarios are the shared spec to check any
  port against.

54 backend tests pass; frontend typechecks/builds clean; Streamlit
smoke-tested end-to-end against the real `ExampleDocs/` photos.

**Note found during this pass, not fixed:** `ExampleDocs/GooseTag.jpg`
and `ExampleDocs/AddieTag.jpg` are swapped relative to what their names
suggest — `GooseTag.jpg` is actually the Brinkley RV **trailer** tag and
`AddieTag.jpg` is the Ford **truck** tag (opposite of the CAT ticket's
"TRACTOR # GOOSE TRAILER # ADDIE"). Didn't rename them since that wasn't
part of the ask, but any future test/demo code should use them this way
around.

## ✅ Done: axle-count / tongue-weight plan (implemented 2026-08-13)

Two logic-fault fixes were designed and approved in the session that wrote
this file, and implemented in the following session (different machine,
after `git pull`). Plan text below is kept as a record of what was built;
see `tests/test_breakdown.py` for the five tests covering all four
scenarios (default axle count, custom axle count, tongue weight omitted,
tongue weight provided, clamp-at-0), plus updated `models.py`,
`database.py`, `api/schemas.py`, `mockData.ts`, and `types.ts`. All 55
backend tests pass; frontend typechecks and builds clean.

**The two faults:**
1. `compute_breakdown()` hardcodes a 2-axle trailer (`gawr_per_axle * 2`)
   regardless of the trailer's actual axle count.
2. "Trailer Total (GVWR)" always excludes tongue weight (an acknowledged
   approximation from the original design — no tongue-weight field exists
   on either tag).

**Agreed fix**, both fields **optional with graceful fallback** to today's
behavior when left blank, and the tongue-weight estimate **folds into the
existing "Trailer Total (GVWR)" card** rather than getting a new one:

- Add `axle_count: int | None = None` to `TrailerTagData`
  (`src/hdttools/models.py`) — user-typed during trailer review (not
  OCR-derivable), field def added to `web/src/mockData.ts`'s `MODULES[2]`.
  `breakdown.py`: `gawr_per_axle * int(trailer.get("axle_count") or 2)`,
  with a note that's dynamic ("Trailer axle rating: N axle(s)...") when
  provided vs. today's "Assumes a 2-axle trailer..." when defaulted.
- Add `standalone_weight_lb: float | None = None` to `TruckTagData`
  (lb-only, no `_kg` counterpart — matches `ScaleTicketData`'s weight
  fields) — user-typed during truck review, field def added to
  `MODULES[1]`. `breakdown.py`: when provided, `tongue_weight =
  max(0.0, (steer + drive) - standalone_weight_lb)` (clamped at 0 — a
  negative estimate is physically meaningless and would understate the
  trailer total, the wrong direction for a safety check), and
  `trailer_total_actual = trailer_axle + tongue_weight` with an updated
  note explaining the estimate. When blank, keep today's exact behavior
  and note unchanged.
- Mirror both new fields into `src/hdttools/database.py`'s
  `_TRAILER_TAG_COLUMNS`/`_TRUCK_TAG_COLUMNS` and
  `src/hdttools/api/schemas.py`'s `TrailerTagOut`/`TruckTagOut`, for
  consistency (CLI persistence, API schema completeness) even though OCR
  won't populate them.
- **No other frontend code changes needed** — `ReviewStep.tsx` and
  `App.tsx`'s `createCheck` already handle `MODULES[step].fields`
  generically, so the two new field defs are sufficient to get working
  input rows end to end.
- New `tests/test_breakdown.py` (currently `compute_breakdown`/
  `verdict_for` only have indirect coverage via one `test_api.py` case):
  default-2-axle case, custom axle count, stand-alone weight omitted vs.
  provided, and the clamp-at-0 edge case (stand-alone weight larger than
  the hitched total).
- Verify against the real `ExampleDocs/` photos again after: blank vs.
  filled-in axle count changes the "Trailer Axle(s)" limit/note correctly;
  blank vs. filled-in stand-alone weight changes the "Trailer Total" actual
  value/note correctly.

**Explicitly deferred** (your idea, agreed as a good eventual direction
but not this round): reading a *second* CAT scale ticket (unhitched) so
`standalone_weight_lb` comes from an actual measurement instead of a typed
number. The math in `compute_breakdown` won't need to change again for
this — only where `standalone_weight_lb` comes from.

**Superseded by the section above**: the "when blank, skip the
tongue-weight adjustment entirely" fallback described below turned out to
be unsafe (implicitly assumes 0% tongue weight) — see "Next up" at the top
of this file for the fix.

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

Both web-app processes are already set up in `.claude/launch.json` in the
**RVSafetyCheck** directory (not this repo) if you're continuing in that
same Claude Code session/workspace — otherwise just run the commands
above.

Full pipeline is verified end-to-end against the real photos in
`ExampleDocs/` (not synthetic data): upload → OCR extract → editable
review → computed pass/fail verdict → shows up in session History/
Dashboard. 54 backend tests pass (`uv run pytest -q`).

## Fresh-machine setup checklist

On a machine that hasn't run this before:
1. `brew install uv tesseract node` (all three were missing on this Mac
   when this phase started — don't assume they're present).
2. `cd HDTTools && uv sync` (Python deps) and `cd web && npm install` (JS
   deps).
3. `git pull` to get this commit if you're setting up a second machine.

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
- **No mobile layout, no drag-and-drop upload** (click-to-browse file input
  only) — matches the original design handoff's stated scope.
- **Not hosted anywhere yet** — local dev only, per your instruction this
  round. Since the backend is now stateless (no database), hosting it is
  simpler than before — no managed Postgres/persistence question to
  answer, just getting the process running somewhere with
  `apt-get install tesseract-ocr` available (Render was the earlier
  recommendation, Docker-based).

## Natural next steps, roughly in order

0. **The tongue-weight fallback fix at the top of this file** — do this
   first, it's a correctness/safety issue in the shipped app, not just a
   nice-to-have.
1. **Try it against more real labels.** Only one truck-tag manufacturer
   (Ford) and one trailer manufacturer (Brinkley RV) have been tested.
   Other manufacturers' compliance labels will have different layouts —
   expect to extend `truck_tag_ocr._parse_fields` /
   `trailer_tag_ocr._parse_fields` with more pattern variants as you feed
   it real photos of your actual rig.
2. **Android**, if you want to pick that up — see the portability section
   above for the decided approach (native, no OCR, reference-image +
   manual entry). Needs an Android Studio/Gradle project set up first;
   nothing in this repo blocks starting that.
3. **Decide on hosting** when ready to move off `localhost` for the web
   app — see the note above, or revisit if requirements have changed.
4. Nothing currently blocks day-to-day local use — both the web app and
   the Streamlit app are functional as-is for testing your own rig's
   numbers.
