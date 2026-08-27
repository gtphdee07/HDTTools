# BoundOCR experiment — high-level plan (Phase 1: pipeline + evaluation harness)

## Context

Tesseract today runs on raw, uncropped phone photos of truck data plates and
fails badly on small/skewed/glare-heavy shots — the 10 photos in
`ExampleDocs/scans/truck/f150_blue_goose_uncropped/` are literally registered
as the **fail-pool** in the existing suite (`vehicle.json`:
`pool: "fail"`, `expected_none_fields: [manufacturer, gvwr_lb,
front_gawr_lb, rear_gawr_lb]`, exercised by `tests/test_fail_pool_regression.py`).
We're prototyping a crop/localization pre-processing stage to see whether a
barcode-anchored, then contour-refined, bounding box can turn these into
OCR successes — as an isolated experiment that doesn't touch the existing
pipeline, so that regression test keeps measuring exactly what it measures
today regardless of this experiment's outcome.

This is Phase 1 of a two-phase effort (confirmed with the user): build and
measure the core detection→extraction pipeline as fully testable, non-UI
logic first; the interactive Streamlit "drag the box, review the fields"
workflow is an explicit, separate Phase 2 once this pipeline's accuracy is
known. Everything here is new code under `src/experiments/BoundOCR/` —
no existing file is modified, only imported from.

## Goal

A self-contained `src/experiments/BoundOCR/` module implementing a
**C → B pipeline** (barcode-anchored localization, refined by contour/quad
detection) that crops the label, runs Tesseract, extracts the four
F-150Spec fields with a confidence gate (blank instead of guessing on low
confidence), and reports accuracy against `F-150Spec.txt`'s known-correct
values across all 10 fail-pool images — architected so sibling detection
strategies (brightness/blob, text-detector, etc.) can be added later as
parallel peers without restructuring anything already built.

## Directory structure

```
src/experiments/BoundOCR/
  README.md                     # what this is, how it relates to the real
                                 # pipeline, explicitly experimental/non-production
  common/
    __init__.py
    image_io.py                 # imports ensure_tesseract_configured/preprocess_image
                                 # from hdttools.ocr_common (reuse, not copy)
    confidence.py                # image_to_data-based per-word confidence +
                                 # per-field format/regex sanity gate -> blank on low confidence
    ground_truth.py              # parses F-150Spec.txt into a normalized,
                                 # comparable dict (numeric value + unit)
    evaluation.py                 # runs a given pipeline over a fixture dir,
                                 # scores against ground truth, emits a report
  pipelines/
    __init__.py
    barcode_contour/             # this iteration's pipeline: C -> B
      __init__.py
      barcode_locate.py           # Option C: pyzbar -> anchor box + angle
      contour_refine.py           # Option B: edge/contour quad, seeded by the anchor
      pipeline.py                  # locate -> refine -> crop -> OCR -> parse -> gate
                                    # exposes both detect_and_extract(image) AND
                                    # extract_from_box(image, box) so Phase 2's UI
                                    # can re-run extraction from a user-adjusted box
                                    # without duplicating pipeline logic
    # future sibling dirs (not built now) live at this same level, e.g.
    # brightness_blob/, text_detector/ - each self-contained, same shape
  cli/
    __init__.py
    evaluate_f150.py              # `uv run python -m src.experiments.BoundOCR.cli.evaluate_f150`
                                   # human-readable per-image/per-field report
  tests/
    __init__.py
    common/
      test_image_io.py
      test_confidence.py
      test_ground_truth.py
      test_evaluation.py
    pipelines/
      barcode_contour/
        test_barcode_locate.py
        test_contour_refine.py
        test_pipeline.py
    test_evaluate_f150_regression.py   # real Tesseract, real 10 images, real ground truth
```

Run with `uv run pytest src/experiments/BoundOCR/tests -v` — this works
today without touching `pyproject.toml`'s `testpaths`, and a bare
`uv run pytest -q` (the existing full-suite command) will not pick these up
or be affected by them either way.

## New dependencies (confirmed, install now — not deferred)

Installed at the project level via `uv add` as an early setup step of this
plan, so the rest of the project can use them too, not just this
experiment:

