# Static checks

What checks the code without running it (typecheck, lint, dead code) or measures how much of it the tests reach (coverage floor), per context, and how each context runs them as one command. Spec: #150 (map #49). The scripts are `scripts/static_checks.py` (core, streamlit, web, scan-proxy) and `scripts/android_session_end.py` (Android); the rules that choose when they run are in `scripts/test_planner_config.json` and `scripts/test_planner.py`.

## How they run

Each context has a `session_end` command in `scripts/test_planner_config.json`:

| Context | `session_end` | Runs | Replaces the context's suites? |
|---|---|---|---|
| core | `uv run scripts/static_checks.py core`, or `uv run scripts/static_checks.py core --coverage` when `src/hdttools/` or `scripts/` changed | ruff, vulture on the code, vulture on the tests, Python coverage floor (with `--coverage`) | no, runs beside them |
| streamlit | `uv run scripts/static_checks.py streamlit`, or `uv run scripts/static_checks.py streamlit --coverage` when `streamlit_app/` changed | the same Python steps | no |
| web | `uv run scripts/static_checks.py web` | `tsc -b`, oxlint against the allow-list, knip | no |
| scan-proxy | `uv run scripts/static_checks.py scan-proxy` | `tsc --noEmit`, oxlint against the allow-list, knip, coverage floor (100%) | no |
| android | `uv run scripts/android_session_end.py` | JVM tests, decision-logic coverage floor (95%), instrumented-test compile, detekt | yes (it runs the JVM tests itself) |

