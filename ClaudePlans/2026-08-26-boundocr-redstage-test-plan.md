# BoundOCR — TDD Red-stage plan, revised (contour/quad only, no barcode anchor)

## Context

The Phase 1 high-level plan (`ClaudePlans/2026-08-26-boundocr-phase1-high-level-plan.md`)
and an initial Red-stage plan for a **C → B** (barcode-anchor → contour-
refine) pipeline were both approved, and `pyzbar`/`opencv-python-headless`
were installed. Before writing any test files, an empirical spike (run
directly against the real fixture images, not assumed) found:

- **`pyzbar` cannot decode the barcode on any of the 10 real F-150
  photos** — 0/10, even after tight cropping to just the barcode band,
  grayscale/autocontrast, 2x upscaling, and restricting to Code128/Code39.
  Confirmed this isn't an environment/library bug: `pyzbar` correctly
  decodes its own bundled test fixtures (`code128.png`, and even a
  *rotated* `qrcode_rotated.png`) on this machine. The real photos' bars
  are usable-looking to the eye but apparently not clean enough
  (compression, slight blur, the label's diagonal security-pattern
  background) for zbar's decoder specifically.
- A quick unanchored Canny + contour + `approxPolyDP` spike (Option B
  alone, no barcode seed) gave a **mixed but non-trivial signal**: on
  `20260824_141530.jpg` the 2nd-largest contour is a clean 4-corner
  polygon at ~15% of frame area that plausibly matches the real label's
  position; on `20260824_141600.jpg` the top candidate is a false
  positive (a top-left frame artifact, not the label). Not a dead end
  like barcode locate, but not reliable either — exactly the kind of
  partial result the plan's `xfail(strict=True)`-per-image approach (see
  below) already exists to handle honestly.

Given the barcode finding, the user decided (2026-08-26): **drop
barcode-anchoring from this experiment entirely.** This iteration builds
contour/quad detection (Option B) standalone, unanchored, directly
against the full frame. `pyzbar` stays installed (not removed) as a
parked, possibly-useful dependency for a genuinely separate future
pipeline option if a different vehicle's photos turn out more
barcode-friendly — it just isn't part of this pipeline.

## Goal

Same as before, minus barcode: a concrete, reviewable test plan for
`src/experiments/BoundOCR/` — exact new files, exact function signatures
under test (not implementations), fixture strategy, and the first
specific failing tests to write — for a pipeline that locates the label
via contour/quad detection alone, crops, runs Tesseract (reusing existing
`hdttools` helpers), extracts fields, gates them on confidence, and scores
against `F-150Spec.txt` across the 10 real images.

## Reuse map (unchanged from the original Red-stage plan)

| BoundOCR needs | Reuse from `hdttools` | Precedent |
|---|---|---|
| Tesseract path setup | `ocr_common.ensure_tesseract_configured` | every `*_ocr.py` |
| Grayscale/contrast/upscale | `ocr_common.preprocess_image` | same |
| Raw OCR text | `ocr_common.ocr_text` (`image_to_string`, `--psm 6`) | same |
| Field extraction from text | `truck_tag_ocr._parse_fields` | `test_fail_pool_regression.py:34` imports this directly already |
| Word-level confidence | **new** — nothing in the repo calls `image_to_data` today | n/a |
| Label localization | **new** (contour/quad only, this iteration) | n/a |

## Directory structure (renamed: this is Option B standalone, not a barcode+contour hybrid)

```
src/experiments/BoundOCR/
  README.md
  common/
    __init__.py
    image_io.py           # reuse-wrapper: ensure_tesseract_configured, preprocess_image
    confidence.py           # image_to_data confidence + per-field format gate
    ground_truth.py         # parses F-150Spec.txt
    evaluation.py            # scores a pipeline run against ground truth
  pipelines/
    __init__.py
    contour_quad/           # renamed from barcode_contour/ - this is Option B alone
      __init__.py
      contour_locate.py      # Option B: Canny -> contours -> approxPolyDP, unanchored
      pipeline.py              # locate -> crop -> preprocess -> ocr -> parse -> gate
    # pyzbar-based barcode locate is NOT built this iteration; if revisited
    # later for a different vehicle, it becomes its own sibling dir here
    # (e.g. pipelines/barcode_contour/), same shape, still parallel-safe
  cli/
    __init__.py
    evaluate_f150.py
  tests/
    __init__.py
    common/
      test_ground_truth.py
      test_confidence.py
      test_evaluation.py
    pipelines/
      contour_quad/
        test_contour_locate.py
        test_pipeline.py
    fixtures/
      # synthetic PIL-drawn images only this iteration (see below) -
      # no barcode fixtures needed since barcode locate isn't built
    test_evaluate_f150_regression.py
```

