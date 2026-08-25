# RigCheck — Test-Driven Development methodology

This file defines the *development-time workflow* for this repo: write a
failing test before the code that makes it pass, on all four product
lines. It's a companion to, not a replacement for, two things that
already exist:

- **`CLAUDE.md`**'s "Coding Preferences" section, which is the root
  authority for "every function needs an automated test" and points here
  for the workflow that produces those tests in the first place.
- Each platform's **`TESTING.md`** (`tests/TESTING.md`, `android/TESTING.md`,
  `web/TESTING.md`, `workers/scan-proxy/TESTING.md`) and the root
  **`TESTING.md`**, which define how tests are *categorized and run*
  after they exist — the Function/Interaction/Module/Inter-module-
  interface/External categories, and the Minor/Major/External
  regression-scoping rules for which suites a given change needs to run.

TDD and the Minor/Major/External model are related but distinct
concerns: this file is about the loop you run while writing one test
against one not-yet-written piece of behavior; the TESTING.md files are
about which existing suites a finished change needs to re-run before it
ships. Every section below says explicitly which category a TDD-driven
test starts in under the existing model, so the two documents stay one
mental model, not two.

## Common TDD discipline

Every platform below follows the same cycle, in the same spirit, using
only that platform's own real tools. This is deliberately not four
different methodologies with a shared name — see "Why one approach" at
the end of this file for the reasoning.

### Red — write the test first, then *watch it fail for real*

