# Python backend/OCR/Streamlit testing

Classifies this repo's Python test suite (`tests/`, covering
`src/hdttools/`, `src/hdttools/api/`, and `streamlit_app/`) against the
categories defined in the root `TESTING.md`. Written 2026-08-21,
retrofitted onto tests written before that framework existed — most of
this suite predates the categories below; this is the first pass at
labeling it, not a rewrite. See this repo's `ARCHIVE_*.md` files (repo
root — `ARCHIVE_WEB_STREAMLIT.md`, `ARCHIVE_TESTING.md`,
`ARCHIVE_EARLY_HISTORY.md`) for the narrative history of individual
features/bugs each test file guards against.

`uv run pytest -q` — currently 156 tests (153 passing, 3 deliberate
`xfail`s — see `test_real_photo_ocr_accuracy.py` below), no CI; everything
runs manually, matching the root `TESTING.md`'s "session regression"
model rather than a cadence.

## Event-based tiers

Per the root `TESTING.md`'s Minor/Major/External model (retired
2026-08-24, roadmap item #9): this suite has never tagged a fast subset,
so today a full `uv run pytest -q` run covers both **Minor** and
**Major** undifferentiated — there's no `[sanity]`-equivalent marker
splitting them yet, documented honestly here rather than inventing a
split that doesn't exist. Scoping which specific test files a given
change actually calls for (Minor vs. Major, per the root file's
regression-scoping rules) is still a per-session judgment call against
the real diff, same as any other platform. **No External suite exists
here today** — nothing in `src/hdttools`/`streamlit_app` calls a real
3rd-party boundary directly (OCR is local Tesseract, not a network
call), so that category is N/A for this platform, not a gap.

## Coverage

`pytest-cov` is a dev dependency; `[tool.coverage.run]`'s `source` in
`pyproject.toml` covers both `src/hdttools` and `streamlit_app` (widened
to include the latter 2026-08-24, roadmap item #6 — previously
`streamlit_app/` had zero coverage measurement at all). Real, repeatable
command:

```bash
uv run pytest --cov --cov-report=term-missing
```

(Bare `--cov` — no `--cov=PATH` needed — because `[tool.coverage.run]`'s
`source` already tells coverage.py what to measure.) Real numbers as of
2026-08-24: 79% total, `streamlit_app/app.py` 80% (223 statements, 44
missed), `streamlit_app/fields.py` 100%, `streamlit_app/recent_rigs.py`
79%. Kept as an explicit, separate command rather than a default
`pytest -q` `addopts` — matching Android's Minor/Major suites, coverage
reporting stays a deliberate, occasional check, not overhead on every
routine run.

**This 79% total is the enforced baseline `scripts/coverage_gate.py`
checks Python against at release time** — see the root `TESTING.md`'s
"Coverage gate" section; the gate fails only on regression below this
real baseline, not an arbitrary target.

