# RigCheck — testing methodology

This defines the test categories and regression-scoping rules used across
the whole repo (Python backend, Web, Streamlit, Android, `scan-proxy`).
Decided 2026-08-20 — see `ARCHIVE_TESTING.md` at the repo root for the
narrative history of how this was arrived at. Platform-specific
files (`android/TESTING.md`, `workers/scan-proxy/TESTING.md`) document
each platform's *actual* current tests against this framework — this file
only defines the framework itself.

## Test categories

Every module (file) is tested at two granularities, plus one category
that exists specifically to catch what those two can't.

### 1. Function unit tests — solitary

One function, its real collaborators replaced with fakes/mocks. For each
function, cover:

- **The interface contract** — given valid inputs, does it accept/reject
  the shapes it's supposed to?
- **Correct operation** — does it do the thing it's for, across the
  meaningfully different cases (not just one happy path)?
- **Expected errors** — do the failure modes it's *supposed* to raise
  actually get raised, and are they the right ones?

Example: `_parse_fields` in `scale_ticket_ocr.py` — `test_parse_fields_on_clean_layout`
(correct operation), `test_parse_fields_returns_none_for_absent_fields`
(interface contract: missing fields come back `None`, not a `KeyError`),
`_find_num`'s miss case (expected-error/no-match handling).

### 2. Interaction tests — sociable, within a module

For functions in the *same* file that share implicit mutable state (not
just parameters and return values) — this is the category unit tests
structurally cannot see, because a solitary test replaces the real
collaborator with a mock and never observes what actually happens between
them. Drive the real sequence of calls in the real order the system
executes them (including reruns/multiple passes, where that's how the
real system behaves), and assert on the net shared-state outcome.

Example, the real bug that motivated this category: Streamlit's
`_render_standalone_ticket_section` and `_render_review` in `app.py` both
read and write `st.session_state` without either function declaring that
as part of its contract. A solitary test of either function in isolation
looked correct; only a test driving the actual sequence — scan, rerun,
re-render — surfaced that the second function's stale widget state
silently clobbered the first function's update. See
`tests/test_streamlit_app.py::test_scanning_a_real_tow_vehicle_only_photo_fills_in_standalone_weight`.

Practical scope-limiter: don't test every function against every other
function in a file. Keep a short, explicit list (even just a comment)
of which functions in a module actually share which piece of mutable
state, and write interaction tests only for the sequences the module's
real control flow produces.

### 3. Module tests — the file's public surface

What the rest of the codebase actually calls into this file for. Same
three checks as function tests, but at the file's exported boundary
rather than one internal function:

- **The interface contract** — the shape callers actually depend on
  (e.g. `compute_breakdown`'s returned list-of-dicts shape, including the
  `estimated`/`tone`/`badgeLabel` keys `main.py` and `app.py` both read).
- **Correct behavior of each offered operation** — `compute_breakdown`
  and `verdict_for` together, as `tests/test_breakdown.py` already does.
- **Expected errors** — does the module fail the way its callers expect
  it to when given bad input, not just silently do the wrong thing?

### 4. Inter-module interface tests

When a change modifies the interface *between* two modules (a function
signature, a return shape, an HTTP request/response contract, a shared
config format), both modules' Major suites run (see below), plus a
dedicated test asserting the contract itself — not just that each side
independently still passes its own tests. Example of the kind of
contract this guards, already caught by an existing test:
`workers/scan-proxy`'s `docTypes.test.ts` asserts its schemas still
contain the exact field names `ScanFieldMapping.kt` on Android reads —
the two modules' own tests couldn't see that field-name coupling on
their own.

**Sequencing, when validating a changed interface spans real, non-mocked
systems** (decided 2026-08-21): run the cheapest, most isolated boundary
first, and only proceed to the more expensive, harder-to-debug layer if
that passes. Concretely: `workers/scan-proxy`'s real interface tests
against RevenueCat/Anthropic (a Node process, precise HTTP-level
failures, `wrangler tail` for logs) before Android's own real-integration
tests (an emulator, Compose rendering, device state, a much larger space
of things that could be wrong). This doesn't make the expensive layer
optional — some real bugs live entirely above what the cheap layer can
see (the RevenueCat SDK's client-side balance-cache bug found 2026-08-18
is a concrete example: no API-contract test, however thorough, would
have caught it). It just means a passing cheap layer meaningfully
narrows where a failure in the expensive layer can be coming from, so
debug there first, escalate second — the same order this project's own
past bug-hunts have already followed in practice (the RevenueCat V1/V2
key issue, the Kotlin golden-vector drift, the scale-ticket real-photo
bug — all found at the cheaper/backend layer before or instead of the
device layer).

