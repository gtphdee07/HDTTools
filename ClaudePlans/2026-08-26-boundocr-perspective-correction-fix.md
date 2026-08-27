# BoundOCR — perspective-correction + margin-padding fix (contour_quad)

## Context

The Green-stage regression run (`ClaudePlans/2026-08-26-boundocr-greenstage-design.md`,
executed 2026-08-26) found **0/10 real F-150 photos fully correct**, with
two concrete, diagnosed root causes:

1. `pipeline.extract_from_box` does a naive axis-aligned bounding-box crop
   (`image.crop((min(xs), min(ys), max(xs), max(ys)))`) even when the
   located quad is a rotated parallelogram, so a rotated label crops in a
   garbled wedge of background instead of a straightened label —
   `20260824_141530.jpg`'s box `[(3257,689),(3339,1498),(1826,1556),(1847,909)]`
   is visibly rotated, and its OCR output was pure noise as a direct
   result.
2. The quad is cropped tight to its own edges with no margin, clipping
   needed rows out of frame — `20260824_141537.jpg`'s otherwise-legible
   crop was missing the GVWR line from its OCR text entirely.

The user reviewed this real result, agreed there's "not much upside" to
the broader set of options discussed, and chose these two specific,
bounded fixes as the next step — explicitly not the other options raised
(Hough-based deskew angle, `minAreaRect` instead of `approxPolyDP`, OCR
character-confusion regex tolerance).

## Goal

Replace the naive bbox crop with a real perspective-corrected (deskewed)
crop, padded outward by a small margin before warping, then re-run the
real 10-image regression test and report the honest before/after result —
not assumed, not threshold- or `xfail`-massaged to force a particular
outcome.

## Design

New module: `src/experiments/BoundOCR/common/geometry.py`

```python
def order_quad_points(quad: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Returns [top-left, top-right, bottom-right, bottom-left], robust
    to whatever order locate_label's contour points came in - required
    before a perspective transform, or the warp can flip/tear the image."""

def pad_quad(quad: list[tuple[int, int]], margin_fraction: float = 0.05) -> list[tuple[int, int]]:
    """Expands quad outward from its own centroid by margin_fraction of
    each point's distance to the centroid. A centroid-radial expansion,
    not a true per-edge-normal offset - a reasonable approximation for
    this bounded fix, not a fully general solution."""

def warp_to_quad(image: Image.Image, quad: list[tuple[int, int]]) -> Image.Image:
    """order_quad_points -> cv2.getPerspectiveTransform / warpPerspective
    into an upright rectangle sized from the quad's own real side lengths
    (max of the two horizontal edges for output width, max of the two
    vertical edges for output height) - not a fixed/guessed output size."""
```

`pipeline.extract_from_box` changes from a plain `.crop(bbox)` to
`warp_to_quad(image, pad_quad(box))` before `preprocess_image`/`ocr_text`.
This applies uniformly whether `box` came from `locate_label` or (in the
future Phase 2 UI) a user-dragged rectangle — warping an already-upright
rectangle is a geometric no-op, so no special-casing is needed for either
caller of `extract_from_box`.

## Tests (Red first, per `TDD_METHODOLOGY.md`)

`tests/common/test_geometry.py`:
1. `test_order_quad_points_normalizes_arbitrary_input_order` — feed a
   known rectangle's corners in a scrambled order, assert the returned
   order is correctly [TL, TR, BR, BL].
2. `test_pad_quad_expands_outward_from_centroid` — a known square,
   assert the padded corners are the expected `margin_fraction` further
   from the centroid.
3. `test_warp_to_quad_deskews_a_rotated_rectangle_and_preserves_orientation`
   — a synthetic rectangle rotated by a known angle, with an asymmetric
   marker (a small dark square in only one corner) so a flip/mirror bug
   would be caught, not just a size/shape check. Asserts the output is
   upright (approximately axis-aligned dimensions matching the
   rectangle's true un-rotated width/height) and the marker lands in the
   correct corresponding corner.

`tests/pipelines/contour_quad/test_pipeline.py`'s existing shape-only
test is expected to stay green unchanged (real integration, not touched
by this design).

## Definition of done

- `test_geometry.py`'s 3 tests written first, confirmed Red
  (`ModuleNotFoundError`), then made Green with `common/geometry.py`.
- `pipeline.py` updated to use `warp_to_quad(image, pad_quad(box))`.
- `test_pipeline.py` still passes, unmodified.
- `test_evaluate_f150_regression.py` re-run against all 10 real images;
  real per-image before/after result reported honestly — no `xfail`
  added preemptively, no threshold tuned to force a pass.
- `uv run pytest -q` (existing suite) still unaffected.

## Verification

- `uv run pytest src/experiments/BoundOCR/tests/common/test_geometry.py -v`
  individually first, then the whole BoundOCR suite.
- Re-run the 10-image regression test and compare real correct-field
  counts per image, before vs. after this change.
- `uv run pytest -q` to confirm zero regression on the existing suite.

## Actual results (executed 2026-08-26)

All 3 `test_geometry.py` cases passed on the first real run; `pipeline.py`
was wired to `warp_to_quad(image, pad_quad(box))`;
`test_pipeline.py` and the existing `uv run pytest -q` suite (554 passed /
3 xfailed) stayed green, unaffected.

Real before/after on the 10-image regression (correct fields per image):

| Image | Before this fix | After this fix |
|---|---|---|
| `20260824_141527.jpg` | none | none |
| `20260824_141530.jpg` | **none** | **`front_gawr_lb`, `rear_gawr_lb`** ✅ |
| `20260824_141533.jpg` | none | none |
| `20260824_141537.jpg` | `front_gawr_lb` | `front_gawr_lb` (unchanged) |
| `20260824_141545.jpg` | no box found | no box found (unchanged) |
| `20260824_141557.jpg` | none scored, but vin/vehicle_type read | **empty OCR text** ❌ regressed |
| `20260824_141600.jpg` | none | none |
| `20260824_141606.jpg` | none | none |
| `20260824_141608.jpg` | none | none |
| `20260824_141611.jpg` | none | none |

**Still 0/10 fully correct** (all 4 fields on any single image). The fix
delivered one real, confirmed win (`141530.jpg`, exactly the rotated-quad
case it targeted) but also surfaced a new, real bug: `141557.jpg`'s
located quad `[(3703,329),(1686,371),(1453,1669),(1423,591)]` is not a
well-behaved rotated rectangle, and `order_quad_points`'s corner-sum
heuristic degenerates on it — it assigned the **same point to both
top-right and bottom-right**
(`[(1391,584),(3785,308),(3785,308),(1422,1715)]`), making the
perspective transform singular and producing an unusable, blank-OCR crop.
No net change on the other 7 images.

**Decision (2026-08-26): stop here.** One real fix, one real new edge
case, net still 0/10 — the user's original "not much upside" read is
confirmed by this bounded experiment, not just a hunch. Not pursuing the
degenerate-quad fix or any further contour/quad refinement under this
`contour_quad` pipeline for now. Next step is deciding a different
approach entirely (see the session's live discussion / a follow-up
`ClaudePlans` entry for whatever's decided next) rather than continuing
to patch this one.
