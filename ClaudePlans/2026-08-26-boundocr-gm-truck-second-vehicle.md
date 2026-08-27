# BoundOCR — add GM truck label as a 2nd real test vehicle

## Context

`ExampleDocs/scans/truck/gm_truck/` (a `gm` "Trailering Information" label
photo + spec file) was just added. Its ground-truth spec file has already
been corrected (it had a leftover "MFD. BY FORD MOTOR CO" line copy-pasted
from the F-150 fixture). This label is a genuinely different schema from
the Ford tag BoundOCR has been built against so far — no barcode, no
front/rear GAWR split (just one `RGAWR`), and several fields Ford's label
doesn't have at all (`GCWR`, `CURB WEIGHT`, `MAX PAYLOAD`, and an SAE J2807
trailer-rating section with `CONVENTIONAL TWR`/`GOOSENECK TWR`/two
`MAX TONGUE WEIGHT` values). Visually it's also a plain brushed-metal
plate with no diagonal security-pattern background — possibly much
friendlier to OCR than the Ford label, worth finding out for real.

Directory placement needs no change: `ExampleDocs/scans/truck/gm_truck/`
already matches `scripts/vehicle_discovery.py`'s
`<truck|trailer|scale>/<vehicle_slug>/` bucket convention. This plan is
about wiring it into BoundOCR as a second real test vehicle, reusing the
schema-agnostic parts of the existing pipeline (localization, confidence
gating, geometry) and adding only what's genuinely GM-specific (field
parsing, ground truth).

## Goal

Get a real, TDD-built regression test running the `contour_quad` pipeline
against `GMTruck_FB.jpg`, scored against corrected ground truth — without
touching `hdttools` (the existing Ford-specific `_parse_fields` stays
untouched) and without duplicating the localization/geometry/confidence
machinery, which is already schema-agnostic.

## What's reused vs. new

