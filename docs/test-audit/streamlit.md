# Test audit: Streamlit (`streamlit_app/`)

Audited 2026-10-04 at commit `354c3d9` on `MPSkills`, against `docs/test-audit/rules.md`. Read-only: nothing in the product was changed; this file is the only write. Measured facts are marked **[measured]**; everything else is reading or judgement.

## 1. Summary

1. Worst gap: no test checks that Results is actually hidden until the Disclaimer is acknowledged, or what the Disclaimer says. The gate is only clicked through (`tests/test_streamlit_app.py:74`, `:209`).
2. Only one file (`tests/test_streamlit_app.py`, 8 tests) drives the Streamlit app, via `AppTest`. Everything else that exercises it is Core OCR and breakdown code that the app imports. Measured `streamlit_app/` coverage is 81% (`app.py` 81%, `fields.py` 100%, `recent_rigs.py` 79%).
3. Untested app paths: choosing a recent rig, "Start Another Check", the Tesseract-no-text and no-match warnings, OCR-failure error branches, the estimated-model skip button, the "pass" verdict, and the estimated-figures notice.
4. Session-end run is one command, `uv run pytest -q`, but on this machine it makes real billed Claude calls (an `ANTHROPIC_API_KEY` is set here; checked, value not printed) unless the key is unset or `tests/test_claude_vision_external.py` is excluded. There is no file, context or marker-based command for Streamlit.
5. `streamlit_app/requirements.txt` (what the host installs) can drift from `pyproject.toml` with nothing checking it; this already caused a production import bug (see `tests/test_optional_anthropic_import.py`).

## 2. Inventory

All tests live in the single repo-wide `tests/` directory; there is no per-context split, no markers and no CI. The 3 External tests and the 649 other collected tests are one `pytest` collection. **[measured]**: `uv run pytest -q --ignore=tests/test_claude_vision_external.py` with `ANTHROPIC_API_KEY` and `HDTTOOLS_OCR_BACKEND` unset gave 645 passed, 4 xfailed in 33.5 s (35 s wall). `tests/TESTING.md:13` still says "156 tests (153 passing, 3 xfail)", which is stale (see section 6).

### 2a. Streamlit tests (cover `streamlit_app/` directly)

| Cat | File | Tests | What it drives |
|---|---|---|---|
| 2 interaction (real Tesseract, real photos) | `tests/test_streamlit_app.py:64,80,101,133` | 4 functions, 5 cases (the walkthrough at `:133` is parametrized over `golden_fields.json` "rigs"; only one rig exists, `addie_and_goose`) | Skip-all to Results; skip notice; real standalone-ticket scan fills the weight; full real-photo walkthrough to a real verdict |
| 2 interaction (mocked extractor) | `tests/test_streamlit_app.py:229,254,280,307` | 4 | `HDTTOOLS_OCR_BACKEND=claude` dispatch per module and the no-Tesseract-warning regression. Mocked, no network |

File total is 8 collected tests; the real-photo ones need Tesseract. **[measured]**: this file alone runs in 12.6 s (about 14 s wall); the walkthrough is the slowest at about 5.9 s.

Command: `uv run pytest -q tests/test_streamlit_app.py`.
Needs: Tesseract binary (found here via `_TESSERACT_CANDIDATES` at `src/hdttools/ocr_common.py:21`, not on `PATH`), the 4 `ExampleDocs/*.jpg` photos plus `ExampleDocs/golden_fields.json`. No network, no secret. Writes to `~/.rigcheck/recent_rigs.json` are redirected to `tmp_path` by an autouse fixture (`:47-53`), so the real file is untouched.

No Streamlit file is a category 1 (function), 3 (module) or 5 (external) test. The helper modules `fields.py` and `recent_rigs.py` have no direct tests: `fields.py` is covered only through the app and through `tests/test_ocr_output_key_contracts.py` (category 4, below); `recent_rigs.save_recent_rig`/`load_recent_rigs` are only reached through the Results step and have no tests of their own (corrupt JSON, 5-rig cap, case-insensitive nickname replacement are all untested; lines 26-30 uncovered).

### 2b. Tests that straddle Streamlit and Core

