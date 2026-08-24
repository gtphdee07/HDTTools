# Streamlit real-photo walkthrough + Python coverage widening (roadmap item #6)

## Context

Item #6 in `NEXT_STEPS.md` has been flagged as "the actual open gap for
a long time": a real, `ExampleDocs/`-photo-driven `AppTest` walkthrough
for the Streamlit desktop app. The existing precedent —
`tests/test_streamlit_app.py::test_scanning_a_real_tow_vehicle_only_photo_fills_in_standalone_weight`
— already proved the pattern's value: it drives the *real* (non-mocked)
`app.py` through real Tesseract OCR against a real `ExampleDocs/` photo,
and it's what caught a genuine stale-widget-value bug that a mocked or
function-level test structurally could not see (documented in
`ARCHIVE_WEB_STREAMLIT.md`). But that existing test only covers **one**
module (the standalone tow-vehicle-only scale ticket) in isolation. The
actual gap: nothing yet drives all **three** modules — truck tag,
trailer tag, and a full (non-standalone) scale ticket — through the real
app with real photos, in one continuous walkthrough to Results. Every
existing "full walkthrough" test in this repo (Streamlit and Web both)
uses the *zero-image, skip-everything* path — real images were never
exercised end-to-end together.

Bundled in, per the 2026-08-23 roadmap decision: widen Python coverage's
scope to include `streamlit_app/`. This can't be meaningfully separated
from item #4a (wiring `--cov` into a real run command at all) — right
now `pyproject.toml`'s `[tool.coverage.run]` only scopes to
`src/hdttools`, and `uv run pytest -q` never even passes `--cov`, so
literally zero coverage numbers exist anywhere in this repo's Python
side yet. Item #4a is described as "nearly free" (`pytest-cov` is
already a dev dependency); doing it alongside item #6 means the new
walkthrough test's own coverage contribution to `streamlit_app/` is
visible immediately as a real number, not measured cold later with
nothing to compare against.

## Goal

A new `tests/test_streamlit_app.py` walkthrough test that drives the
real `app.py` through `AddieTag.jpg`, `GooseTag.jpg`, and
`CatScale-Ticket.jpg` (all three `ExampleDocs/` photos not already used
by another real-photo test), via real Tesseract OCR, module by module,
to a real Results verdict — backed by a shared golden-data file that
also powers a new parametrized real-photo OCR-accuracy test — plus
real, wired-up Python coverage numbers that include `streamlit_app/`,
documented as a repeatable command.

## Golden ground-truth data, not OCR-guessed values

Earlier drafts of this plan proposed running OCR blind and pinning
whatever came out as "correct." **Wrong methodology, corrected**: the
user can supply real ground-truth field values (what's actually printed
on each physical tag/ticket) directly. That's what
`test_scale_ticket_real_photo.py`'s existing numbers actually are too —
its comment says outright "real Tesseract output on this real photo
gets every one of them right," i.e. the asserted values are verified
ground truth, and the test proves OCR reads them correctly — not values
merely captured from a first OCR run and rubber-stamped. The new tests
must follow the same discipline: assert against known-correct values, so
a future OCR regression (a Tesseract version bump, a preprocessing
change) is caught as a real accuracy failure, not silently redefined as
correct.

## Extensibility: supporting more brands/photos later

The user asked what this needs to look like to grow — more truck/
trailer brands, more scale-ticket formats, with the walkthrough
eventually exercising a variety of truck/trailer combinations rather
than always the same one pairing. One critical constraint the user
flagged directly: **a scale ticket's weights are physically real only
for the specific truck+trailer combination that was actually weighed
together** — a truck tag and a trailer tag can be independently real
and correct while still being an invalid *pairing* if the accompanying
scale ticket wasn't actually weighed with that exact pair. So this
can't be "one flat pool of interchangeable photos" — it has to
distinguish **individual document ground truth** (fine to test
independently) from **valid rig tuples** (a matched truck+trailer+scale
triple from one real weighing event, which is what a walkthrough
producing a real verdict actually needs).

