# Test audit: Core (`src/hdttools/`)

Audited 2026-10-04 against `docs/test-audit/rules.md`. Read-only; the live Claude vision test was not run. Facts are marked **Measured** or **Read**; opinions are marked **Judgement**.

## 1. Summary

1. Worst gap: a bare `uv run pytest` on this machine makes real, billed Claude calls (`tests/test_claude_vision_external.py` skips only when `ANTHROPIC_API_KEY` is unset, and it is set here). `scripts/coverage_gate.py` and `scripts/generate_dashboard.py` both run bare pytest, so a release gate or a README regen can spend money.
2. The golden-vector fixture never puts Front Axle, Rear Axle, Trailer Axle(s) or Combined Rig Weight over their limit, never asserts note, badge, headline or subline text, and has no "tongue weight" wording check. Ports can drift on all of these with no test failing. Issues #45 and #48 change exactly these areas.
3. Offline suite: 645 passed, 4 xfailed in 33 s, 85% total statement coverage (86% for `src/hdttools` alone). The gate's enforced floor is 79%. `tests/TESTING.md` still says 156 tests.
4. Anthropic, Pillow, FastAPI and Pytesseract are called by Core but none is in `scripts/external_manifest/` (only `revenuecat-rest` and `supabase-auth` are). The one live Core boundary test has no surface tag, no call cap and no freshness record.
5. There is no per-module or per-context command: no markers, no `conftest.py`, and Core, Streamlit and script tests share one flat `tests/` folder. File-level and whole-suite runs work; context-level needs a hand-written file list.

## 2. Inventory

All counts are **Measured** (JUnit XML from the offline run; the external file excluded). The `TESTING.md` categories are applied by **Judgement** from file contents, since the repo has never tagged tests by category (`tests/TESTING.md` lines 18-28).

Whole-suite command (offline, safe): `env -u ANTHROPIC_API_KEY uv run pytest -q --ignore=tests/test_claude_vision_external.py` (bash). In PowerShell, remove the variable first with `Remove-Item Env:ANTHROPIC_API_KEY`. Runtime 33 s. Needs: local Tesseract binary (real-photo and Streamlit tests), the `ExampleDocs/` photos, no network, no secrets. The `test_external_freshness.py::test_the_real_manifest_declares_supabase_auth` test reads the real manifest and leaves unclosed SQLite connections (ResourceWarning; harmless).

| Category | Files (tests) | Notes |
|---|---|---|
| 1 Function | `test_scale_ticket_ocr_parsing.py` (6), `test_truck_tag_ocr_parsing.py` (4), `test_trailer_tag_ocr_parsing.py` (3), `test_review_form_coerce.py` (10), `test_file_picker.py` (4), `test_vision_client.py` (2), `test_models.py` (4), `test_ocr_common.py` (4), `test_breakdown.py` (20), `test_breakdown_combinatorial_sweep.py` (378), `test_real_photo_ocr_accuracy.py` (20, plus 4 xfail), `test_database.py` (5, partly module) | The sweep is generated (378 cases) and dominates the count. Real-photo tests need real Tesseract. |
| 2 Interaction | `test_streamlit_app.py` (8), `test_review_form_rebuild.py` (7) | `test_streamlit_app.py` is Streamlit-owned; it counts here only because it runs in the same suite. No interaction tests exist for Core's own modules, and none look needed (Read: Core modules share no mutable state). |
| 3 Module | `test_readers_integration.py` (9), `test_api.py` (17, the non-contract ones), `test_database.py`, `test_optional_tkinter_import.py` (1), `test_optional_anthropic_import.py` (1), `test_scale_ticket_real_photo.py` (2) | `test_breakdown.py` is also a module test of `compute_breakdown`/`verdict_for`. |
| 4 Inter-module / cross-platform | `test_breakdown_golden_vectors.py` (14), `test_ocr_output_key_contracts.py` (10), `test_api.py` (3 contract cases), `test_pass_pool_regression.py` (4), `test_fail_pool_regression.py` (2) | Fixtures: `test-vectors/breakdown_cases.json`, `pin_weight_pct_contract.json`, `breakdown_response_shape_contract.json`. |
| 5 External | `test_claude_vision_external.py` (3 live calls; not run) | Needs `ANTHROPIC_API_KEY`; about $0.01-0.03 per call per the file's own docstring (Read, lines 15-17). |
| Tooling tests (not Core code) | `test_coverage_gate.py` (4), `test_coverage_lib.py` (10), `test_dashboard_lib.py` (25), `test_record_external_result.py` (14), `test_external_freshness.py` (37), `test_external_wrapper.py` (10), `test_pass_pool.py` (4), `test_vehicle_discovery.py` (10) | Test `scripts/`. They run in the same suite and inflate the Core count. |