| Cat | File | Tests | Why it straddles |
|---|---|---|---|
| 4 inter-module | `tests/test_ocr_output_key_contracts.py` | 10 | One direction checks OCR `_parse_fields()` keys against `schemas.py` (Core to API); the other checks that every `streamlit_app/fields.py` `FIELDS` name maps to a real OCR key (Core to Streamlit). Streamlit's half is the `keep`-filter direction |
| 2/1 Core, imported by app | `tests/test_ocr_common.py` | 4 | `get_ocr_backend()` default/explicit/invalid; the app calls it at `app.py:138,187` |
| 3 module, real subprocess | `tests/test_optional_tkinter_import.py`, `tests/test_optional_anthropic_import.py` | 1 each | Exist because Streamlit Community Cloud lacks tkinter and (via a stale `requirements.txt`) `anthropic`; the tests guard Core import behaviour for the Streamlit host |
| real-photo, pool | `tests/test_pass_pool_regression.py`, `tests/test_fail_pool_regression.py` | 4, 2 | Real Tesseract over randomly picked pool images; fail pool also reaches a "Not Enough Information" verdict via Core `compute_breakdown`, not through the app. Core-owned; random pick makes them non-deterministic run to run |

### 2c. Core tests that the Streamlit app relies on (for a Core audit agent, listed only for separation)

Core only, not Streamlit: `test_breakdown.py` (20), `test_breakdown_combinatorial_sweep.py` (378), `test_breakdown_golden_vectors.py` (14), `test_scale_ticket_ocr_parsing.py` (6), `test_truck_tag_ocr_parsing.py` (4), `test_trailer_tag_ocr_parsing.py` (3), `test_real_photo_ocr_accuracy.py` (20, includes 4 strict xfails), `test_scale_ticket_real_photo.py` (2), `test_readers_integration.py` (9), `test_vision_client.py` (2), `test_models.py` (4), `test_database.py` (5), `test_file_picker.py` (4), `test_review_form_coerce.py` (10), `test_review_form_rebuild.py` (7), `test_api.py` (17; the FastAPI app is not part of Streamlit). Tooling tests (`test_coverage_*`, `test_dashboard_lib`, `test_record_external_result`, `test_external_*`, `test_pass_pool`, `test_vehicle_discovery`) are repo scripts, not product.

### 2d. External / live tests (not run)