- **When.** At session level, `uv run scripts/test_planner.py --level session` lists a context's static command when a file of the context changed, one of its `static_triggers` (config key) changed, or one of its dependency files changed. A docs-only change lists none; the issue level lists none. `/ticket-finish` runs what the ledger cannot vouch for and records each pass against the tree hash (`verification_ledger.py suite`); `ticket_merge.py verdicts` shows `skip` or `rerun` for it like any suite. The planner never carries a static pass across a review fix (the command names no context to carry by), so any change after the pass reruns it.
- **The Python coverage floor** needs the whole suite under coverage.py (about a minute), so it is in the command only when a file of `src/hdttools/`, `streamlit_app/` or `scripts/` changed (Decision 4); a change to `tests/` alone runs ruff and vulture but not the floor.
- **Exit rule.** Every step of a context runs, even after one fails, so one run shows everything wrong; the command exits with the first failing step's code, and 0 only when all pass. Android's command stops at its first failure.
- **Offline.** No step makes a paid call or touches a device. ruff runs through `uv run ruff`: it is a dev dependency, pinned exactly in `pyproject.toml` and locked in `uv.lock`, with the rules in `ruff.toml`.
- **Each Node context lints with its own oxlint.** Web runs `web/node_modules/.bin/oxlint` and Scan Proxy runs `workers/scan-proxy/node_modules/.bin/oxlint`, each a devDependency with a `lint` script (the script is what stops knip reporting it as unused). A Scan Proxy-only checkout needs only `npm --prefix workers/scan-proxy ci`; a missing binary fails the step and names the install command (`scripts/worktree_setup.py` runs both).
- **Dependency files and External surfaces (#160).** Moving ruff and oxlint out of the commands and into `pyproject.toml`, `uv.lock` and `workers/scan-proxy/package.json` marks the surfaces those files pin stale (ADR-0008), so that change was scheduled just before the final External run. Until #160, ruff was pinned in the command and Scan Proxy borrowed Web's oxlint. A Kotlin source root is still added in `android/build.gradle.kts` rather than `android/app/build.gradle.kts` for the same reason.

## Decisions (owner, 2026-10-21)

1. The checks run in each context's `session_end`, listed by the planner when the context's files change.
2. An error fails; a warning fails unless it is in the checked-in allow-list with a reason, and an allow-list entry for a warning that is gone also fails.
3. `ruff` (Python) and `oxlint` (Web and Scan Proxy) were added now; everything else not covered is below with a follow-up.
4. The Python coverage floor runs when `src/hdttools/`, `streamlit_app/` or `scripts/` changed.

## Allow-lists (nothing is silenced without a reason)

| List | Excuses | Checked by |
|---|---|---|
| `scripts/static_allowlists/oxlint.json` | oxlint warnings, per context, file, rule and count, each with a reason (16 in Web, none in Scan Proxy) | the lint step itself, and `tests/test_static_checks_real.py` (slow) |
| `vulture_whitelist.py` | vulture findings in `src/hdttools`, `streamlit_app` and `scripts` that are not dead code, grouped by why vulture cannot see the use | `tests/test_static_checks_real.py`: a name vulture no longer reports fails |
| `vulture_whitelist_tests.py` | the same for `tests/`: pytest hooks, autouse fixtures, fakes' interface names | the same test |

## Inventory

Every source directory and file type each context owns, and which check covers it. `none` in a check column means no check covers it; the last column then names why and the follow-up ticket. Assets that are not source (images, `index.html`, CSS, fonts, `ExampleDocs/`, build output) are not listed.

### core (`src/hdttools/`, `scripts/`, `tests/`)

| Source | Typecheck | Lint | Dead code | Coverage floor | Not covered: reason and follow-up |
|---|---|---|---|---|---|
| `src/hdttools/*.py` | none | ruff | vulture | Python floor | no Python type checker exists yet: #155 |
| `scripts/*.py` | none | ruff | vulture (code pass) | none | no type checker: #155; `scripts/` is outside coverage's `source`: #157 |
| `scripts/*.sh`, `.githooks/*`, root `test-external.ps1` | none | none | none | none | shell scripts have no linter: #156 |
| `scripts/*.json`, `scripts/external_manifest/**/*.json`, `test-vectors/*.json` | none | none | none | none | read by tests but with no schema check: #159 |
| `ruff.toml`, `vulture_whitelist.py`, `vulture_whitelist_tests.py` (root) | none | none (not scanned: bare names are not code) | read by vulture itself | none | config and lists; staleness of the whitelists is tested (`tests/test_static_checks_real.py`), not linted: #159 |
| `tests/*.py` | none | ruff | vulture (tests pass) | n/a (tests are not measured) | no type checker: #155 |

### streamlit (`streamlit_app/`)

| Source | Typecheck | Lint | Dead code | Coverage floor | Not covered: reason and follow-up |
|---|---|---|---|---|---|
| `streamlit_app/*.py` | none | ruff | vulture | Python floor | no type checker: #155 |

### web (`web/`)

| Source | Typecheck | Lint | Dead code | Coverage floor | Not covered: reason and follow-up |
|---|---|---|---|---|---|
| `web/src/**/*.ts`, `*.tsx` (including the `external/` subdirectory) | `tsc -b` | oxlint | knip | none | Web has no coverage floor, only a report: #158 |
| `web/vite.config.ts`, `web/vitest.external.config.ts` | `tsc -b` (`tsconfig.node.json`) | oxlint | knip | none | coverage: #158 |
| `web/scripts/*.mjs` | `tsc -b` (`checkJs`, closed by #150) | oxlint | knip | none | coverage: #158 |
| `web/*.ps1` | none | none | none | none | no PowerShell linter: #156 |
| `web/package.json`, `tsconfig*.json`, `wrangler.toml`, `.oxlintrc.json`, `supabase/migrations/*.sql` | none | none | none | none | config and SQL files with no schema check: #159 |

### scan-proxy (`workers/scan-proxy/`)

| Source | Typecheck | Lint | Dead code | Coverage floor | Not covered: reason and follow-up |
|---|---|---|---|---|---|
| `workers/scan-proxy/src/*.ts` (including the `external/`, `weekly/` and `release/` subdirectories) | `tsc --noEmit` | oxlint | knip | 100% (line) | none |
| `workers/scan-proxy/*.ps1` | none | none | none | none | no PowerShell linter: #156 |
| `workers/scan-proxy/package.json`, `tsconfig.json`, `knip.json`, `wrangler.toml` | none | none | none | none | config files with no schema check: #159 |

### android (`android/`)

| Source | Typecheck | Lint | Dead code | Coverage floor | Not covered: reason and follow-up |
|---|---|---|---|---|---|
| `android/app/src/main/**/*.kt` | Kotlin compile (JVM tests) | detekt (2 rules) | detekt | 95% on decision-logic classes only | UI and wiring have no number, device and External tests verify them; Android Lint is not run: #159 |
| `android/app/src/test/**/*.kt` | Kotlin compile | detekt | detekt | n/a (tests are not measured) | none |
| `android/app/src/androidTest/**/*.kt` | Kotlin compile (instrumented compile step, closed by #150) | detekt (closed by #150) | detekt | n/a (tests are not measured) | none |
| `android/**/*.kts`, `libs.versions.toml`, `gradle.properties`, `detekt.yml`, `coverage-logic.toml`, `AndroidManifest.xml`, `res/**/*.xml` | Gradle reads them | none | none | none | no check beyond the build: #159 |
| `android/*.ps1` | none | none | none | none | no PowerShell linter: #156 |

## What a check cannot see

- vulture reports at 60% confidence and sees names, not meaning, so a whitelist entry for a generic name (`type`, `input`, `create`, `headers`) stays "reported" while any other definition of that name exists; the staleness test cannot tell those apart, so review such entries by hand: a function only its own test calls counts as used, which is why `tests/` is scanned in a separate pass; a name used only by reflection or by pytest needs an allow-list entry with its reason.
- oxlint runs its default rules plus the `react` plugin in Web; it is not a type-aware linter.
- The Scan Proxy floor is line coverage from Node's `--experimental-test-coverage`; branch coverage is printed but not gated.
- The Python floor (79%) is far below what the tree measures (87.78% on 2026-10-21): #157.

## Proving a check can fail

On 2026-10-21 (#150) one deliberate defect per context made its command exit non-zero and was then removed: an unused import and function (core, streamlit: ruff and vulture), a type error in a new file and an unused file (web: `tsc -b` and knip), an uncovered branch (scan-proxy: 99.92% against the 100% floor), and an unused private function (android: detekt, in `src/main` and in `src/androidTest`). The real output is in the closing STATUS comment on #150.
