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
doesn't have. First run that day found real drift (4 of 9 cases
supported, including a live bug — see `NEXT_STEPS.md` for that writeup);
by the end of the same day's follow-up work, the Kotlin port had gained
every missing capability and this file reports **10 of 10 cases fully
supported** — full parity with Python.

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

## Reconciling with per-platform network/cadence tiers

`android/TESTING.md` and `workers/scan-proxy/TESTING.md` each describe
their own tiers (Android: Unit/Daily/Weekly; scan-proxy: Sanity/Daily/
Weekly/Release) — an earlier scheme, built before Minor/Major existed.
These are **not competing schemes to pick between** — they answer two
different questions, on two independent axes, and both stay in force:

- **Minor/Major (this file)** answers *which test categories to run*,
  scoped to *what a specific change touched*, decided fresh each session
  against the real diff.
- **Sanity/Daily/Weekly/Release** answers *which network-dependency tier*
  a test belongs to — offline/mocked vs. real-but-bounded vs. real
  against a live deployment — and *how often* that tier's real-world
  exposure gets exercised. That classification doesn't change session to
  session; it's a property of the test itself (does it touch a real
  network boundary or not), not of whatever diff prompted running it.

**How they compose**: Minor/Major only ever governs the tiers that are
already offline/mocked — for Android that's Unit (JVM) + Daily
(instrumented, no `Purchases.configure()`); for scan-proxy that's Sanity
+ Daily (both mocked, no real network). Concretely:

- Android: a **Minor** change to a module runs that module's function and
  interaction tests within Unit (JVM). A **Major** change runs the full
  offline suite for that module — Unit (JVM) *and* Daily (instrumented) —
  plus, if the change touches a shared interface, the other module's
  Major suite and the golden-vector/interface tests (category 4).
- `scan-proxy`: a **Minor** change runs that module's `[sanity]`-tagged
  cases. A **Major** change runs the module's full `npm test` (the Daily
  tier, which sanity is already a tagged subset of — the two tiers were
  never separate test suites, just a fast/full split of the same one).

The **real-network tiers** — Android's Weekly, scan-proxy's Weekly and
Release — sit outside Minor/Major entirely. None of them run on a fixed
calendar cadence despite the "Weekly" name, clarified 2026-08-21:
scan-proxy's Weekly tier is just cheap enough to run anytime, ad hoc, no
enforced schedule; Release (scan-proxy's and Android's, see each
platform's own `TESTING.md` for how those two differ) is gated on a real
decision — pushing a major update to the Play Store — not a clock. What
they all guard against is the same regardless of trigger: a live
API/credential/environment integration failure isn't something a
session's diff scope can predict or bound. A purely-internal Minor
change and a sprawling Major one are equally unrelated to whether, say,
RevenueCat's real sandbox still behaves as expected; that only degrades
on its own schedule, external to any code change here — which is
exactly why these tiers are triggered by real-world events (a release
decision, or just "enough time/uncertainty has passed to check") rather
than folded into the diff-driven Minor/Major rules above.

**In short**: read `android/TESTING.md`/`scan-proxy/TESTING.md`'s tier
tables for *what network access a test needs and how often to run it at
all*; read this file's Minor/Major rules for *which of those (already
network-tiered) tests a specific session's change actually calls for*.
Neither file's scheme needs to change to make room for the other.

## Status of this repo against the framework

This framework was defined 2026-08-20, after most of this repo's existing
tests were already written — they haven't been retroactively categorized
against it, and the framework hasn't yet been applied as an actual
per-session discipline. Reconciling the sanity/daily/weekly/release tiers
with Minor/Major (immediately above) closes that specific gap as of
2026-08-21; applying Minor/Major as a lived per-session discipline going
forward is a separate, ongoing thing to keep honest, not a one-time task.