`tests/test_claude_vision_external.py` (3 tests, one per doc type): real Claude vision call each, `skipif(not os.getenv("ANTHROPIC_API_KEY"))` at line 61. Not run. It needs a real key and makes billed calls (the file's own docstring puts a call at about $0.01-0.03). It exercises Core's `extract_*_fields` plus `vision_client`, not Streamlit code; Streamlit is Tesseract-only per ADR-0002, and its Claude branch (`app.py:146-149`) is a manual dev-time option. It belongs to the Anthropic surface (Web/Android/Worker side), not to Streamlit. It is not tagged with a surface, and ADR-0008's per-surface wrapper has no Python/pytest marker yet. **Hazard [measured]**: because the key is set ambiently here, a bare `uv run pytest -q` runs it and spends money (`tests/TESTING.md:36-43` already warns of this). I excluded it by `--ignore` and unset the key for every run in this audit.

## 3. Code coverage

**[measured]** `uv run pytest -q --ignore=tests/test_claude_vision_external.py --cov --cov-report=term-missing` (key unset; `[tool.coverage.run] source = ["src/hdttools", "streamlit_app"]` in `pyproject.toml`). Whole repo 85% (991 statements, 151 missed). Streamlit scope:

| File | Stmts | Miss | Cover | Missed lines |
|---|---|---|---|---|
| `streamlit_app/app.py` | 229 | 44 | 81% | 119-132, 157-170, 192, 198, 248-250, 255-256, 258, 309-311, 324-326, 364, 371, 395-396 |
| `streamlit_app/fields.py` | 3 | 0 | 100% | none |
| `streamlit_app/recent_rigs.py` | 24 | 5 | 79% | 26-30 |
| Streamlit total | 256 | 49 | 81% | |

Running only `tests/test_streamlit_app.py` with `--cov=streamlit_app` gives the identical 81% (49 missed), so every line the whole suite covers in `streamlit_app/` is covered by this one file.

Uncovered lines of consequence, mapped to behaviour:
- `app.py:119-132` is `_reset_wizard`, and `:395-396` the "Start Another Check" button (no test restarts a check).
- `app.py:157-170` is the whole recent-rig chooser (the shortcut straight to the scale ticket step); `recent_rigs.py:26-30` is `save_recent_rig`'s lower half and nickname handling.
- `app.py:192` and `:198` are the "Tesseract returned no text" and "none of it matched" warnings. Only their absence is asserted (`:88`, `:307`).
- `app.py:248-250, 255-256, 258` and `:309-311` are the OCR-failure and no-weight-found error paths for both upload widgets.
- `app.py:324-326` is the "Build Estimated Model / No CAT scale info" button.
- `app.py:364` is the "pass" verdict banner; only fail and insufficient are reached. `:371` is `PREDICTIVE_ESTIMATE_NOTICE`, never rendered in any test.

Context from other Core files (same run): `review_form.py` 46%, `truck_tag_ocr.py` 72%, `trailer_tag_ocr.py` 64% (mostly the interactive `read_*` CLI paths, not used by Streamlit). Branch coverage was not measured.

## 4. Feature coverage

Features from `streamlit_app/CONTEXT.md`, `CONTEXT-MAP.md`, ADR-0002 and `app.py`. There is no requirement list for Streamlit beyond these, so rows are derived from the code.

| Feature | Verifying test |
|---|---|
| Tesseract-only default OCR (ADR-0002: backend defaults to `"tesseract"`) | `tests/test_ocr_common.py` (default, explicit, invalid value); the real-photo AppTest tests run with it implicit |
| Claude backend opt-in only, never a deployment config | Dispatch only: `test_streamlit_app.py:229-307` (mocked). Nothing asserts the shipped Streamlit config cannot select it |
| Rig step: start new rig by nickname | `_start_test_rig` helper used by every AppTest test |
| Rig step: choose a recent rig (skip to scale ticket) | none (`app.py:157-170`) |
| Recent rigs persist, cap 5, case-insensitive replace | none directly; save is exercised at Results, load/corrupt-file and cap are not |
| Photo upload, extraction, review form | `test_streamlit_app.py:133` (real); `:229-280` (mocked) |
| Skip image / enter manually (truck, trailer, scale) | `:64`, `:80`. The separate "Build Estimated Model" button: none |
| Skipped fields stay blank (not 0.0) | `:64` (regression, the ZeroDivisionError case) |
| Standalone tow-vehicle ticket sets stand-alone weight, widget stays in sync | `:101`, `:133` |
| Pin-weight % fallback slider (15-25, default 20) | none (slider value not set or asserted anywhere) |
| Standalone ticket error handling | none (`app.py:248-258`) |
| Disclaimer gate before Results | Click-through only at `:74`, `:209`. Nothing asserts Results hidden before acknowledgement, the wording, or that the acknowledgement is session-scoped. Verdict: **none for the gate itself** |
| Results: verdict banner + breakdown rows | fail and insufficient (`:77`, `:216-219`); pass: none |
| Predictive-estimate notice for estimated rows | none (`app.py:371`) |
| Session history in sidebar | none (the sidebar is never asserted) |
| Start Another Check / reset | none |
| Tesseract-missing or empty-text user warnings | only their absence |
| Free demo: no accounts, credits, paywall, no network boundary | No test (absence of a feature; the closest guard is that the live External test is Core-side) |
| Importable without tkinter / anthropic (Streamlit Cloud) | `test_optional_tkinter_import.py`, `test_optional_anthropic_import.py` |
| Dependency set for the host matches `pyproject.toml` | none (`streamlit_app/requirements.txt`, `streamlit_app/packages.txt` unchecked) |

## 5. Interface coverage

### Our interfaces
| Interface | Test |
|---|---|
| OCR `_parse_fields()` keys vs `fields.py` `FIELDS` (Core to Streamlit `keep` filter) | `tests/test_ocr_output_key_contracts.py` (Streamlit direction) |
| `extract_*_fields(bytes, media_type)` call from `app.py:147` | Mocked in `test_streamlit_app.py:229-307`; Core side in `test_readers_integration.py` |
| `compute_breakdown`/`verdict_for` shape consumed by Results | `test_streamlit_app.py` (end to end, one rig); Core `test_breakdown.py`; golden vectors `test_breakdown_golden_vectors.py` (Streamlit does not consume the shared fixtures directly) |
| `st.session_state` keys shared across functions | `test_streamlit_app.py:101,133` |
| `recent_rigs` JSON file format at `~/.rigcheck/recent_rigs.json` | none |
| `HDTTOOLS_OCR_BACKEND` env var | `test_ocr_common.py`, `test_streamlit_app.py:229+` |
| Disclaimer wording parity with Web/Android (CONTEXT-MAP says independent) | none, by design |

### Their interfaces
| Third-party | How Streamlit uses it | Test | Watched in `scripts/external_manifest/`? |
|---|---|---|---|
| Streamlit (`streamlit`, `AppTest`, widget semantics) | the whole UI; two real bugs were widget-state quirks | the AppTest file only; no check against a new release | **No** (the manifest holds only `revenuecat-rest` and `supabase-auth`) |
| Tesseract binary and `pytesseract` | default OCR engine | real-photo tests (Core) catch output changes | **No** |
| Pillow | image open and preprocess | same | **No** |
| Streamlit Community Cloud (host: `requirements.txt`, `packages.txt`, ephemeral disk) | deployment | none, other than the two optional-import regressions | **No** |
| Anthropic API | only via the opt-in `claude` backend | `test_claude_vision_external.py` (live, unrun, not surface-tagged) | **No** (no `anthropic` surface file yet) |

Nothing Streamlit does in its default configuration reaches a paid third-party API.

## 6. Spec check

- **Stale count/claims**: `tests/TESTING.md:13` says 156 tests (153 passing, 3 xfail). **[measured]** 649 collected without the External file, 645 passed + 4 xfailed; plus 3 External tests. The "Coverage" section's baseline (79% total, `app.py` 80%) is also behind the measured 85% total, `app.py` 81%.
- `tests/TESTING.md` says the Python suite has no External-surface wiring; ADR-0008 says External suites carry a surface tag. `test_claude_vision_external.py` has none and cannot be selected by a surface name.
- `tests/TESTING.md:38-43` says an ambient key makes a routine run spend money; that is still true here and is the main hazard to a session-end run.
- ADR-0002 says Claude is "never a real Streamlit deployment configuration", yet the app has a full Claude branch with 4 tests (`test_streamlit_app.py:229-307`). The tests exceed the stated scope; this is consistent with the "manual dev-time comparison" wording but no test or code guard prevents the branch being enabled in a deployment.
- `CONTEXT-MAP.md` says all three platforms implement a Disclaimer gate; Streamlit's test count for it is zero beyond the click-through.
- `tests/TESTING.md` still labels tests Minor/Major as "undifferentiated"; there is no marker to run a Minor subset.
- Test names claim "real verdict" but there is exactly one rig; the parametrization is ready for more but the data is not there.
- The strict-xfail design (`test_real_photo_ocr_accuracy.py`) is consistent with the spec: documented OCR limits are neither hidden nor asserted wrong.

## 7. Rule fit

| Rule | Can Streamlit tests support it today? |
|---|---|
| 1. Scope ladder (file, context, application) | File: yes, `uv run pytest -q tests/test_streamlit_app.py` works. Context: **no command**; Streamlit and Core share `tests/` and there are no markers or per-context directories, so a Streamlit context run must be hand-assembled as `tests/test_streamlit_app.py tests/test_ocr_output_key_contracts.py tests/test_ocr_common.py tests/test_optional_*_import.py` plus the Core OCR files the diff touches. Application: `uv run pytest -q`, but see the hazard below |
| 2. Per issue (targeted test first, then Minor/Major, interface tests) | Targeted: yes, a file or node id works. Minor-alone: **no**, no marker tags function and interaction tests separately from module tests (`tests/TESTING.md:18-27`). The inter-module test for a changed OCR key set exists (`test_ocr_output_key_contracts.py`). A change to `recent_rigs.py` or `fields.py` has no module test to run first |
| 3. Session end (whole file/context/app per ladder) | File and app runs are possible. Blockers: a bare `uv run pytest -q` includes the live External test; ambient `ANTHROPIC_API_KEY` makes it spend; there is no context-level selection; Tesseract must be installed and is only auto-found at the standard Windows/Homebrew/usr-local paths. About 35 s offline, so the cost is acceptable once the External file is excluded |
| 4. Release | Rules say Streamlit has no full-run release. Today a Streamlit Cloud deploy is a git push with no hook (`.github` absent; ADR-0008's pre-push gate is only for `web/`, `workers/scan-proxy/`, `android/`). The only thing near a gate is `scripts/coverage_gate.py` (Python baseline 79%, below the measured 85%, so it would not catch a drop to 80%) |
| 5. Web gate | Not applicable to Streamlit |

Also relevant to rule 6/7: Streamlit's own dependencies (Streamlit, Tesseract, Pillow, pytesseract) are not watched by any surface, so rule 7's "list dependencies not yet watched" applies to all four.

## 8. Incremental complexity (cheapest to most expensive)

1. **Pure helpers and parsing, no Tesseract**: `uv run pytest -q tests/test_ocr_common.py tests/test_ocr_output_key_contracts.py tests/test_optional_tkinter_import.py tests/test_optional_anthropic_import.py`. A few seconds. Needs only the venv.
2. **Streamlit mocked-extractor and skip tests**: `uv run pytest -q tests/test_streamlit_app.py -k "skipping or skipped or claude_backend"`. About 3-5 s (estimated, not timed separately). Needs only the venv; run with `HDTTOOLS_OCR_BACKEND` unset.
3. **Whole Streamlit file with real OCR**: `uv run pytest -q tests/test_streamlit_app.py`. **[measured]** 12.6 s. Needs Tesseract and the `ExampleDocs/` photos.
4. **Streamlit plus Core OCR real-photo files**: `uv run pytest -q tests/test_streamlit_app.py tests/test_real_photo_ocr_accuracy.py tests/test_scale_ticket_real_photo.py tests/test_pass_pool_regression.py tests/test_fail_pool_regression.py`. Roughly 25-30 s (estimated from the slowest-test list). Same needs; pool picks are random.
5. **Whole offline application suite with coverage**: `env -u ANTHROPIC_API_KEY uv run pytest -q --ignore=tests/test_claude_vision_external.py --cov --cov-report=term-missing`. **[measured]** about 35 s. Needs Tesseract; the key must be unset (or the external file excluded) to avoid cost.
6. **Live Claude vision (External, not run in this audit)**: `uv run pytest -q tests/test_claude_vision_external.py` with a real `ANTHROPIC_API_KEY`. 3 billed calls (about $0.03-0.09 by the file's own estimate), a few seconds each, needs network and the owner's confirmation under rule 6. Not a Streamlit test in substance.
7. **Streamlit Cloud smoke check** (manual, no script): deploy and open the demo; costs nothing but human time; no automation exists.

## 9. Gaps and suggested tickets

Suggestions only; no issues created or edited.

1. **Disclaimer gate test (Streamlit)**: assert Results shows no breakdown before acknowledgement, the heading/wording appears, and acknowledgement persists across a rerun. Source: section 4; small.
2. **Safe session-end command**: a documented or scripted whole-suite command that excludes (or deselects by marker) the live External test regardless of ambient `ANTHROPIC_API_KEY`. Source: rules 3, section 7; small.
3. **Marker or per-context selection**: pytest markers (for example `streamlit`, `core`, `external`) or directory split so a context-level and Minor-only run is one command. Source: rules 1-3; medium.
4. **Cover the untested app paths**: recent-rig chooser, Start Another Check, estimated-model skip, pass verdict, estimated-figures notice, error branches (`app.py:119-132, 157-170, 248-258, 309-311, 324-326, 364, 371, 395-396`). Source: section 3; medium.
5. **`recent_rigs.py` tests**: load (missing, corrupt, non-list), save (cap of 5, case-insensitive replace) against `tmp_path`. Source: section 3; small.
6. **Dependency drift test**: check that `streamlit_app/requirements.txt` covers the imports `app.py` and Core need on the host (it already drifted once). Source: section 4; small.
7. **Watch Streamlit's dependencies**: add manifest surfaces (or one `streamlit-app` surface) for Streamlit, pytesseract, Pillow with PyPI as registry; note that Tesseract itself has no registry. Source: rule 7, section 5; small to medium.
8. **Surface-tag the live Anthropic test**: give `test_claude_vision_external.py` a pytest marker and an `anthropic` manifest surface with a call maximum (ADR-0008). Source: rule 6, section 5; medium (shared with other surfaces).
9. **Refresh `tests/TESTING.md`** counts and coverage baseline (156 vs 649+; 79% vs 85%), and re-baseline `coverage_gate.py`'s Python floor. Source: section 6; small.
10. **Second real rig in `golden_fields.json`** (and a rig that reaches a "pass" verdict) to exercise the parametrized walkthrough. Source: sections 3, 6; medium (needs new real photos).
11. **Guard against enabling Claude on the deployed demo**: a test that the committed Streamlit config/entry defaults to Tesseract. Source: section 6 (ADR-0002); small.
12. **Streamlit Cloud deploy check**: decide whether a Streamlit push needs any release gate; rules currently say no full-run release. Source: rule 4; small (decision).
