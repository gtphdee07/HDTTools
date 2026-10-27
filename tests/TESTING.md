# Python backend/OCR/Streamlit testing

Classifies this repo's Python test suite (`tests/`, covering
`src/hdttools/`, `streamlit_app/` and the `scripts/` tooling) against the
categories defined in the root `TESTING.md`. Written 2026-08-21,
retrofitted onto tests written before that framework existed — most of
this suite predates the categories below; this is the first pass at
labeling it, not a rewrite. See this repo's `ARCHIVE_*.md` files (repo
root — `ARCHIVE_WEB_STREAMLIT.md`, `ARCHIVE_TESTING.md`,
`ARCHIVE_EARLY_HISTORY.md`) for the narrative history of individual
features/bugs each test file guards against.

**What to run, and when,** follows the agreed rules in
[`docs/test-audit/rules.md`](../docs/test-audit/rules.md) (the scope ladder, per issue,
session end, release), and the advisory planner
[`scripts/test_planner.py`](../scripts/test_planner.py) turns a diff into the commands
(`uv run scripts/test_planner.py --level issue|session|release`; it never blocks). The
root [`TESTING.md`](../TESTING.md) has the ladder for all five contexts. Core and
Streamlit share this one suite and this one document; Core has no release event of its
own (it is covered through the apps that use it), and neither has a full-run release.