Write the test against the interface you want to exist, before writing
the implementation (or before writing the fix, if this is a bug). Then
actually run it and read the real failure output — don't reason your way
to "this should fail because X" and move on without checking. This
repo's own history is the reason for that rule, not a textbook
platitude: the Android detekt/JDK-25 toolchain failure
(`DEV_ENVIRONMENT.md`'s Gradle-daemon-JVM gotcha), the OCR framing
assumptions that turned out wrong against real `ExampleDocs/` photos
(`tests/test_real_photo_ocr_accuracy.py`, see `ARCHIVE_WEB_STREAMLIT.md`),
and the `pin_weight_pct == 1.0` division-by-zero
(`ARCHIVE_BREAKDOWN_SWEEP.md`) were all cases where the mental model of
"this will obviously behave like X" was wrong the moment something was
actually run. Watching Red happen for real, not just trusting that it
would, is as much a part of this project's TDD discipline as the
Red-Green-Refactor shape itself.

**When Red can't reach Green for a known, specific reason**: don't
silently skip. This project's answer is `pytest.mark.xfail(strict=True)`
with a real, specific reason string — see
`tests/test_real_photo_ocr_accuracy.py`'s two documented real OCR-accuracy
limits (a digit-drop, a two-column layout jumble), each recorded in
`ExampleDocs/golden_fields.json` with the actual reason, not a vague
"known issue." `strict=True` means if the case ever starts passing for
real, that's a hard failure demanding the xfail be removed — a limitation
note is never allowed to quietly become permanent scenery. The other
three platforms don't have their own established equivalent of
`xfail(strict=True)` yet (Kotlin's JUnit4, Vitest, and Node's `test`
runner each have a `.skip`, but nothing here has adopted a *strict*
skip-that-fails-when-it-starts-passing convention for them) — treat that
as an open question if a genuine "known limitation, can't fix yet" case
comes up on Web, Android, or scan-proxy, not a decided pattern to copy
uncritically from Python.

### Green — the minimum real change that passes

Make the test pass with the smallest change that's honestly correct —
not the smallest change that makes the assertion true by coincidence.
Run the *specific* new test first (each platform section below has the
real single-test command), then the module's full Minor suite before
moving on, so a fix that happens to break a sibling case doesn't sit
undetected until a much later full run.

### Refactor — with the test as the safety net

Clean up now that the behavior is pinned down by a passing test, and
re-run the same test (plus its module's Minor suite) after. If the
refactor touches the module's public interface (signature, return
shape), it has just become a **Major** change under the root
`TESTING.md`'s regression-scoping rules — run that module's full suite,
not just the one new test.

### This project's own layered rules, on top of Red-Green-Refactor

1. **Real over mocked wherever practical.** Mocks are for genuine
   unit-level isolation — proving one function's own logic, not for
   dodging a real dependency a test is actually supposed to exercise.
   `tests/test_vision_client.py` is the model case: it mocks the
   Anthropic client, but only to test `extract_via_claude`'s own
   tool-selection logic in isolation; it is not a substitute for a real
   Claude-vision test anywhere a test's whole point is proving real
   extraction works (that's `tests/test_real_photo_ocr_accuracy.py` for
   OCR, and scan-proxy's `weekly`/`release` suites for Claude). When
   writing a new TDD test, ask which one this is *before* reaching for a
   mock — isolating one function's branching, or proving an integration
   actually works — and don't default to the mocked version because it's
   easier to write.
2. **Strict-by-default over graceful skip** — see the Red section above.
3. **Bugs found outside the TDD loop still get retrofitted into it.**
   Not every bug is found by writing a test first — this project's own
   combinatorial sweep (`tests/test_breakdown_combinatorial_sweep.py`,
   `itertools.product` over representative value dimensions, not
   `hypothesis`-style fuzzing) found two real crash bugs in
   `compute_breakdown` (an explicit `0` rated limit, and
   `pin_weight_pct == 1.0`) by exercising invariants across combinations,
   not by TDD. The fix process after the fact was still Red → Green →
   Refactor: confirm the crash for real
   (`compute_breakdown({"front_gawr_lb": 0, ...}, {}, {...})` raising
   `ZeroDivisionError`, confirmed live), fix it on both Python and Kotlin,
   then add permanent regression tests on both platforms *plus* promote
   the two specific cases to the shared golden-vector file,
   `test-vectors/breakdown_cases.json` (full narrative in
   `ARCHIVE_BREAKDOWN_SWEEP.md`). Whenever a bug turns up by any other
   means — manual testing, code review, a sweep — closing it still goes
   through this same discipline: reproduce for real first, fix minimally,
   then lock it down with a permanent test, not just a changelog entry.
4. **Cross-platform shared logic gets a shared regression case, not a
   hand-duplicated one.** `compute_breakdown`/`verdict_for` exists twice
   by design (Python source of truth, hand-ported Kotlin) — when a TDD
   cycle (or a retrofitted bug fix, per rule 3) touches that shared
   math, the resulting case belongs in `test-vectors/breakdown_cases.json`,
   consumed by both `tests/test_breakdown_golden_vectors.py` and
   `BreakdownGoldenVectorTest.kt`, not copy-typed by hand into each
   platform's own test file. This is specifically about genuinely shared
   business logic, not every test — most Function/Module/Interaction
   tests stay platform-local, per the root `TESTING.md`'s "Cross-platform
   duplication" section.

---

## Python backend / Streamlit (`src/hdttools/`, `streamlit_app/`)

**Fast Red/Green loop — run one new test in isolation:**

```bash
uv run pytest tests/test_breakdown.py::test_zero_rated_limit_is_treated_as_not_provided_not_crashed_on -v
```

Standard pytest node-id addressing; no project-specific wrapper needed.
`uv run` is required per `CLAUDE.md` — never a bare `pytest`/`python -m
pytest`, since that would bypass `.venv`.

**Where a new test joins, and its starting category:** most new
Python-side logic tests join the file matching the module under test
(`test_breakdown.py` for `breakdown.py`, `test_scale_ticket_ocr_parsing.py`
for `scale_ticket_ocr.py`, etc. — see `tests/TESTING.md`'s "By file"
table for the full map). A TDD-driven test on one function, its
collaborators faked, starts as a **Function** test; if it drives a real
multi-step sequence sharing `st.session_state` (Streamlit) it's an
**Interaction** test instead (join `test_streamlit_app.py`); if it
exercises a file's whole public surface it's a **Module** test. Per
`tests/TESTING.md`, this suite has no tagged fast subset yet, so today
Minor and Major both mean "the whole `uv run pytest -q` run" — there's no
narrower command to reach for. A test graduates from Function/Module to
**inter-module interface** the moment it starts asserting a contract
*between* Python and another platform — the existing precedent is
`test_api.py`'s `test_breakdown_endpoint_pin_weight_pct_is_a_fraction_not_the_ui_percentage`
and `test_breakdown_response_matches_the_shared_api_contract`, each
paired with a `web/` test via a shared `test-vectors/*.json` fixture. If
the change touches `compute_breakdown`/`verdict_for` specifically, see
rule 4 above — the case belongs in `test-vectors/breakdown_cases.json`,
not only in `test_breakdown.py`.

**Real-vs-mocked convention, with evidence:** `test_vision_client.py`
mocks only the Anthropic client, to isolate `extract_via_claude`'s own
logic. `test_scale_ticket_real_photo.py` and
`test_real_photo_ocr_accuracy.py` run real Tesseract against real
`ExampleDocs/` photos — no OCR mocking anywhere in this repo, since OCR
accuracy against real images is exactly the thing worth proving.
`test_readers_integration.py` mocks every I/O boundary (file picker,
vision, review form, database) because its job is proving the
`read_*_tag` orchestration/control-flow shape, not re-proving OCR or
Claude accuracy that other tests already cover for real.

**TDD-loop-specific gotcha:** none beyond the general Tesseract-path
auto-detection already covered in `DEV_ENVIRONMENT.md` — no JVM/daemon
warm-up cost here, so `uv run pytest tests/test_X.py::test_Y -v` is
already about as fast a loop as this repo has.

---

## Web (`web/`, React + TypeScript + Vite)

**Fast Red/Green loop — run one new test in isolation:**

```bash
cd web
npm test -- src/wizard/ReviewStep.test.tsx -t "pin-weight slider hides once standalone weight is known"
```

(`npm test` is `vitest run` per `web/package.json`; args after `--` pass
through to Vitest, whose own `-t`/`--testNamePattern` filters to one
`test()`/`it()` block. Passing just the file with no `-t` runs every case
in that one file, which is often the right granularity for a first Red
run before narrowing further.)

**Where a new test joins, and its starting category:** join the file
matching the component/module under test (`web/TESTING.md`'s "By file"
table has the current map — e.g. `UploadStep.test.tsx`,
`ResultsStep.test.tsx`, `recentRigs.test.ts`). Fake-props component tests
and pure-function tests (`api.test.ts`, `recentRigs.test.ts`) start as
**Function**/**Module** tests; anything driving `App.tsx`'s real rendered
UI through `@testing-library/user-event` to exercise its shared `wizard`
closure state (`App.interaction.test.tsx`) is an **Interaction** test.
Per `web/TESTING.md`, Minor and Major are the same undifferentiated
`npm test` run today, same as Python — no tagged fast subset exists yet.
A test graduates to **cross-platform interface** the moment it asserts a
contract against Python's real response shape rather than a
hand-maintained fixture — the existing precedent is `api.test.ts`'s
`pin_weight_pct` case and `apiShape.test.ts`, each paired with a Python
test via a shared `test-vectors/*.json` file.

**Real-vs-mocked convention, with evidence:** every network call
(`extractTruckTag`/`extractTrailerTag`/`extractScaleTicket`/
`createBreakdown`) is mocked with `vi.mock('./api')` in every test that
needs one — this suite has no real-backend test at all today (no Web
External suite exists; `web/TESTING.md` documents this as N/A, not a
gap, since nothing in `web/` calls a 3rd-party boundary directly).
`localStorage`/`sessionStorage`, by contrast, are the **real** jsdom
implementations, never mocked — `recentRigs.test.ts` exercises real
persistence behavior (including `setItem` throwing on quota) because
that's exactly what's worth proving for real, the same "mock only what a
test isn't actually about" judgment call as Python's
`test_readers_integration.py`.

**TDD-loop-specific gotcha:** `src/setupTests.ts` centralizes
`afterEach(cleanup)` because React Testing Library's automatic cleanup
only self-wires when it finds a *global* `afterEach`, which isn't the
case here (`globals: true` isn't set in `vite.config.ts`). A new test
file that doesn't import through the existing setup can silently leave
renders mounted across cases in the same file, corrupting later
`getByText`/`getByRole` queries with stale elements from earlier tests —
this already happened once, in `UploadStep.test.tsx`. If a new Red run
shows a query matching more elements than expected, check this before
assuming the component itself is wrong.

---

## Android (`android/`, Kotlin + Jetpack Compose)

**Fast Red/Green loop — run one new test in isolation:**

```powershell
cd android
.\gradlew.bat :app:testDebugUnitTest --tests "com.rigcheck.app.domain.BreakdownTest.trailer axle limit uses custom axle count" --console=plain
```

**Verified empirically for this doc** (2026-08-25): the aggregate
`./gradlew test` task (and `:app:test`) does *not* accept `--tests` at
all — running it errors with `Unknown command-line option '--tests'`,
because AGP's `test`/`:app:test` is a plain lifecycle `Task` that only
depends on the real per-variant `Test`-typed tasks
(`:app:testDebugUnitTest`, `:app:testReleaseUnitTest`); `--tests` only
exists on those concrete tasks (confirmed via
`.\gradlew.bat help --task :app:testDebugUnitTest`). Filtering to a
single backtick-named Kotlin test method (spaces and all) works when the
literal name is quoted, confirmed by running the command above and
checking `app/build/test-results/testDebugUnitTest/TEST-com.rigcheck.app.domain.BreakdownTest.xml`
afterward — exactly one `<testcase>`, not the whole class. Filtering to
a whole class (drop the trailing `.method name`) also works and is
usually the more practical granularity given how verbose Kotlin's
backtick names get.

**Where a new test joins, and its starting category:** per
`android/TESTING.md`, a Kotlin unit test with no Android
framework/Compose dependency (business logic, ViewModels tested via
MockK) joins the **Minor (Unit, JVM)** suite (`./gradlew test`) — e.g.
`BreakdownTest.kt`, `RevenueCatManagerTest.kt`. A test that needs a real
Compose render or the real `NavHost` joins the **Major (instrumented)**
suite (`./gradlew connectedDebugAndroidTest`) instead — e.g.
`ResultsScreenTest`, `RigCheckNavHostTest.kt`. A test graduates to
**External** only when it needs a real, booted RevenueCat purchase or a
real scan against the deployed Worker (`PaywallScreenWeeklyTest.kt`,
run via `.\test-weekly.ps1`) — gated on a real event (a Play Store push),
not written routinely alongside a normal TDD cycle. If the change
touches `computeBreakdown`/`verdictFor` specifically, see the common
discipline's rule 4 — promote the case into
`test-vectors/breakdown_cases.json`, consumed by
`BreakdownGoldenVectorTest.kt` on this platform.

**Real-vs-mocked convention, with evidence:** `RevenueCatManagerTest.kt`
uses MockK against `Purchases.Companion` — a deliberate unit-level
isolation of `RevenueCatManager`'s own call-ordering logic (the
`invalidateVirtualCurrenciesCache()`-before-read bug), not a stand-in for
proving RevenueCat itself still behaves as expected (that's
`PaywallScreenWeeklyTest.kt`'s job, against the real SDK and a real test
customer). Screen-level Major tests (`ResultsScreenTest`,
`BreakdownRowTest`, etc.) pass fake parameters directly into composables
— no ViewModel, no NavHost, no network — deliberately narrow to
rendering logic; `RigCheckNavHostTest.kt` is the one Major test that
wires up the real NavHost + ViewModel together, offline via
`CustomTestRunner` so `Purchases.configure()` never runs.

**TDD-loop-specific gotcha:** the Minor suite above is fast (JVM-only,
no emulator) and is what a normal Red/Green loop should stay in as long
as possible. The Major suite needs a booted emulator/device and pays a
real Gradle-daemon-JVM cost on first use — the daemon's own JVM is
pinned to JDK 21 via `android/gradle/gradle-daemon-jvm.properties`
specifically so `detekt` doesn't crash under this machine's ambient JDK
25 (`DEV_ENVIRONMENT.md`'s detekt gotcha); this JDK auto-provisions via
foojay on first run on a fresh machine, which is a one-time slow step,
not a per-loop one. An idle/sleeping emulator screen also makes
instrumented Compose tests fail with a misleading "No compose
hierarchies found in the app" error rather than a real one — the
`wakeEmulatorForInstrumentedTests` Gradle task (wired as a
`connectedDebugAndroidTest` dependency in `app/build.gradle.kts`) already
handles this automatically, so it shouldn't surface mid-TDD-loop, but if
it does, that's the known cause, not a real test bug.

---

## `workers/scan-proxy` (Cloudflare Worker, TypeScript)

**Fast Red/Green loop — run one new test in isolation:**

```bash
cd workers/scan-proxy
node --test --test-name-pattern="successful scan charges exactly once" src/scan.test.ts
```

(Same mechanism `test:sanity` already uses in `package.json` —
`node --test`'s own `--test-name-pattern`, scoped here to one file
instead of the whole `src/*.test.ts` glob for the fastest possible
single-test loop.)

**Where a new test joins, and its starting category:** join the file
matching the module under test, in request-flow order per
`workers/scan-proxy/TESTING.md`'s "What each test covers" section —
`docTypes.test.ts`, `request.test.ts`, `scan.test.ts`,
`revenuecat.test.ts`, `claude.test.ts`, `http.test.ts`, `index.test.ts`.
A new offline, fake-`ScanDeps` test starts in **Major** by default
(`npm test`); tag it `[sanity]` in its own test-name string only if it's
representative enough to belong in the small Minor subset
`npm run test:sanity` filters to via `--test-name-pattern`. It graduates
to **External** only by moving to a different, dedicated file —
`src/weekly/*.test.ts` (through-our-service, real but bounded, run via
`.\test-weekly.ps1`/`npm run test:weekly`) or `src/release/*.test.ts`
(direct-provider-boundary, needs real `ANTHROPIC_API_KEY`/
`REVENUECAT_SECRET_KEY`, run via `.\test-release.ps1`) — these are
deliberately excluded from the `src/*.test.ts` glob so `npm test`/
`test:sanity` never pick them up by accident. If a change touches
boundary-calling code (`revenuecat.ts`, `claude.ts`), the root
`TESTING.md`'s category-4/5 diff-driven rule applies: run the matching
External suite too, not just the mocked Major tests.

**Real-vs-mocked convention, with evidence:** every file under
`src/*.test.ts` mocks at the `fetch`/HTTP boundary, not the SDK
internals — `claude.test.ts` mocks `fetch` itself and asserts the real
HTTP request shape (`tool_choice`, image `source`/`media_type`/`data`)
that `@anthropic-ai/sdk` produces, rather than mocking the SDK's own
methods. `scan.test.ts` uses fully fake `ScanDeps` (no network at all) to
isolate `runScan`'s charge/extract/refund control flow — deliberately
narrow, since the money-critical ordering logic is what that file exists
to prove, not RevenueCat's or Anthropic's real behavior. The real
counterpart lives in `src/weekly/scan.weekly.test.ts` (real POSTs to the
deployed Worker) and `src/release/scan.release.test.ts` (real calls
directly at the RevenueCat/Anthropic boundary) — both explicitly turn a
real 401/403 into a named `"<ENV_VAR> appears invalid"` failure rather
than a bare status-code assertion, so a bad key is never confused with a
genuine contract break.

**TDD-loop-specific gotcha:** none specific to the edit/run loop itself —
this is the fastest of the four platforms (`node --test`, no build step,
no daemon warm-up). The one real trap is environment-adjacent, not
loop-speed: `ANTHROPIC_API_KEY` was found ambiently set in this dev
machine's shell once, unintentionally — worth checking `echo
$ANTHROPIC_API_KEY`/`$env:ANTHROPIC_API_KEY` isn't already set before
running anything that could silently skip a "key missing" path you meant
to test, or before running the release suite unintentionally against a
real key.

---

## Why one common approach

The project owner's own scoping call for this document was explicit:
one shared discipline, expressed identically in spirit across all four
platforms, varying only in which real tool executes it. That mirrors how
the Minor/Major/External model itself was already unified across all
four platforms in the root `TESTING.md` (see that file's "Event-based
tiers, not time-cadence tiers" section) — four independently-invented
methodologies would mean four things to remember and four places a
convention could quietly drift out of sync with the other three, exactly
the failure mode `test-vectors/*.json` and the inter-module interface
category already exist to prevent for shared business logic. Keeping TDD
itself as one discipline, not four, is the same reasoning applied one
level up: a developer moving between `tests/`, `web/`, `android/`, and
`workers/scan-proxy/` in the same session should have to relearn *tool
syntax*, never relearn *what disciplined test-first development means on
this project*.

## Status of this repo against this discipline

This file was written 2026-08-25, after nearly all of this repo's
existing code and tests. It's the same situation root `TESTING.md` was
already honest about for the Minor/Major/External model itself (see that
file's own "Status of this repo against the framework" section): almost
none of the work behind this codebase was written test-first. Most of it
was reactive — investigate a real photo/API/build failure, understand
what's actually happening, then write the test that locks the fix down —
not Red written before any code existed. The combinatorial-sweep bug fix
cited under "common discipline" rule 3 above is the representative
example, not an exception.

This file governs **going forward, not retroactively**. Existing code
and tests are not being rewritten to manufacture a test-first history
they don't have — CLAUDE.md's `TDD_METHODOLOGY.md` reference makes this
required for **new code and bug fixes from 2026-08-25 onward**. As with
Minor/Major/External, actually living by this every session is the real,
ongoing discipline — not a one-time box to check off here.