### 5. External tests

Verifies a real 3rd-party boundary (RevenueCat, Anthropic) hasn't
silently changed — a fundamentally different question than any internal
contract category 4 checks, since nothing internal to this codebase can
prove a *provider's* behavior is still what it was. Two trigger
conditions, not one:

- **(a) Diff-driven** — same logic as category 4: a **Major** change
  (below) that touches boundary-calling code (e.g. `revenuecat.ts`,
  `claude.ts`, `RevenueCatManager.kt`) also runs the External suite for
  that boundary. Not a separate thing to remember — it's folded into
  "what a Major change on this module requires."
- **(b) Event-driven** — independent of any diff: release-gated (before
  pushing a major update), a 3rd-party SDK/API version bump, or explicit
  suspicion of drift. This is what used to be called "Weekly"/"Release"
  (scan-proxy) or "Weekly" (Android) — see "Event-based tiers, not
  time-cadence tiers" below for why those names were retired.

Where a platform's real boundary has two genuinely different scopes —
through-our-own-deployed-service vs. direct-provider-boundary — those
are two suites *within* External, not two separate categories and not
kept as separately named tiers. `scan-proxy` is the concrete example:
its real-network suite against the deployed Worker itself, and its
real-network suite calling RevenueCat/Anthropic directly, are both
External, distinguished by scope not by name.

## Regression scoping: Minor vs. Major

Not a calendar cadence (no "daily"/"weekly" here) — scope is driven by
what a change actually touches, decided per session against the real
diff:

- **Minor** — a change confined to internal logic: no new library
  pulled in, no change to the module's public interface (parameters,
  return type/format, or exported names). Run that module's **Minor**
  suite — its function unit tests and interaction tests. Its module
  tests don't need to re-run in full if its public surface genuinely
  didn't move, though re-running them is always safe.
- **Major** — a new library is used internally, *or* the module's
  parameter list or return type/format changes, *or* a large enough
  chunk of the module changed that "it's still internal-only" isn't a
  confident claim. Run that module's **full** suite (all three
  file-level categories above). If the changed interface is shared with
  another module, run that other module's Major suite too, plus the
  inter-module interface tests between them (category 4). If the change
  touches code that calls a real 3rd-party boundary, also run that
  boundary's **External** suite (category 5's diff-driven trigger).
- **Session regression** — the actual set of tests run in a session is
  assembled from the rules above against what really changed, not a
  fixed tier. A session might run one module's Minor suite, another
  module's full Major suite, and one interface test between them — that
  asymmetry is intended, not a shortcut.

New library or new-collaborator-under-a-changed-contract is deliberately
treated as Major even when no parameter/return shape moved: a new
dependency is a broader risk surface (install, licensing, version
conflicts, unfamiliar failure modes) than the diff's line count alone
would suggest.

## Python test commands

