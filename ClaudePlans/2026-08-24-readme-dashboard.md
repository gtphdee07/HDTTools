# README-embedded test-status dashboard

## Context

Roadmap item #7's remaining bullet (`NEXT_STEPS.md`): a static, checked-in
graphic in `README.md` showing regression/coverage status per product
line (Web, Streamlit, Android, `scan-proxy` as its own 4th line), broken
out by test category with pass-rate color coding (Blue 100%, Green >90%,
Yellow >80%, Red <80%) plus a coverage percentage per line — decided
2026-08-24. It was paused mid-design because its "minor/major/
integration" framing didn't match this repo's real vocabulary; that's now
resolved by item #9 (event-based Minor/Major/External, closed 2026-08-24,
commit `9d148dd`), which also shipped `scripts/coverage_gate.py` with
real, working coverage parsers for all four platforms.

This session's design discussion settled the remaining architecture:
- **Reuse via a shared module, not direct coupling**: extract
  `coverage_gate.py`'s parsers into `scripts/coverage_lib.py`; both the
  release gate and the dashboard import from there. Keeps the two
  scripts' own purposes (enforcement vs. reporting) separate while
  avoiding duplicated/drifting parsing logic.
- **Minor/Major run fresh on every dashboard regen; External reflects its
  last real run instead.** External suites cost real money/time (a real
  Claude call, a booted emulator) — regenerating a README graphic
  shouldn't trigger that. A small persisted status file, updated by the
  External wrapper scripts themselves whenever they're actually run for
  real, backs that column instead.
- **Pass-rate data comes from structured test reports** (JUnit XML,
  Vitest's/Node's built-in reporters), the same "parse the tool's own
  native report format" approach `coverage_gate.py` already uses for
  coverage, not text-scraping stdout.
- **Output is a generated SVG**, pure-Python string templating, no new
  dependency, diffs readably in git, embedded directly in `README.md`.

**Explicitly not in scope**: when Web's `coverage_gate.py` entry flips
from report-only to enforced. That's tied to Web actually gaining a real
release/deployment event (currently deferred — see `NEXT_STEPS.md`'s
"Deliberately not on this list," no date set), not to this dashboard
work. The dashboard just mirrors whatever `coverage_gate.py` already
reports for each platform, so Web's cell will automatically start
showing "enforced" the same day someone flips that one line in
`coverage_gate.py` — no dashboard-side change needed when that happens.

## Goal

A real, regenerable `dashboard.svg` embedded in `README.md`, showing all
four product lines' Minor/Major/External status (color-coded by real pass
rate) and real coverage percentage — backed by actual test-report
parsing, not hardcoded numbers, and reusing `coverage_gate.py`'s parsing
logic rather than duplicating it.

## Steps

1. **Extract `scripts/coverage_lib.py`** from `coverage_gate.py`'s four
   pure parsers (`parse_android_report`, `parse_python_report`,
   `parse_web_report`, `parse_scan_proxy_output`) — pure refactor, no
   behavior change. `coverage_gate.py` imports them instead of defining
   them; its own CLI output must stay byte-identical. Move the matching
   parser tests from `tests/test_coverage_gate.py` into a new
   `tests/test_coverage_lib.py`; `test_coverage_gate.py` keeps just its
   `PlatformResult`/threshold tests.

2. **Wire structured pass/fail reporting for Minor+Major on every
   platform**:
   - Python: add `--junitxml=<path>` to the existing `pytest` invocation.
   - Android: nothing to add — AGP already writes real JUnit XML for both
     `./gradlew test` (`app/build/test-results/testDebugUnitTest/*.xml`,
     confirmed real 2026-08-24) and `connectedDebugAndroidTest`
     (`app/build/outputs/androidTest-results/connected/debug/*.xml`,
     confirmed real 2026-08-24) with zero config — just read them.
   - Web: new `test:report` npm script using Vitest's built-in `junit`
     reporter (`vitest run --reporter=junit --outputFile=<path>`).
   - `scan-proxy`: add `--test-reporter=junit
     --test-reporter-destination=<path>` to both the Minor
     (`[sanity]`-filtered) and Major `node --test` invocations (Node's
     built-in `junit` reporter, confirmed available in this repo's
     Node 24).

3. **`scripts/dashboard_lib.py`** (new) — pure functions, each with a
   `tests/test_dashboard_lib.py` case:
   - Parsers: `parse_junit_xml(path) -> (passed, total)` (shared by
     Python/Android/scan-proxy — all produce standard JUnit XML with
     `tests`/`failures`/`errors` counts at the `<testsuites>` root;
     Android's Minor suite has one XML file per test class, so this
     aggregates a list of paths), `parse_vitest_junit(path) -> (passed,
     total)` if Vitest's junit output shape needs different handling than
     the shared parser (verify against a real run in Step 2 first —
     likely the same parser works for all four).
   - `color_for_percent(pct) -> "blue" | "green" | "yellow" | "red"` —
     the Blue-100/Green->90/Yellow->80/Red-<80 threshold, shared by both
     the pass-rate cells and the coverage cell for visual consistency.
   - `render_dashboard_svg(rows: list[PlatformRow]) -> str` — takes a
     small structured data model (one row per platform: name, Minor/
     Major/External `(color, label)` cells, coverage `(percent, color)`)
     and returns SVG text via string templating.