`uv run pytest -n auto --maxprocesses=8` — real run, 2026-10-21 (#64): **1586
passed, 4 `xfail`ed** (see `test_real_photo_ocr_accuracy.py` below), 10 deselected,
in 45 s. The deselected 10 are the live `external` tests (the 5 Claude tests, 3 of them
billed calls, and 5 free Maven-registry reads); `addopts` leaves them out of any default
run, so 1,600 tests are collected in all and 1,590 selected. No CI; everything runs manually,
matching the root `TESTING.md`'s "session regression" model rather than a cadence.
The counts in the tables below are collected tests (`--collect-only`) from the same
day; the by-file table is the place to find a file's own tests, not its count.

## Markers and commands

Markers are declared in `pyproject.toml` (`--strict-markers` is on, so a typo'd marker errors). Each
test file sets a module-level `pytestmark`; a file mixing categories marks
its odd tests individually. No test files moved.

| Marker | Meaning |
|---|---|
| `external` | Live provider calls. `test_claude_vision_external.py` (billed) and `test_maven_registries_external.py` (free registry reads, #54; deliberately not marked `core`, so `-m core` stays offline). |
| `anthropic_python` | External-suite surface tag (ADR-0008) for the `anthropic-python` surface (the Python Claude vision client); always paired with `external` on the same tests. The marker is the surface name with the hyphen as an underscore. |
| `minor` | Function and interaction tests. **Unmarked for `minor` means Major.** |
| `slow` | Real-photo OCR, the Streamlit walkthrough, the combinatorial sweep, and the tooling tests that start pytest, npm, Node or Gradle (#129). The planner owes them only when the diff touches what they check, and always at release; a bare `uv run pytest` still runs them. See "Python test commands" in the root `TESTING.md`. |
| `xdist_group` | Not ours (pytest-xdist): `("gradle")` and `("node")` keep the checks that start those tools on one worker under `-n auto` (`--dist loadgroup` is in `addopts`). |
| `core` | `src/hdttools` and the `scripts/` tooling tests (tooling rides with Core). |
| `streamlit` | Tests that drive `streamlit_app/` (`test_streamlit_app.py`). |

`addopts = -m "not external"`, so bare `pytest`, `scripts/coverage_gate.py`
and `scripts/generate_dashboard.py` never select the live tests, whatever
`ANTHROPIC_API_KEY` is set to. A selected live test with no key does not skip: its
autouse `_require_api_key` fixture fails it (a skip would exit 0 and record a false
pass; see "Per-surface External suite" below). And `tests/conftest.py` makes any
unmarked test that reaches the real Anthropic client (`anthropic.Anthropic`, the
only provider client this suite uses) fail (`test_live_provider_guard.py` checks it).

| Level | Command | Tests |
|---|---|---|
| One file | `uv run pytest tests/test_breakdown.py` (any file; a `-k` or node id narrows it) | that file's |
| Minor only, one context (per issue) | `uv run pytest -m "minor and core"` / `-m "minor and streamlit"` | 1,377 / 19 |
| Minor only, whole app | `uv run pytest -m minor` | 1,396 |
| Fast Minor | `uv run pytest -m "minor and not slow"` | 990 |
| One context | `uv run pytest -m core` / `-m streamlit` | 1,571 / 19 |
| Context, session end (the planner's command) | `uv run pytest -n auto -m "core and not slow"` / `uv run pytest -m "streamlit and not slow"` | 1,153 / 17 |
| Application, session end | `uv run pytest -n auto -m "not slow and not external"` | 1,170 |
| Major, everything offline (the slow tests included), parallel | `uv run pytest -n auto --maxprocesses=8` (45 s on 2026-10-21; the serial `uv run pytest` is the same tests, about 170 s in #129) | 1,590 |
| Slow tests only (owed when the diff touches what they check, always at release) | `uv run pytest -n auto -m "slow and not external"` | 420 |
| External (live) | `uv run pytest -m external` | 10: the 5 Claude tests (3 billed calls, 2 free) + the 5 free Maven ones below |
| Maven registry guard (live, free, about 10 s) | `uv run pytest -m external tests/test_maven_registries_external.py` | 5 |

Counts are collected tests (`--collect-only -m ...`), 2026-10-21. The Minor,
Major and External columns of the ladder are the root `TESTING.md`'s; this table is only
how each is selected here. The slow tests are 420 of the 1,590. In the parallel run they
add about 15 s (1,170 non-slow tests took 29 s, everything 45 s, 2026-10-21) but they start
pytest, npm, Node or Gradle themselves, which is why the planner leaves them out of
per-issue and session-end runs unless the diff touches what they check (root `TESTING.md`,
"Python test commands"). `core` and
`streamlit` do not overlap, but `test_ocr_output_key_contracts.py` (marked `core`) also
checks Streamlit's `fields.py`, and `test_live_provider_guard.py` is
marked `core`. A **Major** run is everything except `external`; a Minor
run is a subset of it. Live tests run on purpose only, after the owner
confirms the cost (about $0.01-0.03 per call).

**Release.** Core and Streamlit have no full-run release; their release evidence is the
slow set above (always listed at release level) plus the Android and Scan Proxy release
runs that use them. **Session end** is the whole file, context or application, by the
size of the diff (`uv run scripts/test_planner.py --level session`); a suite that already
passed at this exact tree is not re-run (the verification ledger, `test_verification_ledger.py`
below).

The earlier real-environment gotcha — this dev machine has
`ANTHROPIC_API_KEY` set ambiently, so a bare run used to make real billed
calls (confirmed 2026-09-09) — is closed by the default `-m "not external"`.

## Per-surface External suite: `anthropic-python` (ADR-0008, #37, #143)

The `anthropic-python` surface (boundary file `src/hdttools/vision_client.py`,
pins `pyproject.toml` and `uv.lock`, the PyPI `anthropic` watch; manifest entry
`scripts/external_manifest/surfaces/anthropic-python.json`, platforms
`core`/`streamlit`, owner `core`, `max_paid_calls` 3) is covered by
`test_claude_vision_external.py`, every case tagged with the `anthropic_python`
marker (ADR-0008's "marker for pytest" convention — the surface name with the
hyphen as an underscore, matched by `scripts/external_wrapper.py`'s
`tagged_in(..., tag_style="marker")` as a `mark.anthropic_python` text search).
The Worker's `claude.ts` is a different surface, `anthropic` (see
`workers/scan-proxy/TESTING.md`); until #143 the two shared one record, and the
Worker's run cleared the Python half unseen. **The repo-root
`.\test-external.ps1` (platform `core`) runs and records `anthropic-python`
when it is stale**, and the Worker's wrapper does not list it. A direct run is
`uv run pytest -m "external and anthropic_python"` (paid, needs the owner's
go-ahead; a direct run records nothing). Its first real pass was recorded
2026-10-20 (3 paid calls; `scripts/dashboard_data/external_status.json`). Needs
`ANTHROPIC_API_KEY`; a missing key fails the run (an autouse
`_require_api_key` fixture calls `pytest.fail`, not `pytest.skip` - a skip
would exit 0 and the wrapper would record a false `pass` for a surface
never actually exercised, exactly what ADR-0008 rejects). Collection still
succeeds without the key, so a key-less default run (which deselects
`external` entirely before setup) is unaffected. `-Skip` records `skipped`
without ever invoking pytest.

Each surface's recorded result comes from its own tagged tests, not the run's
single exit code (#89): the wrapper gives every runner an
`EXTERNAL_RESULTS_FILE` to write JUnit XML to (pytest here, through
`scripts/external_surface_plugin.py`, which adds each marked test's surface as
a `surface` property; vitest and `node --test` on the TS platforms), and
`external_wrapper.surface_results` counts passed/failed/skipped per surface.
A surface passes only if none of its tests failed and at least one passed;
with no per-test data, or a non-zero exit nobody's tests account for, the
exit code decides every surface as before. Covered by `test_external_wrapper.py`
(decision logic on fake results) and `test_external_surface_results.py` (the
pytest side, against a throwaway pytest run). Android's `test-weekly.ps1` does
not use this wrapper (it records the legacy platform+suite entry the gate
ignores), so it is unaffected.

Depths covered: reachable and authenticated
(`test_a_bad_key_is_rejected_with_a_real_auth_error` — a wrong key raises
`anthropic.AuthenticationError`, free); error contract
(`test_a_corrupted_image_is_rejected_before_any_billed_model_call` — a
truncated real image raises `anthropic.BadRequestError` before any model
call, free, same reasoning as `scan.weekly.test.ts`'s equivalent Worker-side
case); response shape and full journey
(`test_claude_vision_extraction_matches_the_shared_golden_values`,
parametrized over the cases in `test-vectors/vision_external_cases.json` —
one fixed photo per doc type, the same three photos the Worker's suite uses,
each compared value by value to its `ExampleDocs/golden_fields.json` entry
through `scripts/vision_cases.py`; a mismatch on a `known_ocr_limitations`
field is tolerated, any other fails. **The only billed part of this file:
exactly 3 real calls**, matching the manifest's `max_paid_calls: 3`). The
random pass-pool pick stays for the free Tesseract tests that use it
(`scripts/pass_pool.py`), not here.

`test_vision_shared_fixtures.py` is the free offline half (no Claude call): it
fails if a shared case names a missing photo or golden entry, if a doc type has
no case, if `test_claude_vision_external.py` stops running exactly the shared
cases, or if a reader's tool name, property names or required names differ from
`test-vectors/vision_tool_schemas.json` (the Worker checks the same file in
`workers/scan-proxy/src/visionSharedFixtures.test.ts`).

`test-vectors/scan_form_fields.json` (#162, under epic #147) sits beside it: per
doc type, the fields every surface's review form shows, as `scanned` (a Scan
can fill them; each must be a property of that doc type in
`vision_tool_schemas.json`) and `manual_only` (shown, never returned by a
Scan), each with a `text` or `number` type. `test_scan_form_fields_fixture.py`
checks the file against the tool schema file and Streamlit's `FIELDS`
(name and type, both directions); Web (#163) and Android (#164) check their own
forms against it.

Review of the pre-existing file against the four depths (#37): before this
ticket, it covered only response shape and journey (added for roadmap item
#16); reachable-and-authenticated and the malformed-image error contract
were gaps, now filled by the two new free cases above. No older Python
suite exists to leave untouched here — this was the first (and remains the
only) External-tier file on this platform.

## Coverage

`pytest-cov` is a dev dependency; `[tool.coverage.run]`'s `source` in
`pyproject.toml` covers both `src/hdttools` and `streamlit_app` (widened
to include the latter 2026-08-24, see `ARCHIVE_WEB_STREAMLIT.md` —
previously `streamlit_app/` had zero coverage measurement at all). Real, repeatable
command:

```bash
uv run pytest -n auto --cov --cov-report=term-missing
```

(Bare `--cov` — no `--cov=PATH` needed — because `[tool.coverage.run]`'s
`source` already tells coverage.py what to measure; the gate runs the same command
with `--cov-report=json`.) The live tests stay deselected, so coverage never makes a
billed call. Real numbers, 2026-10-21 (`uv run scripts/coverage_gate.py --refresh`):
**87.78% of statements** (747 of 851), of which `src/hdttools/` is 83.2% (495 of 595)
and `streamlit_app/` 98.4% (252 of 256). The files under 90% are the interactive
ones, plus code that only a subprocess test reaches: `review_form.py` 46% (the Tkinter
window, the thin GUI glue this project accepts as untested), `trailer_tag_ocr.py` 64%
and `truck_tag_ocr.py` 72% (each one's missed lines are the interactive
`read_*_ocr()` entry point: file picker, review window and save, none of it run here),
`file_picker.py` 85%, `vision_client.py` 88% (the `anthropic`-not-installed branch,
which `test_optional_anthropic_import.py` proves in a real subprocess that coverage does
not see) and `__init__.py` 75%. `scripts/` is not
in `source`, so the tooling tests below have no coverage number. Kept as an explicit,
separate command rather than a default `addopts` — coverage reporting stays a
deliberate check, not overhead on every routine run.

**The enforced floor is 79%.** `scripts/coverage_gate.py` fails Python only below
that number, which is the 2026-08-24 baseline and not the measured one; the measured
87.78% passes with 8.8 points to spare. Whether to raise the floor is the owner's call
(rule 9 of `docs/test-audit/rules.md`: no targets are set until the owner has seen the
numbers). See the root `TESTING.md`'s "Coverage gate" section.

**Structured pass-rate reporting for the README dashboard** (roadmap
item #7, new 2026-08-24): `scripts/generate_dashboard.py` runs one pytest per tier
and context with `--junitxml=junit-<context>-<tier>.xml` (repo root, gitignored):
`-m "minor and core"` and `-m core` for Core, `-m "minor and streamlit"` and
`-m streamlit` for Streamlit, so the Minor and Major cells are different numbers
(they were the same until the markers of #50) — see the root `TESTING.md`'s
"Dashboard" section.

## Static checks

Core's and Streamlit's static checks are one command each (#150), listed by the planner when the
context's files change and run and recorded by `/ticket-finish`; they run beside the tests above, not
instead of them. Offline, no paid call. What each step covers, and what no check covers yet, is
[`docs/agents/static-checks.md`](../docs/agents/static-checks.md).

| Command | Steps | Exit rule |
|---|---|---|
| `uv run scripts/static_checks.py core` | ruff over `src/hdttools`, `streamlit_app`, `scripts`, `tests`; vulture on the code; vulture on `tests/` | 0 only when all three exit 0; every step runs even after one fails |
| `uv run scripts/static_checks.py core --coverage` | the above, then the Python coverage floor (the whole suite under coverage.py, about a minute) | the floor is 79% (`scripts/coverage_gate.py --only python --refresh`); the planner uses this form when `src/hdttools/` or `scripts/` changed |
| `uv run scripts/static_checks.py streamlit`, or `uv run scripts/static_checks.py streamlit --coverage` when `streamlit_app/` changed | ruff over `streamlit_app`, the same two vulture passes, the floor with `--coverage` | the same |

ruff runs through `uv run ruff` with the rules in `ruff.toml` (the correctness rules,
pyflakes `F` and the pycodestyle `E4`, `E7`, `E9`); it is a dev dependency, pinned exactly
(`ruff==0.17.1`) in `pyproject.toml` and locked in `uv.lock` (#160). There is no Python type checker yet (#155).

## Dead code

`vulture` is a dev dependency (added 2026-08-24, see `ARCHIVE_DEAD_CODE.md`):

```bash
uv run vulture src/hdttools streamlit_app scripts vulture_whitelist.py   # production code and tooling
uv run vulture tests vulture_whitelist_tests.py                          # the tests, on their own
```

Since #150 `scripts/` is scanned too, and `tests/` is a second pass of its own with its own
whitelist (scanned together with `src/`, a function that only its own test calls would count as
used and real dead code would hide). Both exit 0, and `uv run scripts/static_checks.py core` runs
them with ruff. `tests/test_static_checks_real.py` fails when a name in either whitelist is no
longer reported, so an entry cannot outlive the code it excuses. The history below is the first
sweep (2026-08-24), kept as written.

Real run against `src/hdttools`/`streamlit_app` found 65 "unused"
findings at default confidence, 2026-08-24 — every single one a false
positive across three known categories (see `vulture_whitelist.py`'s own
comments for the full reasoning, spot-checked against real code before
being whitelisted, not blindly kept from vulture's own
`--make-whitelist` stub): FastAPI route handlers (reachable only via
`@app.post(...)` decorators, e.g. `extract_truck_tag`), Pydantic/
dataclass model field declarations (`schemas.py`/`models.py` — a
well-known vulture false-positive class), and this repo's deliberate
public library API (`read_scale_ticket`/`read_truck_tag`/
`read_trailer_tag`/etc. — see `README.md`'s "Underlying toolkit"
section; meant for external callers, so "no in-repo caller" is expected,
not a sign of dead code). **No genuine dead code found** beyond the one
already-known candidate closed before this tool was even installed —
see `ARCHIVE_DEAD_CODE.md` for `parse_label.py`'s closure. With the
whitelist applied, the command above exits clean (0 findings). The
FastAPI-handler category and the `schemas.py` fields left the whitelist
when the app was removed (#135); `models.py` fields and the public
library API remain.

## By file

| File | Category | Covers |
|---|---|---|
| `test_breakdown.py` | Module | `compute_breakdown`/`verdict_for`'s full public surface: axle-count/pin-weight/pin-weight-percentage math, the `estimated` flag, all four verdict tones, error-shaped edge cases (clamp-at-zero), and the optional truck GCWR (#45): the Combined Rig Weight row exists only with a GCWR, never uses the GVWR sum, and as the Advisory Item never lowers the verdict when insufficient. |
| `test_breakdown_golden_vectors.py` | **Cross-platform interface** | Runs `compute_breakdown`/`verdict_for` against `test-vectors/breakdown_cases.json`, the same cases the Kotlin port's `BreakdownGoldenVectorTest.kt` checks itself against — see the root `TESTING.md`'s cross-platform section. |
| `test_scale_ticket_ocr_parsing.py` | Function | `_parse_fields`/`_find_str`/`_find_num` against transcribed OCR text, including a real (garbled) tow-vehicle-only ticket transcription. |
| `test_truck_tag_ocr_parsing.py` | Function | `_parse_fields`/`_kg_lb` against transcribed OCR text, including a real garbled "LB read as 1B" regression case. |
| `test_trailer_tag_ocr_parsing.py` | Function | `_parse_fields` against transcribed OCR text. |
| `test_scale_ticket_real_photo.py` | Function | Real Tesseract against a real `ExampleDocs/` file: `_parse_fields` on the real tow-vehicle-only ticket (real input, one function). Its `/api/extract/scale-ticket` upload case went with the FastAPI app (#135); real photo bytes through `Image.open` are still covered by `test_streamlit_app.py`'s real-photo cases. |
| `test_real_photo_ocr_accuracy.py` | Function, real-photo, parametrized | New 2026-08-24 (closes item #7's truck/trailer real-photo OCR gap too). Real Tesseract against every real `ExampleDocs/` photo in `ExampleDocs/golden_fields.json`'s `"photos"` — one parametrized case per field, so a future brand/format needs only a new JSON entry, no new test code. Found and fixed two real regex bugs (a stray OCR glyph breaking `truck_tag_ocr._kg_lb`'s label match; a comma `scale_ticket_ocr`'s `location_name` prefix didn't tolerate) — see `ARCHIVE_WEB_STREAMLIT.md`. Two remaining real OCR-accuracy limits (a digit-drop, a two-column layout jumble) are `xfail(strict=True)` with the real reason recorded on `golden_fields.json` — a value real OCR doesn't currently produce is never silently asserted or hidden. |
| `test_readers_integration.py` | Module | Each `read_*_tag`/`read_scale_ticket`'s one public entry point, every I/O boundary (file picker, vision, review form, database) mocked. Explicit sequential composition (each step's output passed to the next as an argument) — no implicit shared state, so this is module-surface testing, not interaction testing, despite the docstring's "orchestration and control flow" framing. New 2026-09-09: also covers the new headless, pure `extract_truck_tag_fields`/`extract_trailer_tag_fields`/`extract_scale_ticket_fields` (`truck_tag.py`/`trailer_tag.py`/`scale_ticket.py`) directly — `extract_via_claude` mocked, no file picker/review form/database involved at all, proving the `TireSpec(**fields.pop(...))` unpacking these functions now share with `read_*_tag()` (which was refactored to call them, removing the old inline duplication). |
| `test_streamlit_app.py` | **Interaction**, real-photo | The clearest interaction-test example in this repo. `_render_review` and `_render_standalone_ticket_section`/`_module_step` in `streamlit_app/app.py` share `st.session_state` implicitly, across reruns — these tests drive the real multi-step sequence and assert the net state, which is exactly what caught the real stale-widget-value bug a solitary test of either function could not have seen. `test_full_walkthrough_with_real_photos_reaches_a_real_verdict` (new 2026-08-24, parametrized over `golden_fields.json`'s `"rigs"`) is the first test anywhere in this repo to drive all four real ExampleDocs/ photos of one rig (truck tag, standalone ticket, trailer tag, full-rig scale ticket) through the real app to a real, hand-verified Results verdict — every prior "full walkthrough" (this file and `web/`'s Playwright suite both) only ever exercised the zero-image, skip-everything path. New 2026-09-09: `test_claude_backend_*_upload_calls_the_matching_extractor` cases (one per module) set `HDTTOOLS_OCR_BACKEND=claude` and mock the matching `extract_*_fields` function, proving `_extract_fields`'s dispatch and the `keep`-filtering against `fields.py`'s `FIELDS` still work identically on that branch; `test_claude_backend_never_shows_the_tesseract_raw_text_warning` is the regression case for the real edge found during design — the `app.py:169` "Tesseract returned no text" warning is keyed off `raw_text.strip()`, which is always empty under Claude (no raw OCR text exists on that path), so it now also checks `get_ocr_backend() == "tesseract"` before firing. New 2026-10-04 (issue #56, closes the test-audit's worst-flagged gap): `test_results_is_hidden_until_the_disclaimer_is_acknowledged` is the first test to assert Results is actually gated on `disclaimer_acknowledged` rather than just click through it (confirmed it fails if the gate is removed), alongside a wording check, plus mocked-Claude-backend tests for the recent-rig chooser, `Start Another Check`'s reset (and what it deliberately leaves alone), the `Build Estimated Model` skip button and the predictive-estimate notice it makes reachable, the pin-weight slider feeding `compute_breakdown`'s axle-estimate branch, a "pass" verdict (the first anywhere in this repo), and the three OCR-failure/no-weight-found error branches for both the main and standalone-ticket uploads. Raised `streamlit_app/app.py` coverage from 81% to 99%. |
| `test_review_form_coerce.py` | Function | `_coerce`'s type conversion + its `ValueError` on invalid input. |
| `test_file_picker.py` | Function | `select_image_file`/`prompt_vehicle_name`'s cancel/blank-input error paths. |
| `test_optional_tkinter_import.py` | Module, real subprocess | New 2026-09-18 — regression test for a real bug (see `ARCHIVE_WEB_STREAMLIT.md`): `file_picker.py`/`review_form.py`'s tkinter imports are now guarded (`try/except ImportError`), so `hdttools.scale_ticket`/`trailer_tag`/`truck_tag`/`file_picker`/`review_form` all import cleanly even where tkinter's system library isn't installed (e.g. Streamlit Community Cloud), and `select_image_file`/`review_and_edit` raise a clear `RuntimeError` instead of a raw `ImportError` if actually called there. Runs in a real subprocess with `sys.modules["tkinter"] = None` rather than monkeypatching this process's own already-imported modules, to avoid poisoning other tests' module state. |
| `test_optional_anthropic_import.py` | Module, real subprocess | New 2026-09-18 — regression test for a second, same-day real bug (see `ARCHIVE_WEB_STREAMLIT.md`): `vision_client.py`'s `anthropic` import is now guarded the same way, since `streamlit_app/requirements.txt` (a separately maintained file Streamlit Community Cloud prefers over `pyproject.toml`) had drifted out of sync and didn't list it. Same real-subprocess technique as `test_optional_tkinter_import.py`. |
| `test_vision_client.py` | Function | `extract_via_claude`'s happy path and its raise when Claude's response has no matching `tool_use` block. Signature changed 2026-09-09: takes `image_bytes: bytes, media_type: str` rather than `image_path: Path` — both real callers (`main.py`'s `UploadFile`, Streamlit's `UploadedFile`) already have bytes in memory, so the old disk read (`image_path.read_bytes()`) was dropped rather than gaining a temp-file indirection. The three interactive callers (`truck_tag.py`/`trailer_tag.py`/`scale_ticket.py`) now compute bytes/media-type at their own call site via the new `vision_client.image_bytes_and_media_type()` helper. |
| `test_database.py` | Function + Module | `_flatten` (Function); `save_scale_ticket`/`save_truck_tag`/`save_trailer_tag` against a real `tmp_path` SQLite file (Module — the module's three offered operations, including row-id increment behavior). |
| `test_models.py` | Function | Dataclass defaults/structure for `TruckTagData`/`TrailerTagData`/`ScaleTicketData`/`TireSpec`. |
| `test_ocr_common.py` | Function | New 2026-09-09 (see `ARCHIVE_WEB_STREAMLIT.md`'s item #16 entry).
`get_ocr_backend()` — defaults to `"tesseract"` when `HDTTOOLS_OCR_BACKEND` is unset, reads an explicit `"tesseract"`/`"claude"` value, and raises `ValueError` (fail loud, no silent fallback) on anything else. |
| `test_ocr_output_key_contracts.py` | **Interface** | Every `fields.py`/`FIELDS` name must map to a real `_parse_fields()` key (2026-08-22): `streamlit_app/app.py`'s `_extract_fields` keep-filter silently drops a field that has no matching OCR key, and `FIELDS` deliberately shows only a curated subset of what OCR extracts, so the check runs in this one direction. Excludes the known manual-only fields (`standalone_weight_lb`, `axle_count`). Calls `_parse_fields("")` — the full key set is structurally present regardless of match success, so no synthetic label text is needed. The opposite direction (every OCR key declared on the FastAPI response models) went with the FastAPI app (#135). New 2026-10-21 (#140): a second, parametrized check that every `FIELDS` name (same manual-only exclusions) is a property of the matching doc type in `test-vectors/vision_tool_schemas.json`, so the same keep-filter cannot silently drop a field on the Claude-vision path (a dev-only comparison under ADR-0002). Web (#148) and Android (#149) get the same check on their side, under epic #147. |
| `test_claude_vision_external.py` | **External** | New 2026-09-09 — the first External-tier test on this platform (see the root `TESTING.md`'s "Event-based tiers, not time-cadence tiers"). Marked `external` and `anthropic_python`, so a default run deselects it; a missing `ANTHROPIC_API_KEY` fails it (never skips); one real Claude vision call per doc type, since #143 against the fixed photo the shared `test-vectors/vision_external_cases.json` names for it (not a random pass-pool pick), asserting no *new* mismatch against `golden_fields.json`'s documented fields beyond what `known_ocr_limitations` already records (a deliberately looser tolerance than `test_pass_pool_regression.py`'s strict equality — see that file's own docstring for why). Surface `anthropic-python`. |
| `test_vision_shared_fixtures.py` | **Cross-platform interface** | New 2026-10-20 (#143) — free drift checks for the two Claude vision implementations: every case in `test-vectors/vision_external_cases.json` has an existing photo and `golden_fields.json` entry and every doc type has a case; `test_claude_vision_external.py` runs exactly those cases; the golden-value comparison rule; and each reader's tool name and schema property/required names against `test-vectors/vision_tool_schemas.json`. The Worker's `visionSharedFixtures.test.ts` runs the same checks on its side. |
| `test_scan_form_fields_fixture.py` | **Cross-platform interface** | New 2026-10-21 (#162, under epic #147). Free checks on `test-vectors/scan_form_fields.json`, the shared list of fields each surface's review form shows, per doc type, with a `text` or `number` type: it has exactly the doc types of `vision_tool_schemas.json`, every `scanned` name is a property of its doc type there, no `manual_only` name is, every type is `text` or `number`, no name appears twice; and Streamlit's `FIELDS` equals `scanned` plus `manual_only` as `(name, type)` pairs, so a dropped, extra or retyped field fails. Each check also runs against a deliberately broken copy to show it can fail. No network, no Claude call. Web (#163) and Android (#164) read the same file. |
| `test_coverage_gate.py` | Function | New 2026-08-24. `../scripts/coverage_gate.py`'s `PlatformResult.passed` baseline-floor logic, loaded via `importlib` since the script lives outside the `hdttools` package. The report parsers themselves moved to `coverage_lib.py` 2026-08-24 (item #7) — see `test_coverage_lib.py` below. The `get_*_result` functions that actually shell out to each platform's toolchain (gradlew/pytest/npm) are deliberately not unit-tested here — thin I/O glue, exercised for real by the script's own manual runs (see `ARCHIVE_TESTING.md`). Extended (#150): `--only python` and `--only scan-proxy` run that platform's floor alone (what the static-check commands call), pass `--refresh` through, and exit non-zero below the floor (fake getters; the others must not be called). |
| `test_coverage_lib.py` | Function | New 2026-08-24 (roadmap item #7). `../scripts/coverage_lib.py`'s four pure coverage-report parsers (`parse_android_report`/`parse_python_report`/`parse_web_report`/`parse_scan_proxy_output`), shared by `coverage_gate.py` and `generate_dashboard.py` — extracted from `test_coverage_gate.py` when the parsers themselves moved out of that script. |
| `test_dashboard_lib.py` | Function | Extended 2026-10-19 (#44): failed/skipped counts, the per-surface list (every state, planned reads "not covered"). Extended 2026-10-04 (#49): surfaces column, per-file Python coverage, snapshot rows, results note. New 2026-08-24 (roadmap item #7). `../scripts/dashboard_lib.py`'s `color_for_percent` threshold banding, `parse_junit_xml` (real schema differences across pytest/Vitest/Android/Node's JUnit XML output — see that module's own docstring), `format_surface_cell`, and `render_dashboard_svg` (well-formedness + content checks, not a pixel-level snapshot). |
| `test_generate_dashboard.py` | Function | New 2026-10-04 (#49), reworked 2026-10-19 (#44). `../scripts/generate_dashboard.py` decision logic: pytest selections per tier, rows from snapshot plus live External cells, every surface state from a fake manifest, status file and git (no registry contacted), old platform+suite entries not shown as current, and `--from-snapshot` running no suite. Suite runners are I/O glue and not run here. |
| `test_context_test_commands.py` | Command checks | New 2026-10-04 (#52). The documented file-level and context-level test commands for Web, Scan Proxy and Android JVM select the intended files and never a live or device test. Web and Scan Proxy commands are run for real (offline, seconds); Android reads Gradle's dry-run task graph. Also checks each context's `TESTING.md` lists the commands. Its two Scan Proxy command checks first call `require_proxy_install` (#82), so a missing `npm install` fails with the install instruction instead of a 502. |
| `test_scan_proxy_install_guard.py` | Command checks | New 2026-10-10 (#82). Running the Scan Proxy tests without `npm install` stops with the install command instead of "expected 200, got 502". Runs every top-level proxy test file, and `npm test`, against a temp copy of the proxy that has no `node_modules`; also checks each top-level `*.test.ts` imports `requireInstall.ts` first, and that the wrapper precondition `require_proxy_install` fails with the same message. Needs Node, no install. |
| `test_scan_proxy_knip_config.py` | Command check | New 2026-10-21 (#152). `workers/scan-proxy/knip.json` keeps `npm run check:dead-code` exiting clean: it must list `uv` under `ignoreBinaries` while a `package.json` script (`deploy`) runs `uv`, and it must be the only knip configuration (no second config file, no `knip` key in `package.json`, which pins three External surfaces). Static checks read the files knip reads; one `slow` test (Node group, about 1.5 s) runs the real `npm run check:dead-code` and needs it to exit 0. Added at the merge review: `knip.json` is tracked and matches no External surface's `boundary_files` or `dependency_pins` (so editing it never marks a surface stale), `package.json` stays the pin of `anthropic`, `scan-proxy-worker` and `worker-token-verification`, and `workers/scan-proxy/TESTING.md` says the command exits clean (no stale wording, no open gap for it). Removing the entry fails the static and the real-run test. The planner owes the slow test when `knip.json`, `package.json` or `scripts/*` change. |
| `test_scan_proxy_coverage_guard.py` | Command check | New 2026-10-21 (#151). Scan Proxy's coverage gate passes at its 100.00% line floor without a test that signs in: `liveTokenCli.ts` carries a `/* node:coverage ignore next 3 */` comment on its run-as-script guard (the owner's choice over lowering the floor or splitting an entry file). One `slow` test (Node group, about 1 s) runs Node's real `--experimental-test-coverage` over `liveTokenCli.test.ts` alone and needs the file at 100% of lines; a static test pins the ignored range to exactly the guard block (nothing else can hide under the comment); a third checks that `TESTING.md` and `workers/scan-proxy/TESTING.md` name the exclusion and no longer report the gate as failing. Dropping or misplacing the comment fails the first two. The planner owes the slow test when `liveTokenCli.ts`, its test or `scripts/coverage_gate.py` change. |
| `test_android_file_command_slow.py` | Command check (`slow`) | New 2026-10-04 (#52). Really compiles and runs `./gradlew testDebugUnitTest --tests ...BreakdownTest` and asserts exactly that class ran. Not `minor`, so the fast run skips it; an unfiltered `uv run pytest` runs it and the planner owes it when the test commands change and at every release. |
| `test_android_release_key_guard.py` | Build-guard checks (one `minor`, the rest `slow`) | New 2026-10-21 (#166). The Android release build refuses a RevenueCat Test Store key. Runs `:app:verifyRevenueCatReleaseKey` alone (no release build): a missing, empty, `test_`, `TEST_` and space-padded `test_` key fail naming the key (never printing it), a `goog_` key passes from the Gradle property and from `REVENUECAT_RELEASE_API_KEY`; Gradle's dry-run graph shows `assembleRelease`, `bundleRelease`, `packageRelease` and `packageReleaseBundle` run the guard first while `assembleDebug` and `test` do not need it; the generated `BuildConfig` has the Test Store key in debug and the given key (empty if none) in release; and `RigCheckApplication.kt` holds no key literal. The Gradle checks share the `gradle` xdist worker. Mutation-checked: dropping the `test_` rule, the blank rule or the release wiring each fails its tests. |
| `test_android_beta_build.py` | Build-guard checks (one `minor`, the rest `slow`) | New 2026-10-23 (#174). The Android `beta` build type: `:app:verifyBetaSigning` alone fails when the keystore path, alias or password is missing, blank or padded, names only the missing property and never prints a value, and passes with all three (from properties, and from the environment variables); `assembleBeta`, `bundleBeta`, `packageBeta` and `packageBetaBundle` run it first while debug, release and `test` need neither it nor any beta task; the generated `BuildConfig` has the Test Store key only in debug and beta and `IS_BETA` true only in beta; no keystore path, alias or password literal is in `android/`; and one check packages a real beta APK with a throwaway keystore made in a temp folder and proves `keytool -printcert -jarfile` shows that key's SHA-1, the package is `com.rigcheck.app`, `versionCode`/`versionName` follow `appVersionCode` and `1.0-beta`, and the manifest is debuggable (RevenueCat's SDK closes a non-debuggable app that uses the Test Store key, #185) (it skips when the beta dependencies are not in the offline Gradle cache). Command-line properties beat the owner's `~/.gradle/gradle.properties`, so the checks never touch the real keystore. The Gradle checks share the `gradle` xdist worker. |
| `test_verification_ledger.py` | Function tests | New 2026-10-18 (#65). `../scripts/verification_ledger.py`, the local verification ledger: the last commit (and its tree hash, `HEAD^{tree}`) whose suites passed, per context and level (issue, session, release), in a file inside the shared git directory (never tracked). Lookups are by tree, so an amend or a no-content merge commit reuses a pass and any content change loses it (#128 builds on this). Only `uv run scripts/verification_ledger.py run --context C --level L -- <test command>` writes it, and only when the command passes on a clean tree with HEAD unchanged during the run; a failed, unstartable or skipped run leaves the previous record untouched. `check` and `show` answer "is this context verified at this commit?" (verified / stale / unverified). Fake git and a fake runner; the ledger file lives in `tmp_path`. Extended 2026-10-19 (#128) with per-suite passes: each suite command remembers every tree it passed at (newest 25 kept), `suite_verdict` answers "did suite S pass at tree T?" and never raises (a failed, skipped or declined record, a missing ledger and an unreadable or malformed one all give "run it"), a non-pass result drops a pass held for the same tree, and `suite` / `check-suite` are the CLI; one real-git test shows an amend reuses a pass and a content change does not. |
| `test_test_planner.py` | Function + command checks | New 2026-10-04 (#60). `../scripts/test_planner.py`, the advisory planner (`uv run scripts/test_planner.py [--level issue|session|release] [--files ...]`; always exits 0): fake config and marker set drive the rules (Minor of the touched context; a public-interface or dependency change forces Major; interface tests added; changed test files first). The command checks run real `pytest --collect-only` on each planned selection to confirm it collects tests, none of them external, and that an interface selection runs exactly its file. Config: `../scripts/test_planner_config.json`. Extended 2026-10-21 (#150), against the real config: each of core, streamlit, web and scan-proxy lists its `session_end` static-check command at session level when a file of the context, one of its `static_triggers` or a dependency file changed (the Python coverage form only when `src/hdttools/`, `streamlit_app/` or `scripts/` changed), none for a docs-only change or at the issue level, and the command runs beside the context's suite where Android's replaces it (`session_end_runs_tests`); every `session_end` argument is one `static_checks.py` accepts. A test file the branch deleted is not planned to run (#135; pytest exits 4 on a missing file). Extended 2026-10-04 (#61) to every context (Web, Android, Scan Proxy, Streamlit, Core) and to `--level session` (scope ladder: file, context, application; stale surfaces) and `--level release` (everything for Android and Scan Proxy, the Web freshness gate; stale paid surfaces and the old paid suites marked `[CONFIRM]`, never run). Android instrumented tests are planned only when the diff touches device-covered code, or at release. The non-Python commands in the config now match what #52 documents and tests; `test_context_test_commands.py`'s planner-config checks fail if they drift. Extended 2026-10-19 (#128): each listed suite is marked `already passed at <tree>` or `run` from the ledger (a fake `passed_at` lookup; a broken ledger marks everything `run`), the `To run:` line omits passed suites, and `suite_affected` decides which suites a changed file can alter (a Python suite counts any file; docs and tests reach only Python suites; an unowned unknown file reaches all). |
| `test_worktree_setup.py` | Function + interaction | New 2026-10-10 (#83). `../scripts/worktree_setup.py`, the one-step bootstrap for a fresh git worktree (`docs/agents/worktree-setup.md`): the plan (`uv sync`, then `npm ci` in Web and Scan Proxy), the local-only-file report (names and present/missing only, never contents), `--copy-env` copying a missing `web/.env.local` and never overwriting, and `run()` with a fake runner stopping at the first failure. No install runs in the test; the real fresh-worktree run is recorded on the ticket. |
| `test_ticket_start.py` | Function + interaction | New 2026-10-10 (#87). `../scripts/ticket_start.py` behind `/ticket-start` (`docs/agents/ticket-skills.md`): blocker, assignee, closed-ticket, existing-branch and Android-emulator stops that change nothing; the claim only after every check; and, with a real `git` in a throwaway repo, that the worktree is cut from `MPSkills` and not the checked-out branch. `gh` and the setup script are fakes. |
| `test_android_suite_loop.py` | Function + interaction | New 2026-10-19 (#127). `../scripts/android_suite_loop.py`, the repeat-run command for the Android instrumented suite (`android/TESTING.md`): how a finished run is labelled (pass, real test failure, infrastructure abort; an abort marker beats a test failure that was a symptom of it; Gradle output read by the same rules), that the emulator is restarted before every run and after any abort, the counts, streak and exit code, the readiness check (booted and every service answering, several polls in a row), the software-GPU emulator command, and that the `am instrument` run excludes the weekly class and every `@ExternalSurface` class, found as the External runner finds them (#153). No emulator, adb or Gradle is touched; the real runs (5 of 5 passing) are recorded in `android/TESTING.md` and on the ticket. |
| `test_pin_weight_wording.py` | Function | New (#48). Scans the shipped source of Core, Streamlit, Web and Android and fails on any "tongue" in it, so the fifth-wheel hitch load stays "pin weight" everywhere, including strings the golden-vector fixture does not pin (the Android truck-entry hint). |
| `test_test_planner_since_verified.py` | Function | New 2026-10-19 (#66). The planner's three later rules, with a small fake context map, a fake ledger (context to last verified commit) and a fake `git diff` (ref to changed files): `--since-verified` plans each context from its own verified commit (committed but unverified work is planned, work verified since is not, a context never verified or whose commit git cannot read is planned from `--base`, the ledger is asked for the planned level, a commit written by the real ledger's `record` is the one diffed from); a change to an interface's provider side queues the sharing contexts (the interface's own named test where the config gives one, else their Major suite; at session end their context run) while a consumer-side change queues no one; `depends_on` queues a dependent, transitively, narrowed to the files it imports when given globs; docs-only changes (`docs_globs`) plan nothing and do not count toward the diff's size. Five real-config checks pin the shipped config (docs-only plans nothing; scan-proxy HTTP queues Android; Core queues Streamlit but `scripts/` does not; every `depends_on` names a declared context). A sixth, that the API contract no longer queues Web, went with the `api-contract` interface (#135). Seven mutations of the planner (no downstream, docs unfiltered, ledger ignored, debt ignored, provider check dropped, globs ignored, downstream beside an application run) each fail it. |
| `test_verification_debt.py` | Function | New 2026-10-20 (#67). `../scripts/verification_debt.py`, the session-start verification debt report (`--hook` prints the JSON a Claude Code SessionStart hook expects; setup in `../docs/agents/verification-debt.md`). A small fake context map, a fake `git diff` (ref to changed files) and a fake ledger (context to last verified commit and time) drive it: each context is measured from its own verified commit, files that reach a context from another (interface or `depends_on`) are shown under where they live, docs-only files add nothing, a suite the ledger shows as passed is left out of the tests owed, a context with no recorded pass gets one bootstrap line with its exact ledger command (never counted or nudged, gone once recorded, and "none" is not claimed when nothing has a record); a recorded commit git can no longer read (a rebase) or an unreadable ledger is not reported as never verified (a note, no bootstrap line, since its command would fail to record). The context-level recommendation fires at the size limit (`>=`) or the age limit with changes pending, uses the context's whole session command wrapped in `verification_ledger.py run`, ignores an unreadable timestamp, and a limit of 0 switches it off; the limits come from the `debt` section of the planner config and a command-line value overrides them. It never blocks or runs tests: a git failure, an unreadable ledger, a broken suite lookup, a bad or unknown argument all exit 0 with a line in the report, `subprocess.run` and `Popen` are forbidden while it builds, and the ledger file is byte-identical afterward. One test reads a ledger written by the real `record` so the age uses the ledger's own timestamp format; three read the setup document (its SessionStart snippet is valid JSON that calls the script with `--hook`; it lists every context's exact bootstrap command; it names the config keys). Four mutations (size limit off by one, no-record contexts counted, passed suites still owed, errors re-raised) each fail it. |
| `test_ticket_finish.py` | Function + interaction | New 2026-10-10 (#87). `../scripts/ticket_finish.py` behind `/ticket-finish`: `READY TO MERGE` refused on a dirty tree, a failed or missing suite, or a criterion with no test; the comment follows `docs/agents/session-handoff.md`; preflight and `post()` against a real throwaway repo with a fake `gh`. Extended 2026-10-19 (#128): `suites` runs the session-level plan once per tree against the real ledger in `tmp_path` and a fake runner (second run and an amend run nothing; a failure is not recorded; after a review fix only suites whose files changed run, the rest are carried forward; an unreadable ledger runs everything unrecorded), and `post` refuses a suite reported as skipped that the ledger does not show as passed. Extended (#150), against the real config: the static-check commands are run and recorded against the tree like any suite, skipped on the second run, not recorded when one fails, and rerun after any later change. |
| `test_ticket_merge.py` | Function + interaction | New 2026-10-10 (#87). `../scripts/ticket_merge.py` behind `/ticket-merge`: preflight (main checkout, clean `MPSkills`, newest `STATUS:` is READY TO MERGE), a `--no-ff` merge commit with conflict abort, and `close` (comment, issue closed, worktree and branch removed; a worktree with modified or untracked files is listed by name and left untouched, #93). A fake `gh` that fails on any `git push` proves nothing pushes. Extended 2026-10-19 (#128): `verdicts` gives each suite finish ran on the branch tip a `skip` and any suite without a recorded pass (a failed run, a later commit, an unreadable ledger) a `rerun`, from the main checkout against a worktree finish ran in. Extended (#150): the static-check commands show as `skip` when finish recorded them and `rerun` when the one that failed has no pass. |
| `test_ticket_skills.py` | Structure | New 2026-10-10 (#87). The three `.claude/skills/ticket-*/SKILL.md` files: user-invoked only, 80 lines or fewer, naming scripts and docs that exist, not gitignored (while other local skill payloads stay ignored). Extended 2026-10-19 (#128): the finish skill says session level only and runs `ticket_finish.py suites`; the merge skill's step 2 uses `verdicts` and keeps the diff read, criterion trace and mutation check. |
| `test_precommit_hook.py` | Interaction | New 2026-10-10 (#87). `../.githooks/pre-commit` with a fake `uv` on PATH: it regenerates and stages `dashboard.svg` on a normal branch and leaves it alone on `ticket-*` branches (`docs/agents/session-handoff.md`). |
| `test_external_gate.py` | Function + interaction | New 2026-10-19 (#43). `../scripts/external_gate.py`, the ADR-0008 release gate, from fake manifest, status and registry data: blocks on a stale, failed, only-skipped or never-run surface in the chain (Android's includes the Worker's) and on an unreachable registry, planned surfaces never block, `--force` needs a reason and records the surfaces that were blocking. Which pushes are gated: only `MPSkills` pushes touching `web/`, `workers/scan-proxy/` or `android/`, a docs-only push does not even reach a registry. The pushed diff is read from a real throwaway repo (new branch, unknown remote commit, a file moved out of a gated directory). |
| `test_prepush_hook.py` | Interaction | New 2026-10-19 (#43). `../.githooks/pre-push` run by a real `git push` to a bare repo with a fake `uv`: the pushed refs reach the gate on stdin, its exit code lets the push through or stops it, and `--no-verify` skips the hook. |
| `test_scan_outcomes_docs.py` | Function | New 2026-10-19 (#115). The "Scan outcomes" glossary table in `../workers/scan-proxy/CONTEXT.md` has a row for every case in `../test-vectors/scan_outcomes.json` and agrees with it on spent, refunded, request id and Try again; the Web and Android `CONTEXT.md` files and `CONTEXT-MAP.md` point at it; the Worker README says `billing_error` may or may not have charged and lists `extraction_failed_no_refund`. The fixture itself is tested by the two clients (`web/src/scanOutcomes.test.ts`, `ScanOutcomesFixtureTest.kt`). |
| `test_scan_proxy_deploy.py` | Function | New 2026-10-19 (#43). `../scripts/scan_proxy_deploy.py` behind `npm run deploy`: wrangler runs only after the gate passes, `--force --reason` (or the exported reason of a forced release run) goes through, other arguments reach `wrangler deploy`. Fake gate and runner, no deploy. |
| `test_wizard_web_revenuecat.py` | Interaction | New 2026-10-11 (#86). `../scripts/wizard_web_revenuecat.sh` run with scripted stdin in a scratch directory: a pasted `sk_` secret key is read silently (a `read` wrapper logs `-s`, since a pipe never echoes), never printed or saved, and the public key that follows is saved. |
| `test_web_glossary.py` | Structure | New 2026-10-11 (#86). `../web/CONTEXT.md`'s **Pro** entry has an `_Avoid_` line and points at the reserved **Entitlement** term in `workers/scan-proxy/CONTEXT.md` instead of defining Pro as an entitlement. |
| `test_record_external_result.py` | Function | New 2026-08-24 (roadmap item #7). `../scripts/record_external_result.py`'s `record()` — writes a new entry, maps a nonzero exit code to `passed: false`, preserves other platforms'/suites' existing entries untouched, and overwrites a stale entry for the same platform+suite. Uses `monkeypatch` on the module's `STATUS_FILE` constant rather than touching the real `scripts/dashboard_data/external_status.json`. |
| `test_testing_docs.py` | Structure | New (#64). The five testing documents (root, this one, Web, Scan Proxy, Android): every test file of a context is named in its document, each document links to `docs/test-audit/rules.md` and to `scripts/test_planner.py` and every relative link resolves, every `scripts/` file a document names exists and every `npm run` script Web's and Scan Proxy's documents run is in that package's `package.json`, the root document has the per-issue, session-end and release levels with the planner's three `--level` forms, every entry under "Known gaps" starts with a status and an open one names its ticket or says there is none, a gap the code has since closed (Scan Proxy's timeout and spend-throws) is not worded as open, and a test file named as existing does exist unless the text says it is retired. Counts are not asserted: they change with every ticket, so the real figures come from a real run when the documents are refreshed. |
| `test_external_freshness.py` | Function | `../scripts/external_freshness.py`, ADR-0008's freshness check, with git history, the status file and every registry response faked: a surface is stale when a commit since its last real pass touched a boundary file or pin, or a watched package published a stable release after it, or a registry is unreachable; the npm, PyPI, Maven Central and Google Maven fetchers (the Maven ones added in #54), the `owner` rules (#142: a surface with no owner, an owner outside its platforms or a list of owners is a manifest problem that exits 1), the planned, failed, skipped and overridden states, and checks of the real manifest (every provider surface registered, every entry well formed, each surface's chain, the Worker's and Python's Claude surfaces sharing no file, pin or package). Its live counterpart is `test_maven_registries_external.py`. |
| `test_maven_registries_external.py` | **External** (free) | New (#54). The Maven fetchers against the real registries (plain GETs, no key, about 10 s), so a registry that stops telling the truth fails here instead of silently marking a surface fresh. Marked `external` and deliberately not `core`, so a default run and `-m core` never reach the network; run with `uv run pytest -m external tests/test_maven_registries_external.py`. A registry that cannot be reached fails, never skips. |
| `test_external_wrapper.py` | Function | `../scripts/external_wrapper.py`, the decision logic behind every platform's `test-external` wrapper, with the runner and recorder faked: which stale surfaces run, the owner rule (a stale surface another platform owns is printed with its script and never run or recorded), a surface with no tagged test recorded `fail`, `-Skip` recorded `skipped`, the paid-call confirmation and budget (`scripts/paid_call_budget.py`), and the per-surface results taken from the tagged tests rather than the exit code (#89). |
| `test_external_surface_results.py` | Interaction | New (#89). The pytest half of the per-surface result: `run_external_pytest.py` selects each surface's marker, loads `external_surface_plugin.py` and writes JUnit XML that `external_wrapper.surface_results` attributes per surface. Runs a throwaway pytest in a temp directory; no live call. |
| `test_live_provider_guard.py` | Function | New (#50). The `external` marker is the only way a test may reach a live provider: an unmarked test that reaches the real `anthropic.Anthropic` client fails (`tests/conftest.py`), the live vision file is marked `external`, a default run's `addopts` excludes `external`, and every test file that reads the real API key to decide whether to run is marked `external` too. |
| `test_pass_pool.py` | Function | New (item #13). `../scripts/pass_pool.py`: a doc type resolves to one of its registered real images with that image's own `golden_fields.json` entry attached (the pool is a membership index over `photos`, not a second copy of the field data). A fixed seed keeps the assertions deterministic. |
| `test_pass_pool_regression.py` | Function, real-photo (`slow`) | New (item #13). A random real photo per doc type from the pass pool, picked at run time with an unseeded `random.Random()`, through real Tesseract: the mismatched fields must equal the documented `known_ocr_limitations`, so a new mismatch is a regression and a limitation that starts matching is an improvement to record. Owed by the planner when the OCR modules, the pool scripts or `ExampleDocs/` change. |
| `test_fail_pool_regression.py` | Function, real-photo (`slow`) | New (item #13). A random known-illegible real photo per doc type through real Tesseract: extraction still gives the documented `None` failure signature, and that signature still reaches "Not Enough Information" through `compute_breakdown`/`verdict_for`, so garbled OCR is never taken as real data. Self-contained in `golden_fields.json`'s `fail_pool` section. |
| `test_vehicle_discovery.py` | Function | New (item #13). `../scripts/vehicle_discovery.py`, the directory-convention discovery behind the pools ("drop images and a `vehicle.json` in a folder and the tests pick them up"): builds a fake `scans/` tree under `tmp_path` per case and proves the discovery mechanics, not the real photos (the two regression files above do that). |
| `test_breakdown_combinatorial_sweep.py` | Function, invariant sweep (`slow`) | `itertools.product` over a small chosen set of truck, trailer, scale, axle-count and pin-weight-percentage values: `compute_breakdown`/`verdict_for` never crash, every tone and status is a real member of its set, `estimated` never leaks onto an insufficient row and `pct` stays in range. Asserts invariants, not values; a bug it finds is promoted to a named case in `test-vectors/breakdown_cases.json`. Owed when `breakdown.py` changes. |
| `test_review_form_rebuild.py` | Function | New (item #8). `review_form.py`'s field discovery and reconstruction (`_leaf_fields`, `_rebuild_from_values`), extracted from the window's closures so no Tkinter window is needed, like `test_review_form_coerce.py`. The widget wiring stays untested glue. |
| `test_paid_call_budget.py` | Function | `../scripts/paid_call_budget.py`, the shared paid-call confirmation and counter (#62): a confirmed step runs and is counted, a declined one is not, spend accumulates across steps, a step that would exceed the maximum or the remaining budget aborts without prompting (exactly the remaining budget is allowed), a zero-call step still confirms, and the default prompt reads stdin and treats anything but `y` or `yes` as no. |
| `test_grant_tester.py` | Interaction | New 2026-10-27 (#180). `../scripts/grant_tester.py`, the beta grant tool (`docs/BUILD_AND_DEPLOY.md`, "Granting a tester"), against a fake RevenueCat server on localhost that applies a deposit once per `Idempotency-Key`: `--apply` sends the Pro `grant_entitlement` and the 20 (or chosen) `SCAN` deposit to the right project and customer; no `--apply` sends nothing and prints the plan; a missing/blank key, a malformed account id or an out-of-range option stops before any request; a second run for the same grant leaves the balance at 20, a new grant id or another tester deposits again; a 409 on Pro still lets the scans go, a 403 stops before the deposit and names the permission; the fake key (including one echoed back inside an error body, or an unreachable server) never reaches stdout or stderr; the project id and currency come from the Worker's `wrangler.toml`. The tool is never run live from a session. |
| `test_release_steps.py` | Function | `../scripts/release_steps.py`'s `run_paid_step` (#62, #63), shared by both release commands: a confirmed passing step runs, a declined one does not run, a step over the budget aborts with exit 1, a confirmed failing step returns its own exit code. |
| `test_scan_proxy_release.py` | Function | `../scripts/scan_proxy_release.py` behind `workers\scan-proxy\release.ps1` (#62), with a fake runner (no deploy, no test run, no network): the offline suite, then the stale surfaces, then the gate, then the release and weekly suites, in that order; a blocked gate stops the run before the weekly suite deploys; `-Force` needs a reason and passes it to every step; a failing offline suite stops before anything paid; a declined paid step is skipped and the next one still runs; exceeding the declared maximum aborts; the default maximum is the release suite's one call plus the weekly suite's two. |
| `test_android_release.py` | Function | `../scripts/android_release.py` behind `android\release.ps1` (#63), with a fake runner and a fake device list (no device, deploy or network): JVM suite, instrumented suite, the Worker's wrapper then Android's own for the stale surfaces, the gate over Android's chain, then the weekly suite, in order; a missing device (or an `adb` that cannot be found) fails the run, never skips it; unauthorized and offline devices are not counted; a blocked gate, a failing wrapper or a failing instrumented suite stops the run; a declined weekly suite is skipped; the default maximum matches the weekly step's declared cost. |
| `test_android_session_end.py` | Function | `../scripts/android_session_end.py`, the device-free session-end command (#133): JVM tests, then the decision-logic coverage floor, then (#150) the instrumented-test compile, then detekt; it stops at the first failing step with that step's exit code and name, says so when everything passes, and no step needs a device; detekt's source set includes `src/androidTest` (set in `android/build.gradle.kts`). Fake runner. |
| `test_static_checks.py` | Function | New (#150). `../scripts/static_checks.py`, each context's static-check command: which steps each context runs and in what order, every step runs after a failure and the first failure's code is returned, `--coverage` only for the Python contexts and passed to `coverage_gate.py --only python --refresh`, ruff run with `uv run ruff` and pinned exactly in `pyproject.toml` and `uv.lock`, each Node context running its own oxlint (a locked devDependency of Web and of Scan Proxy, with a `lint` script, #160), the missing-binary message naming that context's own install, oxlint warnings judged against the allow-list (an error fails, a new warning fails, one more than listed fails, a stale entry fails), and the shape of `scripts/static_allowlists/oxlint.json` (a reason and a positive count on every entry, no duplicates, the files exist). Fake runners. |
| `test_static_checks_real.py` | Command check (part `slow`) | New (#150). The allow-lists against the real tree: every name in `vulture_whitelist.py` and `vulture_whitelist_tests.py` must still be reported by vulture run without it (fast), and `scripts/static_allowlists/oxlint.json` must match what oxlint reports for Web and for Scan Proxy exactly (the two that start Node are `slow`, in the planner's `tooling` group). |
| `test_run_external_android.py` | Function | `../scripts/run_external_android.py`, the Android External runner `external_wrapper.py` calls (#39), with a fake command runner for Gradle, `adb` and the sign-in helper (the instrumentation output is the shape the `medium_phone` emulator printed): the device checks (exactly one device, Google Play Services present), the access token never reaching the device or the output, a failed build, install or sign-in failing the run before any test, the marker file removed even when the run is interrupted, the raw `-r` output turned into JUnit XML with each test's surface, and checks that every `@ExternalSurface` class is an active Android-owned surface in the manifest and is kept out of the Gradle default run. No device, build or network. |

## Known gaps

Each entry says whether it is closed or still open, and an open one names the ticket
that tracks it or says there is none (`tests/test_testing_docs.py` checks this). Refreshed 2026-10-21 (#64)
against the test audit in `docs/test-audit/` (core, streamlit).

- **Open (#140)**: Streamlit's `FIELDS` names are checked against the Tesseract
  parsers' keys (`test_ocr_output_key_contracts.py`) but not against the Claude
  vision extractors' schemas, so a `FIELDS` name that is not a key there would
  silently never be pre-filled on the Claude path.
- **Open (no ticket yet; the audit's suggestion)**: `streamlit_app/requirements.txt`
  (what Streamlit Community Cloud installs) is not checked against `pyproject.toml`
  or the imports `app.py` and Core need. It has already drifted once and caused a
  production import bug (`test_optional_anthropic_import.py` is the regression test
  for that one, not a check of the file).
- **Open (no ticket)**: `review_form.py`'s window wiring, the interactive
  `read_*_ocr()` entry points and `file_picker.py`'s dialog calls are untested glue
  (46%, 64%, 72% and 85% statement coverage under "Coverage" above). A deliberate
  gap, the same class this project accepts for shell-out I/O elsewhere.
- ✅ **Closed (#55)**: the golden-vector fixture has an over-limit case
  for every Breakdown row (18 cases), asserts each row's note and badge and the
  verdict's headline and subline, and every runner fails a case that needs a
  capability it does not know.
- ✅ **Closed 2026-10-04 (#56)**: the Streamlit Disclaimer gate is asserted to hide
  Results until acknowledged (`test_results_is_hidden_until_the_disclaimer_is_acknowledged`),
  and `streamlit_app/app.py` went from 81% to 99%.
- ✅ **Closed (#50)**: a default run, the coverage gate and the dashboard
  never reach a billed Claude call, whatever `ANTHROPIC_API_KEY` is set to;
  Minor, slow, Core and Streamlit are selectable by marker.
- **Obsolete (#135)**: the `estimated`-field-in-the-`/api/breakdown`-response
  check and the OCR-keys-vs-`schemas.py` check guarded the FastAPI app,
  which was removed. `estimated` is now asserted on every row by the
  golden-vector runners in Python, Kotlin and TypeScript.
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