The full Python run is **`uv run pytest -n auto`** (`pytest-xdist`): about 40 s
for about 1,100 tests, against about 170 s on one core (measured 2026-10-18, #129).
Bare `uv run pytest` still runs the same tests serially, slow ones included.
`addopts` caps `-n auto` at 8 workers (`--maxprocesses=8`): 24 workers
ran this machine out of memory (failures were "paging file too small",
`bad_alloc` in Tesseract and a JVM that could not map its heap), and past 8 the run is no faster, because the
longest serial group sets the floor. `--dist loadgroup` keeps tests that cannot
share a worker together: those marked `@pytest.mark.xdist_group("gradle")` or
`("node")` run one after another, so two JVMs or two Node installs never start
at once. The summary prints `deselected: N` itself, since xdist drops that count.

Tests marked `slow` are expensive and are owed only when the diff touches what
they check. The planner (`scripts/test_planner.py`, groups under `slow` in
`scripts/test_planner_config.json`) leaves them out of the Minor, Major, context
and application runs and lists them separately, at issue and session level:

| Slow tests | Owed when the diff touches |
|---|---|
| Tooling checks that start pytest, npm, Node or Gradle (`test_test_planner.py`, `test_context_test_commands.py`, `test_android_file_command_slow.py`) | `scripts/`, `pyproject.toml`, the Web, Scan Proxy and Android build files that define their test commands, `tests/conftest.py`, `tests/_test_command_helpers.py` |
| Real-photo OCR and pool regressions | the OCR modules (`src/hdttools/*_ocr.py`, `ocr_common.py`), `api/main.py`, `api/breakdown.py`, the pool and discovery scripts, `ExampleDocs/` |
| Streamlit walkthrough with real photos | `streamlit_app/`, the OCR modules, `ExampleDocs/` |
| Breakdown combinatorial sweep | `src/hdttools/api/breakdown.py` |

A diff that touches only other `src/hdttools` files owes none of them. At
**release** level the planner always lists all of them
(`uv run pytest -n auto -m "slow and not external"`). Any command that gives its
own `-m` replaces `addopts`' `-m "not external"`, so each slow command repeats
`not external`.

## Cross-platform duplication

RigCheck's business logic exists more than once by design (`compute_breakdown`/
`verdict_for` in Python, independently re-implemented in Kotlin for
Android — a hand-port, not a shared call). Each language/platform
implementation gets its own tests by default; tests are **not**
assumed to transfer across a language boundary just because the
underlying operation is conceptually the same.

**Preferred when it's genuinely the same operation**: define one shared
set of input → expected-output (and expected-error) cases once, and have
each platform's own test runner consume that same set against its own
implementation.

**Built 2026-08-21** for `compute_breakdown`/`verdict_for`:
`test-vectors/breakdown_cases.json`, consumed by
`tests/test_breakdown_golden_vectors.py` (Python),
`android/.../domain/BreakdownGoldenVectorTest.kt` (Kotlin) and
`web/src/breakdown.test.ts` (TypeScript). Each case declares a `requires`
list of capabilities it depends on; every runner FAILS (never skips) a case
naming a capability it doesn't know (#55), and asserts each row's note and
badge plus the verdict headline and subline, not only the figures. Every
Breakdown row has an over-limit case (18 cases today). First run that day found real drift (4 of 9 cases
supported, including a live bug — see `ARCHIVE_TESTING.md` at the repo
root for that writeup);
by the end of the same day's follow-up work, the Kotlin port had gained
every missing capability, so all cases run for real in every runner —
full parity with Python.

**Also built 2026-08-21**, a narrower fixture for a single risky
convention rather than full input/output cases:
`test-vectors/pin_weight_pct_contract.json`, consumed by
`tests/test_api.py`'s `test_breakdown_endpoint_pin_weight_pct_is_a_fraction_not_the_ui_percentage`
and `web/src/api.test.ts`. Every UI works in whole percentage points
(15–25); `/api/breakdown`'s `pin_weight_pct` is the equivalent 0.15–0.25
fraction, converted at each platform's own thin API-client boundary — a
silently-wrong-math risk shape (right field, wrong units, no type error
anywhere) rather than a missing-field one. This is a genuine interface
test, not a golden-vector case: it only proves the *contract* (a whole
number in, that same value ÷ 100 out) holds independently on each side of
the boundary, not any particular breakdown math.