Total offline: 645 passed + 4 xfailed (649). `tests/TESTING.md` line 13 says 156; it is stale by about 490 tests.

Per-file and per-test runs work: `uv run pytest tests/test_breakdown.py -q`, `uv run pytest "tests/test_breakdown.py::test_blank_rig_reports_not_enough_information_not_a_false_pass"`. Note `uv run pytest tests/test_claude_vision_external.py` is a paid run on this machine.

## 3. Code coverage

**Measured** with `uv run pytest --cov` (env var unset, external file ignored, coverage data written to the scratchpad). The configured `source` is `src/hdttools` plus `streamlit_app`.

- Total: 85% (991 statements, 151 missed). `src/hdttools` alone: 86% (735 statements, 102 missed). `streamlit_app`: 81% (256 statements, 49 missed).
- 100%: `api/breakdown.py`, `api/schemas.py`, `database.py`, `models.py`, `scale_ticket.py`, `truck_tag.py`.
- Gaps of consequence:
  - `review_form.py` 46% (lines 14-21, 62-64, 70-140): the tkinter UI path. Only coercion and rebuild are tested.
  - `trailer_tag_ocr.py` 64% (40, 93-111) and `truck_tag_ocr.py` 72% (40, 110-128): the lines are the tail of each module (the `extract_*` entry points and Claude schema; **Judgement**, from line ranges only). The `extract_*_fields` Claude path is covered only by the mock tests in `test_readers_integration.py` and `test_api.py`, so the real prompt and schema are exercised only by the external test.
  - `__init__.py` 75% (23-24, 30): the `ImportError` fallback and `main()`.
  - `file_picker.py` 85% (14-21, 32): the tkinter import guard and the real dialog.
  - `vision_client.py` 88% (12-20, 55): the missing-`anthropic` guard.
  - `api/main.py` 97% (59-60): the unreadable-image 400 branch.
- Coverage gate: `scripts/coverage_gate.py` enforces a baseline floor of 79% for Python (line 40 of that script: `PYTHON_BASELINE = 79.0`); gated, fails only below the floor. Measured today: 85%, so 6 points of headroom. Read: the gate's Python run is `pytest --cov --cov-report=json -q` (lines 205-207) with no ignore of the external test, so on a machine with the key set it makes live calls. The 85% I measured excludes the external file; with it the number would be slightly higher.
- The gate measures Core and Streamlit as one number; there is no Core-only figure.

## 4. Feature coverage

Features from `src/hdttools/CONTEXT.md` and the code. Test names abbreviated.