- **`pyzbar`** (barcode decoding, Option C) — approved. Small, bundles the
  `zbar` DLL on Windows, no extra system install needed for local dev; the
  `packages.txt`/`libzbar0` step discussed earlier only matters once Phase
  2 is deployed to Streamlit Community Cloud.
- **`opencv-python-headless`** (contour/quad detection, Option B) —
  approved, headless variant chosen over full `opencv-python` (no GUI
  bindings needed in this backend/Streamlit pipeline; smaller, avoids a
  known conflict if both variants are ever installed together).

Both add entries to `pyproject.toml`/`uv.lock` (unavoidable for any `uv
add`) but touch no application or test code. Per the user's confirmed
install policy for this project: **uv's own cache/python/tool directories
stay on their current C: defaults, unchanged** — only new toolchains
default to G:, and both of these land in the project's `.venv` (already at
the repo root on G:) the same way every other project dependency does.
`opencv-python-headless`'s wheel is the one piece that exceeds the
10MB-to-C: confirmation threshold (uv's build cache write, ~30-70MB
compressed, before installing into the G:-drive venv) — already confirmed
with the user above.

## Design points carried in from the pipeline discussion

- **Confidence gate** (`common/confidence.py`): combine Tesseract's own
  per-word confidence (`pytesseract.image_to_data`) with a per-field
  format/pattern sanity check (e.g. GVWR must parse as a number + weight
  unit). A field that fails the gate comes back as `None`/blank rather
  than a guessed value — this is what lets the eventual review UI force
  real user attention instead of a rubber-stamped "OK".
- **Scoring** (`common/ground_truth.py` + `common/evaluation.py`):
  normalized/numeric comparison (parse the number out of both the OCR
  result and `F-150Spec.txt`, compare values) rather than exact string
  match, since the label prints `GVWR: 3221 KG (7100 LB)` while
  `F-150Spec.txt` just says `GVWR: 7100 LB`.
- **Manual-adjustment hook**: `pipeline.py` exposes `extract_from_box()`
  as a first-class entry point (not a private helper) precisely so Phase
  2 can feed it a user-dragged box and get the same crop→OCR→gate
  treatment the automatic path gets — this is the seam Phase 2 will need,
  built now so it isn't retrofitted later.
- **What this plan does NOT decide yet** (left for the detailed TDD
  Red-stage plan, the next approval step): the exact pass/fail bar for
  the 10-image regression test. The user's framing ("see what the OCR
  correctness is") reads as a measurement/reporting harness rather than a
  hard gate — the Red-stage plan will propose the test's actual assertion
  shape (a report-well-formed check vs. a numeric accuracy threshold vs.
  a per-image `xfail`-style known-limitations list matching the existing
  `golden_fields.json` convention) for the user to confirm before writing it.

## Definition of done (Phase 1)

- `src/experiments/BoundOCR/` exists with the structure above; zero edits
  to any existing file (only imports from `hdttools.ocr_common`).
- Barcode-anchored locate (C) + contour-refine (B) + crop + Tesseract
  extract + confidence-gated field parse implemented and covered by tests
  written before their implementations (real TDD Red→Green, per
  `TDD_METHODOLOGY.md`).
- `evaluate_f150.py` CLI and the corresponding regression test run all 10
  real images in `f150_blue_goose_uncropped/` against `F-150Spec.txt` and
  produce a per-image/per-field accuracy report.
- `uv run pytest src/experiments/BoundOCR/tests -v` passes; `uv run pytest -q`
  (existing full suite) is unaffected and still passes exactly as before.

## Verification

- `uv run pytest src/experiments/BoundOCR/tests -v` — new suite green.
- `uv run pytest -q` — confirms zero regression on existing tests.
- `uv run python -m src.experiments.BoundOCR.cli.evaluate_f150` — human
  read of the per-image/per-field report; since this is fundamentally a CV
  problem, also visually spot-check a couple of the intermediate crop
  outputs (saved to a scratch/output location) rather than trusting field
  scores alone.

## Next step (separate approval, not part of this plan)

Once this high-level plan is approved, the next deliverable is a detailed
TDD Red-stage plan: concrete test files, fixture/synthetic-image strategy
for `barcode_locate`/`contour_refine` (real fixture images vs. synthetic
generated ones for deterministic function-level tests), and the specific
first failing tests to write for `common/` before `pipelines/barcode_contour/`.