Proposed design, reusing this repo's own existing convention
(`test-vectors/breakdown_cases.json`'s shared-JSON-vectors pattern,
just applied to OCR ground truth instead of breakdown math), split into
two parts:

- **New file: `ExampleDocs/golden_fields.json`**, with a self-documenting
  `_readme` (matching `breakdown_cases.json`'s own style) and two
  top-level sections:
  - `"photos"`: one entry per real photo file (`{doc_type, fields}`,
    keyed by filename) — independent ground truth for what OCR should
    read off *that specific document*, regardless of what it's paired
    with. This is what the accuracy test (below) parametrizes over.
  - `"rigs"`: a list of **valid, physically-coherent tuples** — each
    one names a `truck_photo`, `trailer_photo`, and `scale_photo` that
    were genuinely weighed together in real life, plus the real
    verdict that combination should produce. Only one entry today
    (`AddieTag.jpg` + `GooseTag.jpg` + `CatScale-Ticket.jpg`) — this is
    the list a future combination gets appended to.
  - Both sections are the **single source of truth** — the accuracy
    test and the walkthrough test both read from this one file, so no
    value is hand-duplicated across test files.
- **New parametrized accuracy test** (new file, e.g.
  `tests/test_real_photo_ocr_accuracy.py`) — `@pytest.mark.parametrize`
  over `golden_fields.json`'s `"photos"` entries: run real OCR, call
  the matching `_parse_fields` (`truck_tag_ocr`/`trailer_tag_ocr`/
  `scale_ticket_ocr`, chosen by `doc_type`), assert the extracted
  fields match the golden ones. Independent per-photo — no rig
  validity needed here. **Closes item #7's already-flagged "truck tag /
  trailer tag real-photo OCR pytest coverage" gap as a direct side
  effect** of this same data.
- **Walkthrough test parametrized over `"rigs"`, not `random.choice`**:
  the user's ask was for the walkthrough to eventually exercise varied
  truck/trailer combinations rather than always the same pairing. True
  runtime randomness in a test is the wrong mechanism for that though —
  it makes failures non-reproducible and silently skips untested
  combinations on any given run. `@pytest.mark.parametrize` over every
  entry in `"rigs"` gets the actual goal (every known-valid combination
  genuinely exercised, and a growing pool means growing coverage) with
  full determinism: every rig runs every time, a failure always
  reproduces, and CI-style tooling later can still shuffle *which*
  parametrized case runs first without losing coverage. Today, with one
  rig, this is one test case — functionally identical to a single
  hardcoded walkthrough, but already the right shape for when a second
  rig exists.
- **What "adding a new combination" actually requires**: not just one
  new photo. A new, complete, physically-real `(truck_photo,
  trailer_photo, scale_photo)` triple — three real photos from one
  real weighing event — plus their three `"photos"` ground-truth
  entries and one new `"rigs"` entry with the real resulting verdict.
  Reusing an existing truck or trailer photo with a *different* scale
  ticket is only valid if that scale ticket really was that exact
  combination weighed together — not assumed compatible by default.
- `ExampleDocs/` itself stays flat for now (5 files today, 3 more with
  this plan) — if it grows enough to be unwieldy, subfolders by
  doc type (`truck_tags/`, `trailer_tags/`, `scale_tickets/`) would be
  the natural next step, with `golden_fields.json` gaining a `path`
  field instead of assuming everything sits directly in `ExampleDocs/`.

## Steps

1. **`ExampleDocs/golden_fields.json`** — new shared golden-data file
   (two-part schema above: `"photos"` + `"rigs"`), populated with the
   ground-truth field values the user provides for `AddieTag.jpg`
   (truck), `GooseTag.jpg` (trailer), and `CatScale-Ticket.jpg` (scale)
   — real values transcribed from the physical tags/ticket, not OCR
   output — plus one `"rigs"` entry confirming these three really were
   one real weighing event, and the real verdict that combination
   produces. This is the one piece of this plan that depends on the
   user directly (nothing to derive from the codebase).
2. **New parametrized test** (`tests/test_real_photo_ocr_accuracy.py`)
   — one case per `"photos"` entry: real OCR pipeline (same technique
   as `test_scale_ticket_real_photo.py`), call the matching
   `_parse_fields`, assert against the golden values. Closes item #7's
   truck/trailer real-photo OCR gap as a side effect of this same data.
3. **`tests/test_streamlit_app.py`** — new test, parametrized over
   `"rigs"` (one case today), e.g.
   `test_full_walkthrough_with_real_photos_reaches_a_real_verdict[addie_and_goose]`:
   - Start a rig via the existing `_start_test_rig` helper.
   - For each module in order (truck, trailer, scale): drive
     `at.file_uploader(key=f"upload_{module_key}").set_value((filename,
     photo_bytes, mime_type)).run()` with that rig's real photo, assert
     `not at.exception`, assert the real extracted fields landed in
     `at.session_state[module_key]` (spot-check a couple of fields
     against `golden_fields.json`, not every field), then click
     `continue_{module_key}` and rerun.
   - Click through the disclaimer (`"I Understand — Continue"`, matching
     `_show_disclaimer`'s existing button).
   - At Results: assert no exception, and assert the specific verdict
     recorded on this rig's `"rigs"` entry (computed by hand from the
     golden values against `verdict_for`'s known thresholds when the
     entry was written, not guessed at test-write time) — given real,
     complete data, this should land on an actual pass/fail/warning
     tone, not the "Not Enough Information" state the existing
     skip-tests already cover.
   - If real OCR against these photos doesn't match `golden_fields.json`
     cleanly (a genuine misread), that surfaces as a failure in the new
     accuracy test (step 2) first — follow this project's TDD/honest-
     failure convention: if it's a real app-level bug, fix it and note
     it in `ARCHIVE_WEB_STREAMLIT.md` (matching the standalone-scan
     test's own precedent); if it's an inherent OCR-accuracy limit on
     this particular photo, that's real, valuable information to record
     there too, not to paper over.
4. **`pyproject.toml`** — two changes: widen
   `[tool.coverage.run]`'s `source` to `["src/hdttools", "streamlit_app"]`,
   and wire `--cov` into an actual run path (item #4a) — either a
   documented `uv run pytest --cov` invocation or a `[tool.pytest.ini_options]`
   `addopts` default, whichever this repo's existing convention favors
   once checked against how `android`'s coverage docs framed the
   equivalent decision (real task names/paths, not assumed).
5. **Run for real, confirm real non-zero numbers**: `uv run pytest -q`
   (regression: still passes; count goes from 95 to 99+ — 1 walkthrough
   + 3 parametrized accuracy cases); then the real coverage command,
   confirm `streamlit_app/app.py` shows real non-zero coverage (expect
   it measurably higher than before, since the new walkthrough
   exercises far more of `_module_step`/`_extract_fields`/
   `_results_step` than existing tests did alone).
6. **`tests/TESTING.md`** — new table rows for both new test files,
   categorized per this file's existing scheme (the walkthrough is
   **Interaction** + real-photo, matching `test_streamlit_app.py`'s
   existing entry's tagging style; the accuracy test is **Function** +
   real-photo + parametrized, matching `test_scale_ticket_real_photo.py`'s
   style). Add a "Coverage" note mirroring `android/TESTING.md`'s
   pattern: real command, real path, real numbers, once resolved in
   step 5. Also document `golden_fields.json`'s existence and the
   "add a photo + a JSON entry, no new code" extension path.
7. **`NEXT_STEPS.md`** — flip item #6 to a single terse ✅ line (per
   `Claude.md`'s now-explicit core-file rule) pointing at
   `ARCHIVE_WEB_STREAMLIT.md`; item #4a's checkbox also resolves since
   its work is now done as part of this, and item #7's truck/trailer
   real-photo bullet gets removed (closed as a side effect, not
   deferred). Full narrative — the golden data, what the accuracy test
   found, any bug found and fixed, the real coverage numbers — goes in
   `ARCHIVE_WEB_STREAMLIT.md`, not here.

## Files

- `ExampleDocs/golden_fields.json` (new — ground truth, user-provided)
- `tests/test_real_photo_ocr_accuracy.py` (new — parametrized accuracy)
- `tests/test_streamlit_app.py` (new walkthrough test)
- `pyproject.toml` (coverage source widened; `--cov` wired in)
- `tests/TESTING.md` (new table rows, Coverage section)
- `NEXT_STEPS.md` (items #6, #4a → collapsed/done; #7's truck/trailer
  real-photo bullet removed)
- `ARCHIVE_WEB_STREAMLIT.md` (full narrative, per `Claude.md`'s archive
  discipline rule — including if a real bug or a real OCR-accuracy
  limitation turns up)

No changes to `streamlit_app/app.py` itself expected — this is
test/tooling work — unless step 2/3 surfaces a genuine bug, in which
case it gets fixed as part of this, not deferred.

## What "done" means

- `ExampleDocs/golden_fields.json` holds real, user-verified ground
  truth for all three new photos — not OCR output rubber-stamped as
  correct.
- The new parametrized accuracy test proves real Tesseract OCR actually
  extracts those golden values correctly from the real photos (or
  documents exactly where it doesn't, as a real, recorded limitation).
- The new AppTest walkthrough genuinely uploads all three real photos
  through the real, unmocked `app.py`, via real Tesseract OCR, all the
  way to a real Results verdict computed from the golden data — not
  skipped, not mocked, not a guessed expected value.
- Both new test files read from the same `golden_fields.json` — no
  value is hand-duplicated between them.
- `uv run pytest -q` passes at 99+ (95 today, purely additive).
- A real `--cov` run shows non-zero coverage for `streamlit_app/`,
  documented with the real command and real numbers in `tests/TESTING.md`.
- Adding a future combination requires a new, physically-real
  `(truck_photo, trailer_photo, scale_photo)` triple plus their
  `"photos"` ground-truth entries and one new `"rigs"` entry — confirmed
  by the design, not just asserted (both tests' parametrization is what
  makes this true, without touching test code).
- `NEXT_STEPS.md` shows items #6 and #4a as done (terse ✅ lines) and
  item #7's truck/trailer real-photo bullet removed; full narrative
  lives in `ARCHIVE_WEB_STREAMLIT.md`.
- If the real OCR pass turns up a genuine app-level bug, it's fixed,
  not worked around or silently left for later.
- Nothing committed or pushed without a separate, explicit instruction,
  per this project's standing rule.

## Verification

1. `uv run pytest -q tests/test_real_photo_ocr_accuracy.py -v` —
   confirm all parametrized cases pass for real, driving real Tesseract
   against real photos and matching `golden_fields.json`.
2. `uv run pytest -q tests/test_streamlit_app.py -v` — confirm the new
   walkthrough test passes for real (no `unittest.mock` anywhere in its
   own body).
3. `uv run pytest -q` (full suite) — 99+/99+, zero regression.
4. The real coverage command from step 4/5 above — open or inspect the
   report, confirm `streamlit_app/app.py` shows real non-zero coverage,
   not 0% (which would mean the source path was wrong) or a suspicious
   ~100% (which would mean the new test isn't actually the thing
   generating it).
5. Confirm the extensibility claim directly: temporarily duplicate the
   one `"rigs"` entry under a second name (still pointing at the same
   three real photos — no new photo needed just to prove the
   mechanism) and confirm the walkthrough test now runs as two
   parametrized cases with no code change, then remove the throwaway
   duplicate — proves the "no new code" claim isn't aspirational,
   without requiring a second real physical rig's photos just to test
   the test infrastructure itself.
