# Python backend/OCR/Streamlit testing

Classifies this repo's Python test suite (`tests/`, covering
`src/hdttools/`, `src/hdttools/api/`, and `streamlit_app/`) against the
four categories defined in the root `TESTING.md`. Written 2026-08-21,
retrofitted onto tests written before that framework existed — most of
this suite predates the categories below; this is the first pass at
labeling it, not a rewrite. See `NEXT_STEPS.md` for the narrative history
of individual features/bugs each test file guards against.

`uv run pytest -q` — currently 95 tests, all passing, no markers/tiers
wired up yet (this repo has no CI; everything runs manually, matching the
root `TESTING.md`'s "session regression" model rather than a cadence).

## By file

| File | Category | Covers |
|---|---|---|
| `test_breakdown.py` | Module | `compute_breakdown`/`verdict_for`'s full public surface: axle-count/tongue-weight/pin-weight-pct math, the `estimated` flag, all four verdict tones, error-shaped edge cases (clamp-at-zero). |
| `test_breakdown_golden_vectors.py` | **Cross-platform interface** | Runs `compute_breakdown`/`verdict_for` against `test-vectors/breakdown_cases.json`, the same cases the Kotlin port's `BreakdownGoldenVectorTest.kt` checks itself against — see the root `TESTING.md`'s cross-platform section. |
| `test_api.py` | Module + **Interface** | FastAPI routing/schema validation with OCR mocked. The `test_breakdown_endpoint_*` cases exercise the real (unmocked) `main.py` → `breakdown.py` → `schemas.py` chain. `test_breakdown_endpoint_pin_weight_pct_is_a_fraction_not_the_ui_percentage` (2026-08-21) is a **cross-platform interface test**, paired with `web/src/api.test.ts` via `test-vectors/pin_weight_pct_contract.json` — confirms the endpoint's `pin_weight_pct` is a 0.15–0.25 fraction, and that sending the raw 15–25 UI number unconverted produces a visibly wrong (negative) result rather than a quietly-off one. `test_breakdown_response_matches_the_shared_api_contract` (2026-08-21) is a second **cross-platform interface test**, paired with `web/src/apiShape.test.ts` via `test-vectors/breakdown_response_shape_contract.json` — the "ground truth" half proving `BreakdownItemOut`/`VerdictOut`'s real keys still match what `web/`'s hand-written fixtures assume (see that file's "Known gaps" for the `TruckTagOut`/`TrailerTagOut`/`ScaleTicketOut` shapes this doesn't yet cover, and `FUTURE_API_SCHEMA_VALIDATION.md` for the fuller schema-export approach parked for later). |
| `test_scale_ticket_ocr_parsing.py` | Function | `_parse_fields`/`_find_str`/`_find_num` against transcribed OCR text, including a real (garbled) tow-vehicle-only ticket transcription. |
| `test_truck_tag_ocr_parsing.py` | Function | `_parse_fields`/`_kg_lb` against transcribed OCR text, including a real garbled "LB read as 1B" regression case. |
| `test_trailer_tag_ocr_parsing.py` | Function | `_parse_fields` against transcribed OCR text. |
| `test_scale_ticket_real_photo.py` | Function + **Interface** | Real Tesseract against a real `ExampleDocs/` file — the module-level `_parse_fields` case is Function (real input, one function); the `/api/extract/scale-ticket` case is Interface (the real endpoint, no mocks anywhere in the chain). The only file in this suite that never mocks Tesseract itself. |
| `test_readers_integration.py` | Module | Each `read_*_tag`/`read_scale_ticket`'s one public entry point, every I/O boundary (file picker, vision, review form, database) mocked. Explicit sequential composition (each step's output passed to the next as an argument) — no implicit shared state, so this is module-surface testing, not interaction testing, despite the docstring's "orchestration and control flow" framing. |
| `test_streamlit_app.py` | **Interaction** | The clearest interaction-test example in this repo. `_render_review` and `_render_standalone_ticket_section`/`_module_step` in `streamlit_app/app.py` share `st.session_state` implicitly, across reruns — these tests drive the real multi-step sequence (skip → rerun → review → scan → rerun → review again) and assert the net state, which is exactly what caught the real stale-widget-value bug a solitary test of either function could not have seen. |
| `test_review_form_coerce.py` | Function | `_coerce`'s type conversion + its `ValueError` on invalid input. |
| `test_file_picker.py` | Function | `select_image_file`/`prompt_vehicle_name`'s cancel/blank-input error paths. |
| `test_vision_client.py` | Function | `extract_via_claude`'s happy path and its raise when Claude's response has no matching `tool_use` block. |
| `test_database.py` | Function + Module | `_flatten` (Function); `save_scale_ticket`/`save_truck_tag`/`save_trailer_tag` against a real `tmp_path` SQLite file (Module — the module's three offered operations, including row-id increment behavior). |
| `test_models.py` | Function | Dataclass defaults/structure for `TruckTagData`/`TrailerTagData`/`ScaleTicketData`/`TireSpec`. |
| `test_ocr_output_key_contracts.py` | **Interface** | Two opposite-direction key-set checks per OCR module (2026-08-22): every `_parse_fields()` key must be a declared `schemas.py` field (the FastAPI `response_model`/`extra="ignore"` silent-drop risk), and every `fields.py`/`FIELDS` name must map to a real `_parse_fields()` key (the Streamlit `_extract_fields`'s `keep`-filter silent-drop risk, opposite direction since `FIELDS` deliberately shows only a curated subset of what OCR extracts). Both exclude the same known manual-only fields (`standalone_weight_lb`, `axle_count`). Calls `_parse_fields("")` — the full key set is structurally present regardless of match success, so no synthetic label text is needed, just the shape. |

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
  cross-platform section and `NEXT_STEPS.md` for what running it against
  Kotlin found.