## Test architecture (unchanged in spirit)

All new tests live under `src/experiments/BoundOCR/tests/`, run via
`uv run pytest src/experiments/BoundOCR/tests -v`. Per `TESTING.md`: each
function starts as a **Function** test (collaborators faked); a file's
whole public surface gets a **Module** test; `pipeline.py`'s orchestration
gets an **Interaction**-style test once real wiring is involved. Per
`TDD_METHODOLOGY.md`'s real-vs-mocked rule, the evaluation/regression test
runs real Tesseract against the real 10 F-150 photos — never mocked.

### Fixture strategy (simplified — no barcode fixtures needed)

- **`contour_locate`'s tests use synthetic PIL-drawn images** (a plain
  rectangle on a contrasting background, drawn directly with
  `PIL.ImageDraw` — no new dependency): one clean case (finds the exact
  drawn rectangle), one cluttered case (extra shapes/lines added so the
  target rectangle is not simply "the only shape in frame" — closer to
  the real dark-trim-clutter problem than a bare rectangle would be), and
  one no-clean-quad case (only noise, exercises the fallback path).
- **The real 10 images + `F-150Spec.txt`** remain the fixture set for
  `pipeline.py`'s Module test and the regression test — never mocked.

### Confidence-gate design (v1) — unchanged from the original plan

`common/confidence.py` computes one overall confidence score per crop from
`pytesseract.image_to_data`'s per-word `conf` values (mean of words with
`conf >= 0`; Tesseract's `-1` sentinel excluded). A field is blanked
(`None`) if the crop's overall confidence is below a threshold **or** the
field's own value fails a per-field format check. Per-field
token-to-word-alignment confidence stays a flagged, deferred refinement,
not built now.

### Pass/fail bar for the regression test — unchanged, and now expected to matter more

Per `TESTING.md`/`TDD_METHODOLOGY.md`'s established idiom
(`pytest.mark.xfail(strict=True, reason=...)`, never a silent skip or an
invented threshold), the regression test parametrizes over the 10 real
images and asserts all 4 fields match `F-150Spec.txt` for each; any image
that's a genuine, understood limitation (e.g. "no clean quadrilateral
found — contour detection returned a false-positive frame artifact
instead of the label, see the `20260824_141600.jpg` spike finding above")
gets `xfail(strict=True, reason=...)` individually. Given the spike
already showed at least one false-positive case, this test is expected to
need real `xfail`s from the start, not as an afterthought.

## Concrete files and signatures (test targets, not implementations)