**Structured pass-rate reporting for the README dashboard** (roadmap
item #7, new 2026-08-24): `scripts/generate_dashboard.py` runs `uv run
pytest -q --junitxml=junit.xml` (repo root, gitignored) — the same suite
`uv run pytest -q` already runs, with a JUnit XML report added. Python's
Minor and Major dashboard cells show the same number, since (as noted
above) nothing here tags a fast subset yet — see the root `TESTING.md`'s
"Dashboard" section.

## By file

| File | Category | Covers |
|---|---|---|
| `test_breakdown.py` | Module | `compute_breakdown`/`verdict_for`'s full public surface: axle-count/tongue-weight/pin-weight-pct math, the `estimated` flag, all four verdict tones, error-shaped edge cases (clamp-at-zero). |
| `test_breakdown_golden_vectors.py` | **Cross-platform interface** | Runs `compute_breakdown`/`verdict_for` against `test-vectors/breakdown_cases.json`, the same cases the Kotlin port's `BreakdownGoldenVectorTest.kt` checks itself against — see the root `TESTING.md`'s cross-platform section. |
| `test_api.py` | Module + **Interface** | FastAPI routing/schema validation with OCR mocked. The `test_breakdown_endpoint_*` cases exercise the real (unmocked) `main.py` → `breakdown.py` → `schemas.py` chain. `test_breakdown_endpoint_pin_weight_pct_is_a_fraction_not_the_ui_percentage` (2026-08-21) is a **cross-platform interface test**, paired with `web/src/api.test.ts` via `test-vectors/pin_weight_pct_contract.json` — confirms the endpoint's `pin_weight_pct` is a 0.15–0.25 fraction, and that sending the raw 15–25 UI number unconverted produces a visibly wrong (negative) result rather than a quietly-off one. `test_breakdown_response_matches_the_shared_api_contract` (2026-08-21) is a second **cross-platform interface test**, paired with `web/src/apiShape.test.ts` via `test-vectors/breakdown_response_shape_contract.json` — the "ground truth" half proving `BreakdownItemOut`/`VerdictOut`'s real keys still match what `web/`'s hand-written fixtures assume (see that file's "Known gaps" for the `TruckTagOut`/`TrailerTagOut`/`ScaleTicketOut` shapes this doesn't yet cover, and `FUTURE_API_SCHEMA_VALIDATION.md` for the fuller schema-export approach parked for later). |
| `test_scale_ticket_ocr_parsing.py` | Function | `_parse_fields`/`_find_str`/`_find_num` against transcribed OCR text, including a real (garbled) tow-vehicle-only ticket transcription. |
| `test_truck_tag_ocr_parsing.py` | Function | `_parse_fields`/`_kg_lb` against transcribed OCR text, including a real garbled "LB read as 1B" regression case. |
| `test_trailer_tag_ocr_parsing.py` | Function | `_parse_fields` against transcribed OCR text. |
| `test_scale_ticket_real_photo.py` | Function + **Interface** | Real Tesseract against a real `ExampleDocs/` file — the module-level `_parse_fields` case is Function (real input, one function); the `/api/extract/scale-ticket` case is Interface (the real endpoint, no mocks anywhere in the chain). |
| `test_real_photo_ocr_accuracy.py` | Function, real-photo, parametrized | New 2026-08-24 (roadmap item #6, closes item #7's truck/trailer real-photo OCR gap too). Real Tesseract against every real `ExampleDocs/` photo in `ExampleDocs/golden_fields.json`'s `"photos"` — one parametrized case per field, so a future brand/format needs only a new JSON entry, no new test code. Found and fixed two real regex bugs (a stray OCR glyph breaking `truck_tag_ocr._kg_lb`'s label match; a comma `scale_ticket_ocr`'s `location_name` prefix didn't tolerate) — see `ARCHIVE_WEB_STREAMLIT.md`. Two remaining real OCR-accuracy limits (a digit-drop, a two-column layout jumble) are `xfail(strict=True)` with the real reason recorded on `golden_fields.json` — a value real OCR doesn't currently produce is never silently asserted or hidden. |
| `test_readers_integration.py` | Module | Each `read_*_tag`/`read_scale_ticket`'s one public entry point, every I/O boundary (file picker, vision, review form, database) mocked. Explicit sequential composition (each step's output passed to the next as an argument) — no implicit shared state, so this is module-surface testing, not interaction testing, despite the docstring's "orchestration and control flow" framing. |
| `test_streamlit_app.py` | **Interaction**, real-photo | The clearest interaction-test example in this repo. `_render_review` and `_render_standalone_ticket_section`/`_module_step` in `streamlit_app/app.py` share `st.session_state` implicitly, across reruns — these tests drive the real multi-step sequence and assert the net state, which is exactly what caught the real stale-widget-value bug a solitary test of either function could not have seen. `test_full_walkthrough_with_real_photos_reaches_a_real_verdict` (new 2026-08-24, parametrized over `golden_fields.json`'s `"rigs"`) is the first test anywhere in this repo to drive all four real ExampleDocs/ photos of one rig (truck tag, standalone ticket, trailer tag, full-rig scale ticket) through the real app to a real, hand-verified Results verdict — every prior "full walkthrough" (this file and `web/`'s Playwright suite both) only ever exercised the zero-image, skip-everything path. |
| `test_review_form_coerce.py` | Function | `_coerce`'s type conversion + its `ValueError` on invalid input. |
| `test_file_picker.py` | Function | `select_image_file`/`prompt_vehicle_name`'s cancel/blank-input error paths. |
| `test_vision_client.py` | Function | `extract_via_claude`'s happy path and its raise when Claude's response has no matching `tool_use` block. |
| `test_database.py` | Function + Module | `_flatten` (Function); `save_scale_ticket`/`save_truck_tag`/`save_trailer_tag` against a real `tmp_path` SQLite file (Module — the module's three offered operations, including row-id increment behavior). |
| `test_models.py` | Function | Dataclass defaults/structure for `TruckTagData`/`TrailerTagData`/`ScaleTicketData`/`TireSpec`. |
| `test_ocr_output_key_contracts.py` | **Interface** | Two opposite-direction key-set checks per OCR module (2026-08-22): every `_parse_fields()` key must be a declared `schemas.py` field (the FastAPI `response_model`/`extra="ignore"` silent-drop risk), and every `fields.py`/`FIELDS` name must map to a real `_parse_fields()` key (the Streamlit `_extract_fields`'s `keep`-filter silent-drop risk, opposite direction since `FIELDS` deliberately shows only a curated subset of what OCR extracts). Both exclude the same known manual-only fields (`standalone_weight_lb`, `axle_count`). Calls `_parse_fields("")` — the full key set is structurally present regardless of match success, so no synthetic label text is needed, just the shape. |
| `test_coverage_gate.py` | Function | New 2026-08-24 (roadmap item #9). `../scripts/coverage_gate.py`'s `PlatformResult.passed` baseline-floor logic, loaded via `importlib` since the script lives outside the `hdttools` package. The report parsers themselves moved to `coverage_lib.py` 2026-08-24 (item #7) — see `test_coverage_lib.py` below. The `get_*_result` functions that actually shell out to each platform's toolchain (gradlew/pytest/npm) are deliberately not unit-tested here — thin I/O glue, exercised for real by the script's own manual runs (see `ARCHIVE_TESTING.md`). |
| `test_coverage_lib.py` | Function | New 2026-08-24 (roadmap item #7). `../scripts/coverage_lib.py`'s four pure coverage-report parsers (`parse_android_report`/`parse_python_report`/`parse_web_report`/`parse_scan_proxy_output`), shared by `coverage_gate.py` and `generate_dashboard.py` — extracted from `test_coverage_gate.py` when the parsers themselves moved out of that script. |
| `test_dashboard_lib.py` | Function | New 2026-08-24 (roadmap item #7). `../scripts/dashboard_lib.py`'s `color_for_percent` threshold banding, `parse_junit_xml` (real schema differences across pytest/Vitest/Android/Node's JUnit XML output — see that module's own docstring), `format_external_cell`'s never-recorded/single-suite/multi-suite-combining logic, and `render_dashboard_svg` (well-formedness + content checks, not a pixel-level snapshot). |
| `test_record_external_result.py` | Function | New 2026-08-24 (roadmap item #7). `../scripts/record_external_result.py`'s `record()` — writes a new entry, maps a nonzero exit code to `passed: false`, preserves other platforms'/suites' existing entries untouched, and overwrites a stale entry for the same platform+suite. Uses `monkeypatch` on the module's `STATUS_FILE` constant rather than touching the real `scripts/dashboard_data/external_status.json`. |

## Known gaps (identified 2026-08-21, not all closed)

- ✅ **Closed**: `estimated` field surviving the real `/api/breakdown`
  JSON response — nothing checked this before
  `test_breakdown_endpoint_response_preserves_the_estimated_field` was
  added; a rename/drop on either side of the `breakdown.py`/`schemas.py`
  boundary would have gone uncaught even with every other breakdown test
  passing.
- ✅ **Closed 2026-08-22**: `truck_tag_ocr._parse_fields`'s and
  `trailer_tag_ocr._parse_fields`'s output keys (and `scale_ticket_ocr`'s,
  for completeness) confirmed to still match what `TruckTagOut`/
  `TrailerTagOut`/`ScaleTicketOut` (schemas.py) declare — see
  `test_ocr_output_key_contracts.py` above. Still genuinely open: the
  `TruckTagOut`/`TrailerTagOut`/`ScaleTicketOut`-vs-`web/`'s-hand-written-
  fixtures gap `web/TESTING.md` flags (a different boundary — Python
  internal vs. Python-to-TypeScript) and the fuller schema-export
  approach in `FUTURE_API_SCHEMA_VALIDATION.md` remain their own,
  separate, not-yet-started work.
- ✅ **Closed 2026-08-22**: `scale_ticket_ocr`/`truck_tag_ocr`/
  `trailer_tag_ocr`'s output dict keys confirmed to still match what
  `streamlit_app/app.py`'s `FIELDS` dict (`fields.py`) expects — see
  `test_ocr_output_key_contracts.py` above.
- ✅ **Closed 2026-08-21**: `test_breakdown_golden_vectors.py` (new)
  loads `test-vectors/breakdown_cases.json`, shared with the Kotlin port's
  own `BreakdownGoldenVectorTest.kt` — see the root `TESTING.md`'s
  cross-platform section and `ARCHIVE_TESTING.md` (repo root) for what
  running it against Kotlin found.
- ✅ **Closed 2026-08-24**: truck tag / trailer tag real-photo OCR
  coverage (the scale ticket reader already had this) — see
  `test_real_photo_ocr_accuracy.py` above, driven by the new
  `ExampleDocs/golden_fields.json` (ground truth for every real photo,
  plus valid `(truck, trailer, scale)` "rigs" tuples — a scale ticket's
  weights are only physically meaningful for the exact combination
  actually weighed together, so this isn't a flat interchangeable photo
  pool). Same data also backs `test_streamlit_app.py`'s new full
  walkthrough. Full narrative — two real regex bugs found and fixed,
  two real OCR-accuracy limits found and documented — in
  `ARCHIVE_WEB_STREAMLIT.md`.