| Feature | Verifying test | Status |
|---|---|---|
| Truck tag OCR (Tesseract) | `test_truck_tag_ocr_parsing.py`, `test_real_photo_ocr_accuracy.py` | covered; 2 xfail real-photo limits recorded |
| Trailer tag OCR | `test_trailer_tag_ocr_parsing.py`, real-photo | covered |
| Scale ticket OCR | `test_scale_ticket_ocr_parsing.py`, `test_scale_ticket_real_photo.py` | covered |
| Claude vision extraction (3 doc types) | mocked in `test_readers_integration.py`, `test_vision_client.py`; live in `test_claude_vision_external.py` | live only when run by hand |
| OCR backend switch (`HDTTOOLS_OCR_BACKEND`) | `test_ocr_common.py`, `test_api.py` | covered |
| Front/Rear axle, Trailer Axle(s) comparison | `test_breakdown.py`, fixture (success and insufficient only) | the over-limit tone for all three is **not in the fixture**; `test_breakdown.py` covers some cases |
| Tow Vehicle Total: hitched, standalone-estimate, none | `test_breakdown.py` lines 163-205, fixture | covered |
| Trailer Total: exact (hitched + standalone), axle-estimate, GVWR fallback | `test_breakdown.py`, fixture | covered |
| Pin weight pct (adjustable, 1.0 guard, 0 clamp) | `test_breakdown.py`, fixture | covered |
| Estimated flag | `test_breakdown.py` lines 209-221, fixture | covered |
| Combined Rig Weight (GVWR+GVWR today) | `test_breakdown.py` line 131 (insufficient case), fixture (success/insufficient) | over-limit Combined is not tested anywhere I found; will change with #45 |
| Verdict: fail wins, insufficient, partial, pass | `test_breakdown.py`, fixture (status only) | covered; headline and subline strings checked only for fail, partial and insufficient in `test_breakdown.py` (lines 115, 134, 160); the "Safe to Tow" headline and subline are not asserted anywhere in Python (not found by `grep`; **verify** before relying on this) |
| Half-up rounding | fixture `rounding_*` cases | covered |
| Axle count default (2) | `test_breakdown.py` line 32, fixture `custom_axle_count` | covered |
| Zero treated as not entered | `test_breakdown.py` lines 224-255, fixture | covered |
| Tongue weight (bumper-pull), Hitch Type, Receiver Rating (#2) | none | not built |
| GCWR input (#1/#45) | none | not built |
| SQLite save of tags and tickets | `test_database.py` | covered |
| Review form UI | `test_review_form_*` for logic only | the tkinter UI: none |

## 5. Interface coverage

**Our interfaces**

| Interface | Covering test | Status |
|---|---|---|
| `compute_breakdown`/`verdict_for` public shape (`label`, `tone`, `badgeLabel`, `pct`, `actualLabel`, `limitLabel`, `note`, `estimated`) | `test_breakdown.py`, `test_api.py` | covered |
| Golden-vector fixture shared with Android and Web | `test_breakdown_golden_vectors.py` (14 cases) | see gaps below |
| `/api/breakdown` request and response shape | `test_api.py` (3 contract cases), `breakdown_response_shape_contract.json` | covered, for an endpoint ADR-0007 removed from deployment |
| `pin_weight_pct` fraction convention | `test_api.py`; `web/src/api.test.ts` no longer references `pin_weight_pct_contract.json` (Read, grep) | the Web half of this contract is gone; the Python half guards an undeployed endpoint |
| OCR `_parse_fields` keys vs `schemas.py` and `streamlit_app/fields.py` | `test_ocr_output_key_contracts.py` (10) | covered |
| Reader entry points (`read_*`, `extract_*_fields`) | `test_readers_integration.py` | covered (mocked I/O) |
| Package root exports (`__init__.py`) | `test_optional_tkinter_import.py` | partial; the export list itself is not asserted |

**Golden-vector fixture gaps (Measured from the 14 cases):**
- No case has Front Axle (Steer), Rear Axle (Drive), Trailer Axle(s) or Combined Rig Weight with tone `warning`. Only Tow Vehicle Total and Trailer Total are ever over. A port that inverts a comparison on those four rows would pass.
- Only 3 cases have an item with `actual == limit`, all Trailer Total from the GVWR fallback. The `<=` boundary is not exercised for any hitched axle row, and no case sits one pound over a limit.
- Expected values contain only `verdict_status`, tone, `actual_lb`, `limit_lb`, `pct`, `estimated`. Notes, badge labels, headline and subline are not asserted by the fixture, so wording drift between ports is invisible to it. `test_breakdown.py` does assert the Python note wording, but Android and Web do not read those assertions.
- `pct` clamping at 100 is hit only incidentally.
- The `_readme` says `predictive_truck_estimate` is still unsupported on Kotlin (as of 2026-08-21) and root `TESTING.md` says 10 of 10 cases are supported; the file has 14 cases. The documents disagree (**Judgement**: stale text).

**What issues #45 to #48 will need from Core's tests** (issue #47 and #46 are the Android and Web ports of the GCWR change, #45 the Core change, #48 the wording fix; titles read with `gh issue view`):
- #45 (GCWR): fixture cases for GCWR present and under, exactly at, over; GCWR absent (Combined row omitted, which changes every existing case's `items` list, since 13 of the 14 cases currently assert a Combined row, 8 as `success` and 5 as `insufficient`); GCWR present but no gross (`insufficient`, verdict ignores it); a failing Combined wins; the neutral subline clause when GCWR was not checked. The fixture needs a `gcwr_lb` truck field and, to make the caveat clause cross-platform, either an asserted subline or a new verdict field. `test_breakdown.py` line 131 and the API contract fixture (item count, shape) will change. The Streamlit field, hint and below-GVWR warning need `test_streamlit_app.py` cases. The `verdict_for` signature may need to expose which items are advisory; `test_breakdown.py::test_verdict_status_is_never_derived_from_headline_text` and the sweep (`test_breakdown_combinatorial_sweep.py`) must be re-checked for assumptions about six rows.
- #48 (wording): `tests/test_breakdown.py` asserts the literal strings "1,660 lb tongue weight", "0 lb tongue weight" and "2,500 lb tongue weight" (lines 66, 75, 177), so it will fail on purpose and must be updated. The fixture asserts no note text, so nothing there would catch a port that still says "tongue weight". Suggest adding asserted note text, or a "no user-visible string contains `tongue`" check, to the fixture.
- #46 and #47: both ports are tested against the same fixture, so Core must land the fixture first. The change to the Python tests is only the fixture update; Android and Web carry the rest.

**Their interfaces (third-party APIs Core calls)**

| Provider | Where Core calls it | Test | Watched in `scripts/external_manifest/`? |
|---|---|---|---|
| Anthropic Messages API (tool use, base64 images) | `vision_client.py:62-93` | `test_claude_vision_external.py` (live, 3 calls); mocks elsewhere | **No.** No `anthropic` surface; pyproject pins `anthropic>=0.120.2` |
| Tesseract binary via `pytesseract` | `ocr_common.py` | offline real-photo tests (real binary) | No (system binary; no registry proxy applies) |
| Pillow | `ocr_common.py`, `api/main.py`, `scale_ticket_ocr.py` | indirectly | No |
| FastAPI, Starlette (deprecation warning for `httpx` in the test client) | `api/main.py` | `test_api.py` | No |
| tkinter | `file_picker.py`, `review_form.py` | import guard only | No (stdlib) |

Manifest holds `revenuecat-rest` (scan-proxy, android) and `supabase-auth` (web) only; neither is a Core boundary. `pyproject.toml` also lists `easyocr`, `opencv-python-headless` and `pyzbar`, which no `src/hdttools` or `tests/` file imports (only `src/experiments/BoundOCR` uses `cv2`). **Judgement**: possibly dead dependencies; not investigated further.

## 6. Spec check

- `tests/TESTING.md` line 13 claims 156 tests (153 pass, 3 xfail); actual 645 passed and 4 xfailed. Same file, "Event-based tiers" section, says a bare `pytest -q` does not skip External on this machine; that matches what I found.
- The `CONTEXT.md` states the GCWR approximation is "unintended"; `test_breakdown.py` and the fixture lock in that behaviour (`limit = truck GVWR + trailer GVWR`). They lag behind the intended behaviour (#45), as expected until it lands.
- `CONTEXT.md` says Tongue Weight is not supported and user text saying it is a bug (#48); `test_breakdown.py` asserts that text. Tests exceed the spec in the wrong direction.
- Root `TESTING.md` says Web and Python have "no real External suite"; Python gained one on 2026-09-09. `tests/TESTING.md` corrects this, the root file does not.
- Root `TESTING.md`: the golden-vector section reports 10 of 10 cases; the fixture has 14.
- `CONTEXT-MAP.md` and ADR-0007 say `src/hdttools/api/` is no longer deployed for Web. Only `api/breakdown.py` is still imported by the running Streamlit app (`streamlit_app/app.py:33`). `api/main.py` and `api/schemas.py` have no non-test caller found by `grep` (only `pyproject.toml` still lists `fastapi`, `uvicorn`, `python-multipart`). `test_api.py` (17 tests) and two of the shared contract fixtures still guard it. **Judgement**: the endpoint half is guarding something not shipped; the `breakdown.py` half is not. Whether to keep it is the owner's decision.
- The `anthropic` model name and `max_tokens` are set in `vision_client.py`; no test pins them (the live test would only catch a rejected model).

## 7. Rule fit

1. **Scope ladder.** File: yes (`uv run pytest tests/<file>`). Context: no direct command. Core, Streamlit, `scripts/` and experiment tests all sit in `tests/` with no markers, so "the Core context" means a hand-built file list. Application: yes, whole suite, but see rule 3 and the cost trap. A planner would need a file-to-context map; one can be derived from import lines.
2. **Per issue.** The issue's targeted test can be run alone by node id. A module's Minor suite (function plus interaction) cannot be selected by command; `tests/TESTING.md` says it has never tagged a fast subset, and I found no markers (`pyproject.toml` defines none). Today Minor and Major are the same run. Inter-module tests are identifiable by file name only (`test_ocr_output_key_contracts.py`, `test_breakdown_golden_vectors.py`, contract cases inside `test_api.py`, which are not selectable by file).
3. **Session end.** A whole-suite offline run takes 33 s and is cheap, but it is not safe to run as-is on a machine with `ANTHROPIC_API_KEY` set: it silently includes live paid calls. The blocker is the missing exclusion, not runtime. Quick fix is one marker plus a default deselect, or a skip tied to an explicit opt-in variable rather than the ambient key.
4. **Release.** Core has no full-run release (rule 4); it is covered through Streamlit's and Android's runs. Note the coverage gate runs bare pytest for Python, so Android's release path (which calls the gate) can reach the live test.
5. **Web gate.** Not applicable to Core directly. Core's fixture and the Web port's tests are the link; the Web gate (ADR-0008) does not watch `test-vectors/` as a boundary file for any surface. A fixture change would not mark any surface stale. **Judgement**: fine, because the gate is about external providers, but the fixture change is the one Core change that must trigger Web and Android Major runs, and nothing enforces that today (rule 8's planner script could).

## 8. Incremental complexity

Cheapest to most expensive for Core. Times are **Measured** unless marked estimate.

1. One test by node id: `uv run pytest "tests/test_breakdown.py::<test>" -q`. About 1-2 s (estimate, includes `uv` start). Needs nothing.
2. One file: `uv run pytest tests/test_breakdown.py -q`. About 2 s (estimate). Needs nothing.
3. Breakdown math plus fixture: `uv run pytest tests/test_breakdown.py tests/test_breakdown_golden_vectors.py tests/test_breakdown_combinatorial_sweep.py tests/test_api.py -q`. A few seconds (estimate). Needs nothing. This is the right set for a Core math change.
4. OCR parsing offline: `uv run pytest tests/test_*_ocr_parsing.py tests/test_ocr_output_key_contracts.py tests/test_ocr_common.py -q`. A few seconds. Needs nothing.
5. Real-photo OCR: `uv run pytest tests/test_real_photo_ocr_accuracy.py tests/test_scale_ticket_real_photo.py tests/test_pass_pool_regression.py tests/test_fail_pool_regression.py -q`. About 1.3 s per photo case, tens of seconds total. Needs Tesseract and `ExampleDocs/`.
6. Whole offline suite: `env -u ANTHROPIC_API_KEY uv run pytest -q --ignore=tests/test_claude_vision_external.py`. 33 s. Needs Tesseract. Free.
7. Offline suite plus coverage: add `--cov --cov-report=term-missing`. About 35-40 s (estimate). Free.
8. Coverage gate: `uv run scripts/coverage_gate.py`. It runs the Android and scan-proxy platforms as well when their reports are missing (device and Node needed); **do not run it with the key set** unless the live test is meant to run.
9. Live Claude vision (3 calls): `uv run pytest tests/test_claude_vision_external.py -q` with a real key. Paid, about $0.03-0.09 total by the file's own per-call estimate; the manifest has no surface or call cap for it. Not run in this audit.

## 9. Gaps and suggested tickets

Suggestions only; no issues created or edited.

1. **Make the live Claude test opt-in, not ambient-key-triggered** (rule 6; section 7). Add a marker or an explicit opt-in variable, and make `coverage_gate.py` and `generate_dashboard.py` exclude it. Small. This is the only item with a real money risk today.
2. **Fixture: add over-limit and at-limit cases for Front, Rear, Trailer Axle(s) and Combined** (section 5). Small to medium. Best done together with #45 so the fixture changes once.
3. **Fixture: assert notes, badge labels and verdict headline and subline** (sections 5, 6; needed for #45 caveat clause and #48 wording). Medium; changes the contract Android and Web must meet, so coordinate with #46 and #47.
4. **Update `tests/test_breakdown.py` "tongue weight" assertions with #48** (lines 66, 75, 177). Small; list it in #48's acceptance criteria.
5. **Add a `anthropic` External surface to `scripts/external_manifest/`** with the existing live test tagged to it, a call cap (3) and the PyPI package watched (rule 7; ADR-0008). Medium. Pillow and FastAPI are lower value; Tesseract is a system binary with no registry proxy.
6. **Add pytest markers (or a directory split) for Core, Streamlit and scripts, and for Minor, Major and contract tests** (rules 1-2). Medium. Without it, context-level and Minor-only runs stay manual.
7. **Decide the fate of `src/hdttools/api/main.py` and `schemas.py`** (ADR-0007; section 6): keep tested, or remove with its 17 tests and two contract fixtures. Small to medium; owner decision.
8. **Refresh stale docs**: `tests/TESTING.md` test count (156 vs 645), the fixture `_readme` and root `TESTING.md` "10 of 10" (now 14 cases), root `TESTING.md` External note. Small.
9. **Raise coverage of the Claude-extract tails of `truck_tag_ocr.py` and `trailer_tag_ocr.py`** (lines 93-111 and 110-128) and the `review_form.py` UI (46%). Medium; owner sets the target (rule 9).
10. **Check whether `easyocr`, `opencv-python-headless` and `pyzbar` are still needed in `pyproject.toml`.** Small; investigation only.
11. **Advisory planner script input**: a file-to-context map and a "fixture changed, so run Web and Android Major" rule (rule 8; section 7). Medium.