```python
# common/ground_truth.py
def parse_spec_file(path: Path) -> dict:
    """Parses F-150Spec.txt-style text into {"manufacturer": str,
    "gvwr_lb": float, "front_gawr_lb": float, "rear_gawr_lb": float} —
    same key names hdttools.truck_tag_ocr._parse_fields already returns."""

# common/confidence.py
def word_confidences(image: Image.Image) -> list[float]:
    """pytesseract.image_to_data(..., output_type=Output.DICT), returns
    conf values with the -1 'no detection' sentinel excluded."""

def gate_fields(fields: dict, overall_confidence: float,
                threshold: float = <TBD, see first tests>) -> dict:
    """Returns a copy of `fields` with any value replaced by None where
    overall_confidence < threshold OR the field fails its own format
    check (see FIELD_VALIDATORS below)."""

FIELD_VALIDATORS: dict[str, Callable[[object], bool]]
    # weight fields: lambda v: isinstance(v, (int, float)) and 0 < v < 50000
    # manufacturer: non-empty string, no digits (exact predicate decided when writing the test)

# common/evaluation.py
def score_image(extracted: dict, expected: dict) -> dict:
    """Per-field {"correct": bool}: numeric fields as exact float
    comparison; manufacturer case-insensitive, punctuation-stripped."""

def evaluate_directory(pipeline_fn, images_dir: Path, spec_path: Path) -> list[dict]:
    """Runs pipeline_fn over every real image in images_dir, scores each
    against parse_spec_file(spec_path), returns one report row per image."""

# pipelines/contour_quad/contour_locate.py
def locate_label(image: Image.Image) -> list[tuple[int, int]] | None:
    """Canny -> cv2.findContours -> approxPolyDP over the FULL frame
    (unanchored - no barcode seed this iteration). Filters candidates by
    area (must be a meaningful fraction of the frame, not a tiny fragment)
    and corner count (==4 preferred; falls back to the bounding rect of
    the best-scoring larger-corner-count contour if no clean quad exists -
    the 20260824_141530.jpg spike's 7-corner largest-area contour vs. its
    own 4-corner 2nd-largest is the concrete real case this fallback logic
    has to choose correctly between). Returns None if nothing plausible
    is found at all - an interface-contract case, not an exception path.

# pipelines/contour_quad/pipeline.py
def detect_and_extract(image: Image.Image) -> dict:
    """locate_label -> crop -> preprocess_image -> ocr_text -> _parse_fields
    -> gate_fields. Returns the gated fields dict plus metadata (box used,
    overall_confidence, label_found: bool) for scoring and for the
    eventual review UI."""

def extract_from_box(image: Image.Image, box: list[tuple[int, int]]) -> dict:
    """Same crop -> preprocess -> ocr -> parse -> gate tail, given an
    already-known box - the seam Phase 2's manual-adjustment UI calls
    directly, skipping locate entirely."""
```

## First failing tests to write, in order

1. **`tests/common/test_ground_truth.py::test_parse_spec_file_reads_the_real_f150_spec`**
   — real file. (Function.)
2. **`tests/common/test_confidence.py::test_gate_fields_blanks_a_field_that_fails_its_format_check`**
   and **`test_gate_fields_blanks_everything_below_the_confidence_threshold`**
   — faked inputs, pure logic isolation. (Function.)
3. **`tests/pipelines/contour_quad/test_contour_locate.py::test_locate_label_finds_a_clean_synthetic_rectangle`**,
   **`test_locate_label_picks_the_real_label_quad_over_a_cluttered_larger_contour`**
   (mirrors the real `20260824_141530.jpg` 7-corner-vs-4-corner case,
   synthetically constructed so it's deterministic), and
   **`test_locate_label_returns_none_when_nothing_plausible_is_found`**.
   (Function, synthetic fixtures.)
4. **`tests/pipelines/contour_quad/test_pipeline.py::test_detect_and_extract_wires_the_real_stages_together`**
   — one real F-150 image, asserts return shape, not accuracy yet.
   (Interaction/Module.)
5. **`tests/test_evaluate_f150_regression.py::test_pipeline_against_all_ten_real_f150_photos`**
   — real, parametrized, `xfail`-capable regression test. Written last.

## Definition of done (this Red stage)

- All 5 test files above exist with real, runnable (currently Red) test
  functions — no stubs/placeholders/`assert True`.
- `uv run pytest src/experiments/BoundOCR/tests -v` shows every new test
  failing with `ModuleNotFoundError`/`AttributeError` (expected Red — no
  implementation exists yet), not an unrelated error.
- Nothing under `src/hdttools/`, `tests/`, or any other existing path is
  touched. `pyzbar` remains installed (parked, unused this iteration) —
  not uninstalled, since it may serve a future separate pipeline option.

## Verification

- `uv run pytest src/experiments/BoundOCR/tests -v` — confirm real,
  specific Red failures (read the actual output, per `TDD_METHODOLOGY.md`'s
  "watch it fail for real" rule).
- `uv run pytest -q` — existing suite still 554 passed / 3 xfailed,
  completely unaffected.

## Next step (after this Red stage is written)

Run the new tests, confirm real Red failures, then **stop and discuss the
actual Red output with the user before writing any Green-stage
implementation code** (standing instruction from the user, unchanged).
Only after that discussion does Green-stage implementation begin, in the
order listed above.
