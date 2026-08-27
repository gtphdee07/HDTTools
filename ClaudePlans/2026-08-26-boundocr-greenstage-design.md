# BoundOCR — Green-stage design (make the 5 Red tests pass)

## Context

The Red stage is done and confirmed: `src/experiments/BoundOCR/tests/` has
5 real test files, each failing with a clean `ModuleNotFoundError` for the
specific module it needs (`common.ground_truth`, `common.confidence`,
`common.evaluation`, `pipelines.contour_quad.contour_locate`,
`pipelines.contour_quad.pipeline`). Existing suite unaffected (554 passed
/ 3 xfailed). This plan designs the minimum real implementation to turn
each Red test Green, in the same dependency order the tests were written.

## Goal

Concrete algorithms for the 5 missing modules — precise enough to
implement directly — that make every existing Red test pass, reusing
`hdttools.ocr_common`/`hdttools.truck_tag_ocr` per the established reuse
map, with no changes to existing files.

## Designs

### `common/ground_truth.py`

```python
from pathlib import Path
from hdttools.ocr_common import find_num, find_str

def parse_spec_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return {
        "manufacturer": find_str(r"MFD\.?\s*BY\s+(.+)", text),
        "gvwr_lb": find_num(r"GVWR:?\s*([\d,]+)\s*LB", text),
        "front_gawr_lb": find_num(r"GAWR:?\s*([\d,]+)\s*LB", text),
        "rear_gawr_lb": find_num(r"REAR\s*GAWR:?\s*([\d,]+)", text),
    }
```
Reuses `find_str`/`find_num` exactly as `truck_tag_ocr._parse_fields`
does. `re.search` (used inside both helpers) returns the leftmost match,
so the plain `GAWR:?...LB` pattern naturally matches line 3
("GAWR: 3525 LB") before it would ever reach line 4 ("REAR GAWR: 3800",
which has no "LB" and so can't match this pattern anyway) — no lookbehind
needed. Verified by hand against the real file's 4 lines.

### `common/confidence.py`

```python
import pytesseract
from pytesseract import Output

DEFAULT_CONFIDENCE_THRESHOLD = 50.0

def word_confidences(image) -> list[float]:
    data = pytesseract.image_to_data(image, output_type=Output.DICT)
    return [float(c) for c in data["conf"] if float(c) >= 0]  # -1 = Tesseract's "no detection"

FIELD_VALIDATORS = {
    "gvwr_lb": lambda v: isinstance(v, (int, float)) and 0 < v < 50000,
    "gvwr_kg": lambda v: isinstance(v, (int, float)) and 0 < v < 50000,
    "front_gawr_lb": lambda v: isinstance(v, (int, float)) and 0 < v < 50000,
    "front_gawr_kg": lambda v: isinstance(v, (int, float)) and 0 < v < 50000,
    "rear_gawr_lb": lambda v: isinstance(v, (int, float)) and 0 < v < 50000,
    "rear_gawr_kg": lambda v: isinstance(v, (int, float)) and 0 < v < 50000,
    "manufacturer": lambda v: isinstance(v, str) and v.strip() != "" and not any(c.isdigit() for c in v),
}

def gate_fields(fields: dict, overall_confidence: float,
                threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> dict:
    if overall_confidence < threshold:
        return {key: None for key in fields}
    gated = {}
    for key, value in fields.items():
        validator = FIELD_VALIDATORS.get(key)
        gated[key] = value if (value is None or validator is None or validator(value)) else None
    return gated
```
Fields with no validator (vin, date, vehicle_type, tire specs) pass
through ungated when confidence is above threshold — only the weight
fields and manufacturer have a real format check today, matching what
the Phase-1 plan scoped.

### `common/evaluation.py`

Only `score_image` this increment — `evaluate_directory` stays out until
the CLI work actually needs it and gets its own test (nothing in the 5
Red tests calls it; writing it now would be untested code).

```python
import re

def _normalize(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())

def score_image(extracted: dict, expected: dict) -> dict:
    scores = {}
    for field, expected_value in expected.items():
        actual_value = extracted.get(field)
        if isinstance(expected_value, str):
            correct = isinstance(actual_value, str) and _normalize(actual_value) == _normalize(expected_value)
        else:
            correct = actual_value == expected_value
        scores[field] = {"expected": expected_value, "actual": actual_value, "correct": correct}
    return scores
```

### `pipelines/contour_quad/contour_locate.py`

```python
import cv2
import numpy as np

_MIN_AREA_FRACTION = 0.02

def locate_label(image) -> list[tuple[int, int]] | None:
    arr = np.array(image.convert("RGB"))
    frame_area = arr.shape[0] * arr.shape[1]
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < _MIN_AREA_FRACTION * frame_area:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        candidates.append((len(approx), area, approx))
    if not candidates:
        return None

    candidates.sort(key=lambda item: (0 if item[0] == 4 else 1, item[0], -item[1]))
    corners, _, best = candidates[0]
    if corners == 4:
        return [(int(p[0][0]), int(p[0][1])) for p in best]
    x, y, w, h = cv2.boundingRect(best)
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
```
Sort key: exact-4-corner candidates always rank before any other corner
count (area is not allowed to override this — this is the specific rule
the `20260824_141530.jpg` spike showed is necessary, where a 7-corner
contour had *more* area than the real 4-corner label match). Ties within
the same corner-count bucket go to larger area.

**Note honestly:** the `corners != 4` fallback branch (bounding-rect of
the best non-quad candidate) has no dedicated Red test yet — none of the
3 written cases exercise "best candidate exists but isn't a clean quad."
It's included because it's explicitly documented in the approved Red-stage
plan's docstring and is a small, low-risk extension of logic already
needed for the sort, but flagging this now rather than silently claiming
full test coverage. A dedicated test for this branch is a reasonable
follow-up.

### `pipelines/contour_quad/pipeline.py`

```python
from experiments.BoundOCR.common.confidence import gate_fields, word_confidences
from experiments.BoundOCR.pipelines.contour_quad.contour_locate import locate_label
from hdttools.ocr_common import ocr_text, preprocess_image
from hdttools.truck_tag_ocr import _parse_fields

def extract_from_box(image, box) -> dict:
    xs = [p[0] for p in box]; ys = [p[1] for p in box]
    crop = image.crop((min(xs), min(ys), max(xs), max(ys)))
    preprocessed = preprocess_image(crop)
    confidences = word_confidences(preprocessed)
    overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    fields = _parse_fields(ocr_text(preprocessed))
    gated = gate_fields(fields, overall_confidence)
    return {**gated, "label_found": True, "overall_confidence": overall_confidence, "box": box}

def detect_and_extract(image) -> dict:
    box = locate_label(image)
    if box is None:
        return {"manufacturer": None, "gvwr_lb": None, "front_gawr_lb": None,
                "rear_gawr_lb": None, "label_found": False,
                "overall_confidence": 0.0, "box": None}
    return extract_from_box(image, box)
```
Reuses `preprocess_image`/`ocr_text`/`_parse_fields` from `hdttools`
exactly per the reuse map — no field-regex logic duplicated.

## Expected real outcome (stated honestly, not assumed)

- Tests 1–4 (`ground_truth`, `confidence`, `contour_locate`,
  `pipeline`-shape) are designed to pass outright.
- Test 5 (`test_evaluate_f150_regression`, parametrized over all 10 real
  photos) is **expected to show real failures** on first run — the spike
  already found contour detection doesn't cleanly find the label on every
  photo (e.g. `20260824_141600.jpg`), and even a good crop isn't
  guaranteed perfect Tesseract accuracy on every field. Per the approved
  plan, real per-image failures get inspected and only then annotated
  with `pytest.mark.xfail(strict=True, reason="<specific, observed
  reason>")` — not guessed in advance, not threshold-adjusted to force
  a pass.

## Deferred items (explicit, so nothing gets silently forgotten)

| Item | Why deferred | Reconsider when |
|---|---|---|
| `common/evaluation.py::evaluate_directory` | No Red test calls it yet — the 5 approved tests only need `score_image`. Writing it now would be untested code. | When `cli/evaluate_f150.py` is actually built (Phase 1's later CLI step) — write its own failing test first, per TDD, at that point. |
| Dedicated test for `contour_locate.py`'s non-4-corner fallback branch (bounding-rect of the best non-quad candidate) | None of the 3 written `test_contour_locate.py` cases exercise "a plausible candidate exists but isn't a clean quad" — the branch is implemented (per the approved Red-stage docstring) but not test-driven. | Before/alongside running the full 10-image regression test if a real image is observed hitting this exact branch — or opportunistically, the next time `contour_locate.py` is touched for any other reason. |
| Per-field confidence (aligning a specific extracted token back to its own Tesseract word-level score, rather than one overall-crop confidence gating every field together) | Flagged as a real, meaningfully bigger piece of logic in the original Red-stage plan (`_parse_fields` works on flattened text with no position tracking) — not needed to pass any of the 5 approved tests. | If the overall-crop confidence gate proves too coarse in practice — e.g. the regression test shows a crop with one genuinely bad field and three genuinely good ones, where today's design would blank all four together. Worth revisiting with real evidence from that test, not preemptively. |

## Definition of done

- The 5 modules above exist with exactly this logic (or a corrected
  version if real test runs reveal a mistake in this design).
- `uv run pytest src/experiments/BoundOCR/tests -v`: tests 1–4 green;
  test 5's real per-image results observed and reported honestly,
  with `xfail` added only for images with a confirmed, specific reason.
- `uv run pytest -q` still 554 passed / 3 xfailed, unaffected.

## Verification

- Run each new module's test individually first, in order, then the
  whole BoundOCR suite, per `TDD_METHODOLOGY.md`'s Green-stage loop.
- Report the real regression-test results (pass/fail per image, and why)
  back before adding any `xfail` markers, so that's a visible decision
  point rather than a silent implementation detail.