4. **External "last-known-result" persistence**: new git-tracked
   `scripts/dashboard_data/external_status.json` (one entry per
   platform+suite: `passed`, `timestamp`). New small
   `scripts/record_external_result.py <platform> <suite> <exit-code>`
   helper that updates one entry. Wire it into the *end* of each existing
   External wrapper, before their final `exit`:
   - `android/test-weekly.ps1` — record using `$testExitCode`.
   - `workers/scan-proxy/test-release.ps1` — record using `$LASTEXITCODE`
     after `npm run test:release`.
   - **New** `workers/scan-proxy/test-weekly.ps1` — today the
     through-our-service External suite is only ever run via bare `npm
     run test:weekly` (no wrapper exists), so it has no recording hook.
     Add a thin wrapper mirroring `test-release.ps1`'s exact shape
     (run the npm script, record the result, propagate the exit code) —
     `workers/scan-proxy/TESTING.md`'s documented command changes
     from `npm run test:weekly` to `.\test-weekly.ps1`.

5. **`scripts/generate_dashboard.py`** (new) — the orchestrator, same
   run-or-read `--refresh` shape as `coverage_gate.py`. Per platform: run
   (or read existing reports for) Minor+Major fresh, get pass-rate via
   `dashboard_lib.py` and coverage via `coverage_lib.py`; read External's
   status from `external_status.json`; call `render_dashboard_svg(...)`
   and write `dashboard.svg` at the repo root.

6. **`README.md`**: embed `![RigCheck test status](dashboard.svg)` near
   the top (after the intro paragraph, before "Desktop (Streamlit)"), and
   fix its "Testing" section's stale scan-proxy tier line ("organized
   into tiers (sanity → daily → weekly → release)") to reflect Minor/
   Major/External — a real leftover gap from item #9 that its own file
   list didn't include `README.md`.

7. **Root `TESTING.md`**: short new "Dashboard" section (mirroring the
   existing "Coverage gate" section's shape) documenting
   `scripts/generate_dashboard.py`, `external_status.json`'s role, and
   the new recording hooks on the External wrapper scripts.

## Files

- `scripts/coverage_lib.py` (new, extracted from `coverage_gate.py`),
  `scripts/coverage_gate.py` (import change only)
- `scripts/dashboard_lib.py`, `scripts/generate_dashboard.py`,
  `scripts/record_external_result.py` (new)
- `scripts/dashboard_data/external_status.json` (new, git-tracked)
- `tests/test_coverage_lib.py` (new, moved from `test_coverage_gate.py`),
  `tests/test_dashboard_lib.py` (new)
- `android/test-weekly.ps1`, `workers/scan-proxy/test-release.ps1`
  (append a recording call), `workers/scan-proxy/test-weekly.ps1` (new)
- `pyproject.toml` / `tests/TESTING.md`, `web/package.json` /
  `web/TESTING.md`, `workers/scan-proxy/TESTING.md` (new
  reporter flags/scripts, documented)
- `README.md` (embed the graphic, fix the stale tier reference)
- `TESTING.md` (root) — new "Dashboard" section
- `dashboard.svg` (generated output, git-tracked so it renders on GitHub
  without a build step)
- `NEXT_STEPS.md` — close out item #7's dashboard bullet once verified

## Definition of Done

- `dashboard.svg` exists at the repo root, is embedded in `README.md`,
  and its four rows/cells reflect real current numbers (spot-checked
  against each platform's own last real run).
- `coverage_gate.py`'s output is unchanged after the `coverage_lib.py`
  extraction — pure refactor, verified by re-running it.
- Every new pure function (report parsers, `color_for_percent`, the SVG
  renderer) has a passing test.
- External's dashboard status reflects a real recorded run (not a live
  re-run triggered by dashboard regeneration), and is git-tracked.
- `README.md`'s scan-proxy tier reference matches Minor/Major/External.
- `NEXT_STEPS.md` item #7's dashboard bullet is ✅ with a compact summary.

## Verification

1. `uv run scripts/generate_dashboard.py` end-to-end — confirm a real
   `dashboard.svg` is produced and at least one cell's color is manually
   checked against the real number it represents.
2. `uv run scripts/coverage_gate.py` after the extraction — confirm
   identical output to its pre-refactor run (no regression from moving
   the parsers into `coverage_lib.py`).
3. `uv run pytest tests/test_coverage_lib.py tests/test_dashboard_lib.py
   tests/test_coverage_gate.py -q` — all passing.
4. Manually run one External wrapper (e.g. the new
   `workers/scan-proxy/test-weekly.ps1`) and confirm
   `external_status.json` updates with a real, current timestamp — the
   one piece that can't be verified by `generate_dashboard.py` alone,
   since it depends on a real run happening.
5. Open `dashboard.svg` directly (or preview `README.md`'s rendering) to
   visually confirm the graphic actually reads correctly, not just that
   well-formed SVG XML was produced.
6. Deliberately break one test, regenerate the dashboard, confirm that
   cell's color actually changes to red/yellow — proves the pipeline
   reflects reality rather than being stale/hardcoded — then revert the
   deliberate break and confirm it goes back to green/blue.
