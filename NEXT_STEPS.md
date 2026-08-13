# RigCheck — where things stand

Working notes for picking this back up on another machine. Written 2026-08-13.

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

## What exists right now

**Frontend** (`web/`, React + Vite + TS): all 7 RigCheck screens, wired to a
real backend (no more mocked data). `npm install && npm run dev` — runs on
`localhost:5173`.

**Backend** (`src/hdttools/api/`, FastAPI): OCR-only extraction (Tesseract,
no `ANTHROPIC_API_KEY`) for truck tags, trailer tags, and CAT scale
tickets, plus rig/check persistence in the same `hdttools.db` SQLite file
the CLI tool uses. `uv run uvicorn hdttools.api.main:app --reload --port
8000` — runs on `localhost:8000` (`/docs` for Swagger UI).

Both are already set up in `.claude/launch.json` in the **RVSafetyCheck**
directory (not this repo) if you're continuing in that same Claude Code
session/workspace — otherwise just run the two commands above.

Full pipeline is verified end-to-end against the real photos in
`ExampleDocs/` (not synthetic data): upload → OCR extract → editable
review → server-computed pass/fail verdict → persisted check → shows up in
History/Dashboard. 50 backend tests pass (`uv run pytest -q`).

## Fresh-machine setup checklist

On a machine that hasn't run this before:
1. `brew install uv tesseract node` (all three were missing on this Mac
   when this phase started — don't assume they're present).
2. `cd HDTTools && uv sync` (Python deps) and `cd web && npm install` (JS
   deps).
3. `git pull` to get this commit if you're setting up a second machine.

## Known limitations (intentional, not bugs)

- **No "create new rig" UI.** The backend seeds one placeholder rig ("Big
  Blue (Ford F-350)" / "The Nest (Grand Design 2930RL)") on first run; the
  wizard only lets you pick from existing rigs. You decided to defer this
  rather than build rig-management CRUD this round.
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
  round. When ready: Render was the earlier recommendation (Docker-based,
  so `apt-get install tesseract-ocr` just works; managed Postgres add-on
  if you want to move off SQLite).

## Natural next steps, roughly in order

1. **Try it against more real labels.** Only one truck-tag manufacturer
   (Ford) and one trailer manufacturer (Brinkley RV) have been tested.
   Other manufacturers' compliance labels will have different layouts —
   expect to extend `truck_tag_ocr._parse_fields` /
   `trailer_tag_ocr._parse_fields` with more pattern variants as you feed
   it real photos of your actual rig.
2. **Decide on rig creation** if the single seeded placeholder rig starts
   to feel limiting — needs a small form (truck name + trailer name) in
   `web/src/wizard/RigStep.tsx` plus a `POST /api/rigs` endpoint
   (`src/hdttools/api/main.py` + `store.py`).
3. **Decide on hosting** when ready to move off `localhost` — see the
   Render note above, or revisit if requirements have changed.
4. **Postgres migration** would come with hosting, if you want checks to
   survive across deploys rather than living in a local SQLite file.
5. Nothing currently blocks day-to-day local use — the app is functional
   as-is for testing your own rig's numbers.
