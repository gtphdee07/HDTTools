# RigCheck — where things stand

Working notes for picking this back up on another machine. Written 2026-08-13.

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
