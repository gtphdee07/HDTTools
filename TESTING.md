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

Verifies a real remote interface (Anthropic, RevenueCat, Supabase, the
deployed Worker and Pages site) hasn't silently changed — a fundamentally
different question than any internal contract category 4 checks, since
nothing internal to this codebase can prove a *provider's* behavior is
still what it was. Real calls, dedicated test accounts, never mocked.
The model is in `docs/adr/0008-external-api-tests-are-per-surface-and-freshness-gated.md`;
this is the working summary.

**The unit is a surface**, not a platform or a suite: one provider
interface, such as `anthropic`, `revenuecat-rest`, `supabase-auth`,
`scan-proxy-worker` or `pages-site`. Each has its own last-pass record,
and each platform keeps owning its own External suite (node, pytest,
Android instrumentation), tagging each test with its surface name (node
and pytest today; Android's surfaces are still `planned`, so it has none).
`scripts/external_manifest/surfaces/<name>.json` is the one source of
truth for a surface: its boundary files, dependency pins, watched
registry packages (npm, PyPI, Maven), maximum paid calls, the platforms
whose release depends on it, and whether it is `active` or `planned`.

**Depth, per surface:** reachable and authenticated; response shape
matches our contract; error contracts; a full user journey. A surface
whose ticket says one of these does not apply records why.

**When to re-run it — freshness, not a calendar.** A surface is *stale*
when a commit since its last real pass touched its boundary files or
dependency pins, or any watched package published a new stable release
after that pass (whether or not we upgraded), or a registry cannot be
reached. `uv run scripts/external_freshness.py` prints the verdicts and
the stale list; each platform's wrapper passes that list to its runner's
native filter, so only stale surfaces re-run. This replaces the older
"diff-driven plus event-driven" pair: a Major change that touches
boundary code makes the surface stale through its boundary files, and a
dependency bump or a provider release does the same through the pins and
the registries. Nothing is on a timer. A provider that changes its web
API without publishing a library release is out of scope, by design.

**What a surface can read as** (shown on the dashboard, see below):

| State | Meaning |
|---|---|
| fresh | last real pass is newer than every boundary-file change and registry release |
| stale | never passed, or something it depends on changed since its last pass |
| failed | its latest real run failed |
| skipped | its latest run was an explicit skip: a skip is recorded, never advances the timestamp and never counts as a pass, so the surface stays stale |
| overridden | stale, and the release gate was forced past it with a reason (until its next real pass) |
| planned | listed in the manifest but not yet testable; shown as not covered and never blocking |

A missing secret, account or device **fails** the run; only an explicit
skip flag records `skipped`. Each paid surface has a maximum call count
in the manifest, enforced by a shared counter that aborts the run.
`scripts/record_external_result.py --surface NAME --outcome pass|fail|skipped`
records the result (outcome, time, registry versions seen, our commit SHA);
the old `platform/suite` entries in `external_status.json` are history
only, ignored by the gate and not shown on the dashboard. The release
gate that reads all this is in "External release gate" below.

Where a platform's real boundary has two genuinely different scopes —
through-our-own-deployed-service vs. direct-provider-boundary — those
are different surfaces, not different tiers. `scan-proxy` is the
concrete example: `scan-proxy-worker` (the deployed Worker itself) and
`anthropic`/`revenuecat-rest` (the providers it calls) are separate
surfaces with separate records.

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
| Real-photo OCR and pool regressions | the OCR modules (`src/hdttools/*_ocr.py`, `ocr_common.py`), `api/breakdown.py`, the pool and discovery scripts, `ExampleDocs/` |
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
`test-vectors/pin_weight_pct_contract.json`, consumed by Web's
`web/src/breakdown.test.ts`. Every UI works in whole percentage points
(15–25); the breakdown math takes the equivalent 0.15–0.25 fraction,
converted at each UI's own thin boundary (Web's `createBreakdown`) — a
silently-wrong-math risk shape (right field, wrong units, no type error
anywhere) rather than a missing-field one. It proves the *contract* (a
whole number in, that same value ÷ 100 out), not any particular breakdown
math. (Its Python half, a test of the removed FastAPI endpoint, went with
the app in #135.)

**Response shape.** The keys the UIs read from each breakdown row and from
the verdict are asserted by the golden-vector runners in Python, Kotlin and
TypeScript (`label`, `tone`, `badgeLabel`, `pct`, `actualLabel`,
`limitLabel`, `note`, `estimated`; `status`, `headline`, `subline`), so
`test-vectors/breakdown_response_shape_contract.json` and Web's
`apiShape.test.ts` were retired in #135 along with the FastAPI app they
guarded. Presentation-only keys (`barColor`, `bandBg`, `icon`) need no
assertion. Kotlin compares raw numbers and the badge text rather than the
formatted `actualLabel`/`limitLabel` strings.

**Built 2026-10-19 (#115)**, a fourth shared fixture, for what a Scan that
does not deliver tells the user and how a retry behaves:
`test-vectors/scan_outcomes.json`, one row per case, written up as "Scan
outcomes" in `workers/scan-proxy/CONTEXT.md`. Consumed by
`web/src/scanOutcomes.test.ts` and `android/.../ui/ScanOutcomesFixtureTest.kt`.
Each row names the phrases the message must contain, whether a retry keeps the
request id, and whether Try again is offered; the fixture is the source of
truth and each client keeps its own strings. A row field not yet built in a
client is marked pending for it in the fixture, with the ticket that builds it;
the test skips and lists it. Changing the fixture changes both clients' queued
tests (`scripts/test_planner_config.json`, interface `scan-outcomes`).

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
  3rd-party boundary, per surface, run when the surface is stale. This is
  what "Weekly" (Android, scan-proxy) and "Release" (scan-proxy) used to
  mean, now unified as surfaces and their freshness rather than two more
  separately-named tiers. Where a platform has two real scopes
  (through-our-service vs. direct-provider-boundary — scan-proxy's old
  Weekly-vs-Release split), those are separate surfaces, not two tiers.

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
sections. Python/Streamlit's only real External test is Core's Claude
vision call (the `anthropic` surface); Web has its own External suite
(`supabase-auth`, `pages-site`, `supabase-tables`, `revenuecat-web-billing`).

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
README graphic shouldn't trigger that. Instead, the per-surface External
runners (`scripts/external_wrapper.py`, behind the `test-external`
wrappers) record each surface's result with `scripts/record_external_result.py`
in the git-tracked `scripts/dashboard_data/external_status.json` (see
category 5 above). The dashboard just reads that file; a surface that has
never run reads as stale. The older whole-platform wrappers
(`android/test-weekly.ps1`, `workers/scan-proxy/test-weekly.ps1`,
`test-release.ps1`) still write `platform/suite` entries (`android.weekly`,
`scan_proxy.weekly`, `scan_proxy.release`) into that file; they are history
only, and the dashboard no longer shows them (#44).

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
in `external_freshness.py`, not here. (#44 below merged it with the old
External column.)

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

### Dashboard update, 2026-10-19 (#44): per-surface External status

The old per-suite External column is gone; the **External** column is now
the surface cell (`fresh/active`, then counts of what is not fresh:
`2/5 (1 planned, 1 failed)`). Below the platform grid, an **External
surfaces** list shows every surface in the manifest on its own line:
a coloured dot (fresh blue, stale and skipped yellow, failed and
overridden red, planned grey), the surface name, its state and the
platforms whose release depends on it. A planned surface reads
`planned - not covered`. The states are the ones in category 5 above;
`failed` and `skipped` are new to the graphic (they used to read plainly
as stale). The graphic is built from the manifest, the recorded
per-surface status and git only, so it stays offline; the old
`platform/suite` entries are never read.

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
and the dashboard's External cell shows `(N overridden)` until each one's next
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