**Also built 2026-08-21**, a third shared fixture, this time a plain key
list rather than input/output values or a units conversion:
`test-vectors/breakdown_response_shape_contract.json`, consumed by
`tests/test_api.py`'s `test_breakdown_response_matches_the_shared_api_contract`
(real, unmocked endpoint call — the "ground truth" half) and
`web/src/apiShape.test.ts` (a type-literal check that `types.ts`'s
`BreakdownItem`/`VerdictInfo` still declare exactly those keys — the
"does our mirror still match" half). Every `web/` test otherwise mocks
`fetch`/`./api`, so nothing there ever touches a real Python response; a
field rename or drop in `schemas.py` would previously have gone uncaught
by the entire `web/` suite. This is a manually-synced tripwire, not a
fully-derived contract — see `FUTURE_API_SCHEMA_VALIDATION.md` for the
Pydantic-JSON-Schema-export approach that would remove the manual-sync
step entirely, parked for later rather than built now since this covers
the two highest-traffic shapes (`BreakdownItemOut`/`VerdictOut`) at much
lower cost; `TruckTagOut`/`TrailerTagOut`/`ScaleTicketOut` remain
uncovered by either approach as of this writing.

## Event-based tiers, not time-cadence tiers

Retired 2026-08-24 (full narrative in `ARCHIVE_TESTING.md`): `android/TESTING.md` used to
describe its own Unit/Daily/Weekly tiers and `workers/scan-proxy/TESTING.md`
its own Sanity/Daily/Weekly/Release tiers, coexisting alongside Minor/
Major as a second, independent axis (a test's network-dependency
classification, orthogonal to what a given session's diff scoped in).
That two-axis model is gone — **Minor/Major/External is the one axis
now, used identically on every platform**:

- **Minor** — a change confined to internal logic (see "Regression
  scoping" above). Runs a module's offline function + interaction tests.
  This is what "Sanity" (scan-proxy) and "Unit" (Android) used to mean —
  same tests, same commands, new name.
- **Major** — a new library, or the module's public interface changed,
  or a large enough internal change that "internal-only" isn't a
  confident claim. Runs a module's full offline suite (all of category
  1-3, plus category 4 if an interface is shared). This is what "Daily"
  (both platforms) used to mean — same tests, same commands, new name.
- **External** (category 5, above) — real, live calls to a genuine
  3rd-party boundary. This is what "Weekly" (Android, scan-proxy) and
  "Release" (scan-proxy) used to mean, now unified as External's two
  trigger conditions rather than two more separately-named tiers. Where
  a platform has two real scopes (through-our-service vs.
  direct-provider-boundary — scan-proxy's old Weekly-vs-Release split),
  those are External's two suites, not two tiers.

**Why the time-cadence names were dropped**: "Daily"/"Weekly" never
actually ran on a real cadence in practice, confirmed 2026-08-21 —
scan-proxy's Weekly tier was "just cheap enough to run anytime, ad hoc,
no enforced schedule," and Release was gated on a real decision (pushing
a major update), never a calendar. The names implied a clock that was
never actually there; **Minor/Major/External names what actually
triggers a test running** — a change's real scope, or a real-world event
(a release, a dependency bump, suspicion of drift) — which is what was
really governing these tiers all along.

**Applied uniformly across all four platforms**, including Web and
Python/Streamlit, even though neither ever had tier language before —
see `web/TESTING.md`'s and `tests/TESTING.md`'s own "Event-based tiers"
sections. Neither currently has a real External suite (no direct
3rd-party boundary call exists in either today), which is a fact about
what those platforms do, not a gap in the model.

## Coverage gate

`scripts/coverage_gate.py` (`uv run scripts/coverage_gate.py`) — a
single cross-platform orchestrator, run at release time, reporting real
coverage for all four platforms from their own native coverage tooling
(JaCoCo for Android, `coverage.py` for Python, Vitest's `coverage-v8`
provider for Web, Node's `--experimental-test-coverage` for scan-proxy).

**Enforced** for Android, Python, and scan-proxy — the three platforms
with a real release-gating event today (Android/scan-proxy's shared
"before a major Play Store push" trigger; Python/Streamlit's suite is
what that same push exercises on the backend side). Python and
scan-proxy are baseline floors: the gate fails only if the real number
drops *below* its last known-good baseline (2026-08-24: Python 79%,
scan-proxy 100%).

**The Android gate is a JVM floor on decision logic, not an app-wide
number.** It reads the JVM unit-test JaCoCo report (`./gradlew
testDebugUnitTest createDebugUnitTestCoverageReport`, about 20 s, no
device) and fails below **95.0%** instruction coverage over the classes
listed in `android/coverage-logic.toml` (Breakdown and Verdict math, Scan
rules, field mapping, account rules; about 97% when it was set, 2026-10-18).
Compose screens, navigation, view-model wiring and provider wrappers have
**no coverage number**: device tests and External tests verify them, and
they are listed as waived with a reason. Coverage is a map of untested
code, not a score. The gate also fails when an allow-listed class is not in
the report (a stale list) and names every class in `domain`, `data` or
`ui` that is on neither list as *unclassified* (a warning, never a
failure). The device-based Android numbers (Major suite, Major+External
merged) are still printed, as informational numbers that gate nothing.

**Report-only** for Web — the one platform with no real release event
yet (no hosting at all today; see `NEXT_STEPS.md`'s "Deliberately not on
this list"). The script prints its real number with an explicit "not
gated — no release event yet" note and always exits 0 for it. Once Web
gains a real release event, its threshold flips to enforced the same way
the other three already are.

The script's overall exit code reflects only the platforms actually
gated — a Web coverage dip alone never fails the gate.

## Dashboard

`scripts/generate_dashboard.py` (`uv run scripts/generate_dashboard.py`)
— generates `dashboard.svg`, embedded at the top of `README.md`
(roadmap item #7). One row per platform, one column per Minor/Major/
External plus a coverage column, color-coded with the same Blue-100/
Green->90/Yellow->80/Red-<80 banding the coverage gate uses.

**Minor/Major run fresh on every regen** — cheap, offline, so there's no
reason not to. Their real pass-rate is parsed from each platform's own
structured test report (JUnit XML — pytest's `--junitxml`, Vitest's/
Node's built-in `junit` reporters, and AGP's already-automatic reports
for Android), via `scripts/dashboard_lib.py`'s `parse_junit_xml` (shared
logic across all four platforms' genuinely different report shapes — see
that module's own docstring for the real schema differences found while
building this).

**Coverage reuses `coverage_gate.py`'s own run-or-read functions
directly** (`get_android_result`/`get_python_result`/`get_web_result`/
`get_scan_proxy_result`) rather than re-implementing coverage retrieval
— one source of truth, so the dashboard and the release gate can never
silently disagree about the same number. Web's real percentage still
displays even though `coverage_gate.py` doesn't enforce it yet (report-
only, not hidden — see that script's own "not gated" note).

**External never re-runs from the dashboard** — those suites cost real
money/time (a real Claude call, a booted emulator), and regenerating a
README graphic shouldn't trigger that. Instead, `scripts/record_external_result.py`
is called from the *end* of each real External wrapper script
(`android/test-weekly.ps1`, `workers/scan-proxy/test-weekly.ps1`,
`workers/scan-proxy/test-release.ps1` — all three, whenever they're
actually run for real) and persists the result to the git-tracked
`scripts/dashboard_data/external_status.json`. The dashboard just reads
that file — a platform's External cell shows `n/a` until its wrapper has
actually been run at least once. `workers/scan-proxy/test-weekly.ps1` is
new as of this work — before it existed, that suite only ever ran via
bare `npm run test:weekly`, with no way to record a result anywhere.

`--refresh` on either `coverage_gate.py` or `generate_dashboard.py`
forces every already-cached report to be regenerated instead of reused;
without it, an existing report on disk is read as-is.

### Dashboard update, 2026-10-04 (#49)

The rows are now the five contexts of `CONTEXT-MAP.md` (Core, Streamlit,
Web, Android, Scan Proxy) instead of four platforms. Python's Minor and
Major are real: the pytest markers from #50 split the shared suite, so
Core and Streamlit each get `-m "minor and <ctx>"` and `-m <ctx>` runs.
Their coverage comes from the per-file figures in `coverage.json`
(`src/hdttools/` and `streamlit_app/`), shown report-only because the
release gate's floor applies to the combined Python number. The new
**Surfaces** column shows fresh/active External surfaces per platform
(planned ones as a count), computed from the manifest, recorded status
and git; registries are not contacted, so a new upstream release shows
in `external_freshness.py`, not here. The legacy External column is
unchanged and still read from `external_status.json`.

Measured results are saved to `scripts/dashboard_data/test_results.json`
(date and commit; the graphic's header shows them) by any run that
measures. `uv run scripts/generate_dashboard.py --from-snapshot` runs
nothing and rebuilds the graphic from that file plus the live External
cells.

**Commit hook.** `.githooks/pre-commit` runs `--from-snapshot` and stages
`dashboard.svg`. It runs no tests, never blocks a commit (any failure
only warns), and is enabled once per clone with
`git config core.hooksPath .githooks`. `--no-verify` skips it. Because
it does not re-measure, the pass-rates and coverage stay as of the date
and commit in the header until someone runs the generator without
`--from-snapshot`. Android's device tier and coverage need a connected
device and show `n/a` without one. Python's expected failures (xfail)
count as not passed, as before.

## External release gate (ADR-0008, #43)

A release needs every External surface in its chain fresh (`uv run
scripts/external_freshness.py` says which are not). `scripts/external_gate.py`
turns that into a block. It only reads the recorded status, git and the package
registries; it never runs a live test. It blocks on a stale, failed, skipped or
never-run surface and when a registry cannot be reached. Planned surfaces never
block. It runs in four places:

| Where | Gates | Chain |
|---|---|---|
| `.githooks/pre-push` | a push to `MPSkills` (Pages' production branch) whose diff touches `web/`, `workers/scan-proxy/` or `android/`; any other push, including a docs-only one, passes without contacting a registry | the touched directory's platform: web, scan-proxy, android |
| `npm run deploy` in `workers/scan-proxy/` (`scripts/scan_proxy_deploy.py`, also used by `pretest:weekly` and `android/test-weekly.ps1`) | the Worker deploy | scan-proxy |
| `workers/scan-proxy/release.ps1` | before the release and weekly suites, the latter deploys | scan-proxy |
| `android/release.ps1` | before the weekly suite, which deploys the Worker | android, which includes the Worker's surfaces |

**Setup.** `git config core.hooksPath .githooks` once per clone (the same setting
as the pre-commit hook), and `uv` on the PATH, since the hook runs `uv run`. No
other install. If the hook cannot run, the push fails rather than slipping through.

**Unlocking a blocked gate.** Run the External suite that covers each named
surface (`web\test-external.ps1`, `workers\scan-proxy\test-external.ps1`) and
try again. The Worker's own surfaces are tested against the deployed Worker, so
deploying changed Worker code in order to test it is the case that needs a force.

**Forcing it needs a reason.** `EXTERNAL_GATE_FORCE_REASON="why" git push` (git
passes a hook no flags), `npm run deploy -- --force --reason "why"`, or
`-Force -Reason "why"` on the two `release.ps1` scripts. `--force` without a
reason is refused. The reason is recorded in
`scripts/dashboard_data/external_status.json` on every surface that was blocking,
and the dashboard's Surfaces cell shows `(N overridden)` until each one's next
real pass; a failed or skipped run does not clear it. Forcing a gate that would
have passed records nothing. The mark is written to the status file of the
checkout you run from, so it is a tracked-file change to commit; and the gate
judges that checkout's working tree and status file, so push `MPSkills` from the
checkout that has it checked out. The mark stays until a real pass even if the
surface stops looking stale in between (for example a registry that was only
briefly unreachable).

**`git push --no-verify` bypasses the hook on purpose.** It skips every check and
records nothing, so the dashboard cannot show it. It is a deliberate act, not an
accident, and the only way past the hook without a recorded reason. A push also
skips the hook when it runs from a machine without `core.hooksPath` set.

Not done: the registries are asked on every qualifying push (about a dozen
requests; an unreachable one blocks) with no cache.

## Status of this repo against the framework

This framework was defined 2026-08-20, after most of this repo's existing
tests were already written — they haven't been retroactively categorized
against it, and the framework hasn't yet been applied as an actual
per-session discipline. Reconciling the sanity/daily/weekly/release tiers
with Minor/Major closed that specific gap 2026-08-21; retiring those
tier names entirely in favor of the single Minor/Major/External axis
(immediately above), plus standing up the coverage gate, closed the
remaining redesign 2026-08-24. Applying Minor/Major/External as a lived
per-session discipline going forward remains a separate, ongoing thing
to keep honest, not a one-time task.
