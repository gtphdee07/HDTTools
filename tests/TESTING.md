# Python backend/OCR/Streamlit testing

Classifies this repo's Python test suite (`tests/`, covering
`src/hdttools/`, `src/hdttools/api/`, and `streamlit_app/`) against the
four categories defined in the root `TESTING.md`. Written 2026-08-21,
retrofitted onto tests written before that framework existed — most of
this suite predates the categories below; this is the first pass at
labeling it, not a rewrite. See `NEXT_STEPS.md` for the narrative history
of individual features/bugs each test file guards against.

`uv run pytest -q` — currently 75 tests, all passing, no markers/tiers
wired up yet (this repo has no CI; everything runs manually, matching the
root `TESTING.md`'s "session regression" model rather than a cadence).

## By file

| File | Category | Covers |
|---|---|---|
| `test_breakdown.py` | Module | `compute_breakdown`/`verdict_for`'s full public surface: axle-count/tongue-weight/pin-weight-pct math, the `estimated` flag, all four verdict tones, error-shaped edge cases (clamp-at-zero). |
| `test_api.py` | Module + **Interface** | FastAPI routing/schema validation with OCR mocked. The four `test_breakdown_endpoint_*` cases and the new `test_breakdown_endpoint_response_preserves_the_estimated_field` are genuinely interface tests — they exercise the real (unmocked) `main.py` → `breakdown.py` → `schemas.py` chain, not a mock of any of them. |
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

## Known gaps (identified 2026-08-21, not all closed)

- ✅ **Closed**: `estimated` field surviving the real `/api/breakdown`
  JSON response — nothing checked this before
  `test_breakdown_endpoint_response_preserves_the_estimated_field` was
  added; a rename/drop on either side of the `breakdown.py`/`schemas.py`
  boundary would have gone uncaught even with every other breakdown test
  passing.
- **Not yet closed**: no interface test confirms `truck_tag_ocr._parse_fields`'s
  and `trailer_tag_ocr._parse_fields`'s output keys still match what
  `TruckTagOut`/`TrailerTagOut` (schemas.py) declare, the way the new
  breakdown test does for `compute_breakdown`. Lower risk than the
  breakdown case since a genuine key mismatch here would at least show up
  as a `None` field in the UI rather than silently wrong math, but still
  an unguarded contract.
- **Not yet closed**: no test confirms `scale_ticket_ocr`/`truck_tag_ocr`/
  `trailer_tag_ocr`'s output dict keys still match what
  `streamlit_app/app.py`'s `FIELDS` dict (`fields.py`) expects to read via
  `.get()` — a silent-`None` failure mode, same shape as the truck/trailer
  API case above, just on the Streamlit side instead of the FastAPI side.
- **Cross-language, not yet started**: `compute_breakdown`/`verdict_for`'s
  Kotlin port (`android/.../Breakdown.kt`) has no shared golden-vector
  file with this suite — see the root `TESTING.md`'s cross-platform
  section. Nothing here would catch the Kotlin port silently drifting
  from a future Python-side change.
