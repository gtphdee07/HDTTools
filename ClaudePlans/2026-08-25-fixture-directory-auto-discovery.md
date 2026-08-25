# Directory-convention auto-discovery for the pass-pool/fail-pool

## Context

Item #13's remaining open piece is manufacturer/format diversity growth
— today the pass-pool only covers the Ford/Brinkley pairing
(`AddieTag.jpg`/`GooseTag.jpg`, defined in `ExampleDocs/golden_fields.json`)
and the fail-pool only covers one F-150 tag shot 10 ways
(`ExampleDocs/scans/truck/f150/`, also defined in `golden_fields.json`).
Today, adding a new vehicle means hand-editing `golden_fields.json`.

The project owner wants a lower-friction workflow for when new real
photos (other trucks, RVs/trailers) arrive later: drop image files plus
one small file of expected OCR data into a directory tree, and have the
pass-pool/fail-pool tests pick them up on their next run — no
`golden_fields.json` edits, no test-code changes.

**Deliberately scoped to the two pools, not the whole fixture system**:
`golden_fields.json`'s `"photos"` section (used by the exhaustive
per-field `tests/test_real_photo_ocr_accuracy.py`) and `"rigs"` section
(used by `tests/test_streamlit_app.py`'s full walkthrough) both still
reference `AddieTag.jpg`/`GooseTag.jpg`/the `CatScale-*.jpg` pair at
their current top-level `ExampleDocs/` paths. Moving those would touch
three other test files and gain nothing for this request — this plan
leaves them exactly where they are and only builds the new
auto-discovery mechanism for `pass_pool`/`fail_pool`, merging it
alongside the existing JSON-defined entries rather than replacing them.

## Goal

Drop a new vehicle folder under `ExampleDocs/scans/<truck|trailer|scale>/
<vehicle_slug>/` containing image files plus one `vehicle.json`
describing `pool` (`"pass"`/`"fail"`) and either `fields` or
`expected_none_fields` — and have `tests/test_pass_pool_regression.py`/
`tests/test_fail_pool_regression.py` include it automatically on their
next run, with zero other file edits.

## Design

**`vehicle.json` schema** (minimal — `doc_type` is *not* a field, it's
inferred from which bucket directory the vehicle folder sits under,
so there's exactly one source of truth for it, not two that could
drift):

```json
// pass-pool vehicle, e.g. scans/truck/chevy_silverado/vehicle.json
{
  "pool": "pass",
  "fields": {"manufacturer": "CHEVROLET", "gvwr_lb": 10000.0, "front_gawr_lb": 5000.0, "rear_gawr_lb": 6500.0},
  "known_ocr_limitations": {}
}
```
```json
// fail-pool vehicle
{
  "pool": "fail",
  "expected_none_fields": ["manufacturer", "gvwr_lb", "front_gawr_lb", "rear_gawr_lb"]
}
```

Every image file (`.jpg`/`.jpeg`/`.png`, case-insensitive) sitting in
the same folder as a `vehicle.json` is automatically a pool member —
**dropping in an extra photo of the same vehicle needs no file edit at
all**, only a new `vehicle.json` needs writing when it's a genuinely new
vehicle. `truck`/`trailer`/`scale` bucket names map to
`truck_tag`/`trailer_tag`/`scale_ticket` doc_types (a `scale` bucket is
supported by the code but not populated — a scale ticket is a weighing
*event*, not a persistent vehicle, per this project's existing note in
`FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md`).

**New `scripts/vehicle_discovery.py`**: `discover_vehicles(scans_root:
Path | None = None) -> dict` walks `ExampleDocs/scans/*/*/vehicle.json`,
globs sibling images, and returns
`{"pass_pool": {doc_type: [vehicle_dict, ...]}, "fail_pool": {...}}` —
same per-vehicle dict shape (`vehicle`, `images`, plus `fields`/
`expected_none_fields`) the two pools already use, so merging is a
plain list-append. Fails loudly (`ValueError` naming the exact
`vehicle.json` path) on: an unrecognized `pool` value, a pass-pool
entry missing `fields`, a fail-pool entry missing `expected_none_fields`,
or a vehicle folder with a `vehicle.json` but zero image files —
matching this project's fail-loud-not-silent convention rather than
skipping a malformed entry quietly. Accepts an optional root override so
tests can point it at an isolated temp tree.

**`scripts/pass_pool.py` / `scripts/fail_pool.py`**: `_load_golden()`
now also calls `discover_vehicles()` and appends its results onto
`golden["pass_pool"][doc_type]` / `golden["fail_pool"][doc_type]`
respectively (both already lists of vehicle dicts — directory-discovered
ones just add more entries). `resolve_pass_pool_image` gets one small
branch: if the picked vehicle dict has `"fields"` directly (the new,
self-contained shape), use it as-is; otherwise (today's two legacy
`AddieTag.jpg`/`GooseTag.jpg` JSON entries) resolve through
`golden["photos"][filename]` exactly as it does today.
`resolve_fail_pool_image` needs no branch — it was already
self-contained. Each module also gets a small `registered_doc_types()`
helper (backed by the same merged `_load_golden()`) so the two test
files can parametrize from the merged view instead of re-reading raw
JSON directly (their current `_GOLDEN = json.loads(...)` at module
level would otherwise miss a doc_type that exists *only* via directory
discovery).

## Steps (TDD order)

1. **`tests/test_vehicle_discovery.py`** first — build a fake `scans/`
   tree under `tmp_path`, assert: a pass-pool vehicle with `fields` is
   discovered correctly; a fail-pool vehicle with `expected_none_fields`
   is discovered correctly; a stray non-image file (mirrors the real
   `F-150Spec.txt` case) is ignored; an unrecognized bucket directory
   name is ignored; missing/invalid `pool`, a pass-pool entry missing
   `fields`, and a zero-image vehicle folder each raise `ValueError`
   naming the file. Watch it fail (`ModuleNotFoundError`), then write
   `scripts/vehicle_discovery.py` to pass it.

2. **Wire the merge into `pass_pool.py`/`fail_pool.py`** (the small
   `_load_golden()` change + `resolve_pass_pool_image`'s new branch +
   `registered_doc_types()` on both) and repoint
   `tests/test_pass_pool_regression.py`/`test_fail_pool_regression.py`'s
   parametrize source at the new `registered_doc_types()` helpers. Run
   both regression tests to confirm they still pass unchanged (today's
   two JSON-defined pools, no directory-discovered ones yet).

3. **Real live migration, proving the fail-pool half end-to-end**: move
   `ExampleDocs/scans/truck/f150/` → `ExampleDocs/scans/truck/
   f150_blue_goose_uncropped/`, add its `vehicle.json`
   (`pool: "fail"`, the same `expected_none_fields` already documented),
   and delete the now-redundant `fail_pool.truck_tag` entry from
   `golden_fields.json` — the 10 F-150 photos become the first real
   directory-discovered vehicle instead of a JSON-defined one. Re-run
   `tests/test_fail_pool_regression.py` for real to confirm it still
   passes, now sourced entirely from the directory.

4. **Real integration proof for the pass-pool half**, since there's no
   spare unentangled real photo to migrate the same way (`AddieTag.jpg`/
   `GooseTag.jpg` both have other consumers — `"photos"`, `"rigs"` — and
   moving them is explicitly out of scope): a `tmp_path`-based test in
   `tests/test_pass_pool_regression.py` that copies `AddieTag.jpg`'s
   real bytes into an isolated fake `scans/truck/<slug>/` folder next to
   a real `vehicle.json`, points `discover_vehicles()` at that temp root
   directly, and asserts `resolve_pass_pool_image` can pick it and that
   running the real Tesseract pipeline against the copied file still
   extracts the documented fields — proving the whole self-contained
   path works with a real image and real OCR, without adding a
   duplicate fixture to the permanent `ExampleDocs/` tree.

5. **Document the new workflow**: a short new paragraph in
   `golden_fields.json`'s own `"pass_pool"`/`"fail_pool"` `_readme`
   strings pointing at the directory convention as the preferred way to
   add a new vehicle going forward (JSON-defined entries are legacy, not
   removed). Update `NEXT_STEPS.md` item #13 and
   `FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md` to mark the
   auto-discovery mechanism done, leaving "actually add new
   manufacturer photos" and the Android decision as the only remaining
   open items.

## Definition of Done

- `scripts/vehicle_discovery.py` exists, TDD'd, all edge cases
  (malformed sidecar, zero images, stray non-image file, unknown
  bucket) verified with real assertions, not assumed.
- The fail-pool's F-150 vehicle is a real, live directory-discovered
  entry (no JSON entry left for it) and its regression test still
  passes for real.
- A real (non-mocked) integration test proves the pass-pool half of the
  mechanism end-to-end via a temp directory + real image bytes + real
  Tesseract.
- Full suite (`uv run pytest -q`) passes, no regressions.
- The new workflow is written down somewhere a future session (or the
  project owner, months later) can find without re-deriving it.

## Verification

1. `uv run pytest -q tests/test_vehicle_discovery.py -v` — confirm every
   discovery edge case is real, not assumed.
2. `uv run pytest -q tests/test_pass_pool_regression.py tests/test_fail_pool_regression.py -v` —
   several times, confirm both the legacy JSON path and the new
   directory-discovered path (F-150) still resolve and pass for real.
3. `uv run pytest -q` — full suite, confirm no regressions.
4. Manually create one throwaway test folder
   (`ExampleDocs/scans/truck/_manual_check/` + a copied real image +
   `vehicle.json`), run the pass-pool test, confirm it gets picked up,
   then delete it — a real end-to-end sanity check of the exact
   workflow being designed for, beyond the automated tests above.
