# BoundOCR (experimental)

Not part of the production `hdttools` app. This is a research/prototype
area for pre-processing truck-doorjamb data-plate photos (crop/localize
the label) before handing them to Tesseract, since the real pipeline runs
on raw uncropped phone photos today and fails on the small/skewed/glare
kind (see `ExampleDocs/scans/truck/f150_blue_goose_uncropped/vehicle.json`
— those 10 photos are the existing suite's registered fail-pool).

Code here imports from `hdttools` (e.g. `ocr_common.ensure_tesseract_configured`,
`preprocess_image`, `truck_tag_ocr._parse_fields`) but nothing under
`src/hdttools/` or the top-level `tests/` imports back from here, and
nothing here is wired into the real app. Requires no `ANTHROPIC_API_KEY` —
Tesseract + classical/local CV only.

## Layout

- `common/` — shared, pipeline-agnostic pieces: ground-truth parsing,
  confidence gating, scoring.
- `pipelines/<name>/` — one self-contained localization strategy per
  directory, each independently runnable/testable. `contour_quad/` is the
  first: Canny + contour + `approxPolyDP` quadrilateral detection,
  unanchored (no barcode seed — `pyzbar` was tried and found unable to
  decode any of the 10 real target photos; see
  `ClaudePlans/2026-08-26-boundocr-redstage-test-plan.md` for the spike
  that established this). Future parallel strategies (brightness/blob,
  a barcode-anchored variant for other vehicles, a text-detector model)
  each get their own sibling directory here, same shape.

## Running the tests

```bash
uv run pytest src/experiments/BoundOCR/tests -v
```

This is intentionally outside the top-level `tests/` `testpaths` — a bare
`uv run pytest -q` (the existing full-suite command) does not run these,
and running these does not affect that suite.
