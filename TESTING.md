# RigCheck — testing methodology

This defines the test categories and regression-scoping rules used across
the whole repo (Python backend, Web, Streamlit, Android, `scan-proxy`).
Decided 2026-08-20 — see `NEXT_STEPS.md`'s tiered-test-strategy section
for the narrative history of how this was arrived at. Platform-specific
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
  inter-module interface tests between them (category 4).
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
`tests/test_breakdown_golden_vectors.py` (Python) and
`android/.../domain/BreakdownGoldenVectorTest.kt` (Kotlin). Each case
declares a `requires` list of capabilities it depends on; Kotlin's runner
skips (not silently passes) any case needing something its current port
doesn't have — running it today reports **4 of 9 cases fully supported**,
the rest skipped by name (adjustable pin-weight %, insufficient/partial
verdict tiers, the GVWR-fallback and predictive-estimate branches — none
of the 2026-08-19–2026-08-20 feature arc made it to Kotlin). One more
case, deliberately unskipped, proved something worse than a missing
feature: Kotlin's existing standalone-weight branch has the *same real
bug* fixed in Python this session (no check that a real hitched reading
exists before using it) — that case fails on purpose,
`expected:<14225> but was:<11380>`, an honest, reproducible proof the bug
is live on the shipped Android app. See `NEXT_STEPS.md` for the full
writeup. Porting the missing features/fixing the bug in Kotlin itself is
separate, not-yet-started work — this only built the mechanism that makes
the gap visible and testable.

## Status of this repo against the framework

This framework was defined 2026-08-20, after most of this repo's existing
tests were already written — they haven't been retroactively categorized
against it, and the framework hasn't yet been applied as an actual
per-session discipline. `android/TESTING.md` and `workers/scan-proxy/TESTING.md`
still describe their sanity/daily/weekly/release tiers (a different,
earlier scheme) — reconciling those with Minor/Major here is unstarted,
tracked in `NEXT_STEPS.md`'s tiered-test-strategy section, not done
silently by this file existing.