| Piece | Ford (existing) | GM (new) |
|---|---|---|
| Localization (`locate_label`), geometry (`pad_quad`/`warp_to_quad`), confidence scoring mechanism | shared, unchanged | shared, unchanged |
| Field-extraction parser | `hdttools.truck_tag_ocr._parse_fields` (reused) | **new**: `common/gm_truck_fields.py::parse_gm_fields` |
| Ground-truth parsing | `common/ground_truth.py::parse_spec_file` (unchanged) | **new**: `common/ground_truth.py::parse_gm_spec_file` (kept as a separate function, not a forced generalization — the two spec formats aren't similar enough to safely unify without risking the already-passing Ford test) |
| Field validators (confidence gate) | existing `FIELD_VALIDATORS` entries | **add** GM's field names to the same shared dict — no collision risk, keys are already namespaced by field name |
| Pipeline orchestration | `pipeline.detect_and_extract`/`extract_from_box` | **same functions, extended** with an optional `field_parser` param (default = Ford's `_parse_fields`, so existing calls/tests are unaffected) |
| Cross-vehicle evaluation loop | `test_evaluate_f150_regression.py` (hand-rolled loop, unchanged) | **new**: `common/evaluation.py::evaluate_directory` gets actually built now (previously deferred — "when a second real caller needs it," which this is), and the new GM regression test uses it |

## Design

### `common/gm_truck_fields.py` (new)

```python
def parse_gm_fields(text: str) -> dict:
    """Regex-parses a GM Trailering Information label's OCR text.
    Returns vin (str) plus *_lb/*_kg float pairs for: gvwr, gcwr, rgawr,
    curb_weight, max_payload, conventional_twr, gooseneck_twr, and the two
    positionally-distinct 'MAX TONGUE WEIGHT' values (conventional vs.
    gooseneck section) - mirrors how truck_tag_ocr._tire_specs resolves
    front vs. rear tire specs positionally via re.finditer + indexing,
    since 'MAX TONGUE WEIGHT' is a repeated label meaning different things
    by position, not by distinct text."""
```

### `common/ground_truth.py` (extended, not modified in place)

```python
def parse_gm_spec_file(path: Path) -> dict:
    """Parses GMTruck-Spec.txt's plain LABEL: NUMBER KG/UNIT LBS lines
    into the same field-name keys parse_gm_fields uses, plus vin (str)."""
```

### `common/confidence.py`

Add entries to the existing `FIELD_VALIDATORS` dict for every new numeric
GM field (same `0 < v < 50000`-style plausibility check already used for
Ford's weight fields) — no new mechanism, just more entries.

### `pipelines/contour_quad/pipeline.py`

```python
def extract_from_box(image, box, field_parser=_parse_fields) -> dict:
    ...
    fields = field_parser(ocr_text(preprocessed))
    ...

def detect_and_extract(image, field_parser=_parse_fields) -> dict:
    ...
    return extract_from_box(image, box, field_parser=field_parser)
```
Default preserves existing behavior exactly — `test_pipeline.py` (Ford)
needs no changes.

### `common/evaluation.py` (finishing the deferred piece)

```python
def evaluate_directory(pipeline_fn, images_dir: Path, expected: dict) -> list[dict]:
    """Runs pipeline_fn over every real image in images_dir, scores each
    against the already-parsed `expected` dict via score_image, returns
    one report row per image. Takes a parsed dict rather than a spec path
    now, since Ford and GM use different spec-parsing functions - this
    keeps evaluate_directory decoupled from which one was used."""
```

## Tests (Red first)

1. `tests/common/test_gm_truck_fields.py` — `parse_gm_fields` against a
   known clean text sample (Function test, direct text input, no image
   dependency) covering the ordinary fields plus the positional
   conventional-vs-gooseneck tongue-weight case specifically.
2. `tests/common/test_ground_truth.py` — add
   `test_parse_gm_spec_file_reads_the_real_gm_spec` (Function, real file).
3. `tests/common/test_evaluation.py` (new file — `evaluate_directory` has
   never had a dedicated test) — a fake `pipeline_fn` and a small real
   directory (reuse the existing fixture dirs), asserting the report
   shape and that scores match `score_image`'s own output for each image.
4. `tests/test_evaluate_gm_truck_regression.py` — the real regression
   test: real Tesseract, the real `GMTruck_FB.jpg`, `parse_gm_spec_file`
   for ground truth, `evaluate_directory` to run and score it. Only one
   image exists, so this isn't parametrized the way the 10-image Ford
   test is — a single real assertion, `xfail(strict=True, reason=...)`
   added only if a real run shows a genuine, specific limitation (same
   honest-reporting discipline as before, not decided in advance).

`test_pipeline.py` and all previously-passing BoundOCR/existing tests are
expected to stay green unmodified.

## Definition of done

- New files/functions above exist, each with a Red test written first.
- `uv run pytest src/experiments/BoundOCR/tests -v` — all Function/Module
  tests green; the GM regression test's real result reported honestly
  (not assumed) before any `xfail` is added.
- `uv run pytest -q` (existing suite) still unaffected.
- Nothing in `hdttools/` or top-level `tests/` touched.

## Verification

- Run each new test file individually first, then the whole BoundOCR
  suite, per the established TDD loop.
- Report the real GM regression result — including whether the
  no-security-pattern/no-barcode label surface actually OCRs better, as
  suspected but not yet confirmed.
- `uv run pytest -q` to confirm zero regression on the existing suite.

## Actual results (executed 2026-08-26)

All new Function/Module tests passed on the first real run:
`test_gm_truck_fields.py` (2), `test_ground_truth.py`'s new GM case,
`test_evaluation.py` (new file, `evaluate_directory` finally built and
tested), and the existing Ford `test_pipeline.py` stayed green unmodified
(the `field_parser` default-parameter change is fully backward-compatible).

**The real GM regression test failed — 0/10 fields correct** via the
automated pipeline, but the root cause is the opposite of Ford's:

- `locate_label` picked the **wrong region entirely** — it selected the
  trailer-hitch/ball-mount hardware at the top of the frame (box
  `[(0,0),(1206,0),(1206,466),(0,466)]` out of a 1206x1201 image), not
  the actual label lower in the photo. Its overall_confidence (44.6)
  also happened to land just under the 50.0 gate threshold on that wrong
  crop, blanking every field regardless.
- **Hand-cropping the real label region and re-running the exact same
  OCR + `parse_gm_fields` got 8 of 10 scored fields exactly right**:
  VIN, GVWR, GCWR, RGAWR, curb weight (LB), max payload, conventional
  TWR, and its tongue weight all matched ground truth precisely. Only
  the two `gooseneck` TWR fields failed — Tesseract's text for that one
  line came out as "7539 Bete fon Fee" instead of "7539 KG / 16620 LBS",
  likely from a real dirt/rust smudge visible over that part of the
  label in the photo (`curb_weight_kg` also misread 3254->9254, but that
  field isn't in scope for scoring since only `curb_weight_lb` is in
  ground truth).

**This confirms the suspected hypothesis**: this label's plain
brushed-metal surface with no diagonal security-pattern background is
dramatically more OCR-friendly than the Ford label — 8/10 on a correct
crop here vs. 0/10 on Ford's best hand-crop, using the same OCR engine
and no engine change at all. The bottleneck for THIS vehicle is purely
`locate_label`'s region selection, not OCR quality — the reverse of what
limited the Ford case.

No `xfail` added — this is a real, understood, likely-fixable
localization bug (analogous to Ford's `20260824_141600.jpg` false
positive), not an accepted permanent limitation. Left for the next
decision: whether to invest in improving `locate_label`'s region
selection now that there's a second, concrete real failure case to learn
from, or move on.
