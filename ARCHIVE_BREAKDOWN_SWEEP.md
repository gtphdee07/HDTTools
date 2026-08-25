# Archive: combinatorial sweep testing for compute_breakdown/verdict_for

New archive file, 2026-08-24 — split out as its own topic rather than
appended to `ARCHIVE_TESTING.md` (already past this project's own
800-1000 line split threshold). See `NEXT_STEPS.md` item #12 for current
status.

**Entry-tag convention** (for `Grep`-based lookup instead of reading this
whole file): entries lead with `✅ **Real bug`, `**Decided`, or similar
bold tags — grep for those to filter by type.

---

## ✅ Real bugs: structured combinatorial sweep found two crashes in shared breakdown math - closed 2026-08-24

Started from a real test-planning idea: the user wanted random/
combinatorial testing of the core towing-safety math
(`compute_breakdown`/`verdict_for` in `src/hdttools/api/breakdown.py`,
the single source of truth also hand-ported to Kotlin's
`Breakdown.kt`), including deliberately choosing extreme/bad-choice
combinations - something this project had never had (no `hypothesis` or
any property-based testing library, confirmed absent from dev deps and
every planning doc). **Decided: a structured sweep, not
`hypothesis`-driven fuzzing** - the interesting space here
(present/absent/zero/boundary combinations across truck/trailer/scale
fields, the three tongue-weight-estimate branches, `axle_count`/
`pin_weight_pct` overrides) is small and already enumerable by reading
the code, not continuous, so `itertools.product` over a deliberately
curated set of representative values per dimension is a better fit than
open-ended random generation.

**New test file**: `tests/test_breakdown_combinatorial_sweep.py`.
`itertools.product` over `TRUCK_VARIANTS` × `TRAILER_VARIANTS` ×
`SCALE_VARIANTS` × `PIN_WEIGHT_PCTS` = 378 combinations. Unlike the
existing hand-written tests (`tests/test_breakdown.py`) and golden
vectors (`tests/test_breakdown_golden_vectors.py`,
`test-vectors/breakdown_cases.json`), which assert exact expected
output for specific known scenarios, this sweep asserts *invariants*
that must hold for every combination: never raises, every row's `tone`
is a real enum member, `verdict_for`'s `status` is a real enum member,
`estimated` never leaks `true` on an `insufficient` row, `pct` stays in
`[0, 100]`.

**✅ Real bug #1: an explicit `0` rated limit crashed the whole
computation.** Found by direct code review while designing the sweep's
value dimensions, before the sweep even ran: `compute_breakdown`'s
per-row `insufficient` checks used `is None` only (e.g.
`front_gawr_raw is None`), not a truthy check - so a rated limit field
(`front_gawr_lb`, `rear_gawr_lb`, `gvwr_lb` on either truck or trailer,
`gawr_per_axle_lb`) explicitly set to `0` sailed through as "sufficient
data." That `0` then became the divisor computing `pct = min(100,
round((actual / limit) * 100))`, crashing with `ZeroDivisionError`
instead of ever reaching a graceful "Not enough info" - confirmed live
with `compute_breakdown({"front_gawr_lb": 0, ...}, {}, {...})`. This is
externally reachable, not just an internal-caller concern:
`BreakdownRequest.pin_weight_pct`/every field on `BreakdownRequest` in
`src/hdttools/api/schemas.py` has no Pydantic range/value constraint at
all, so a real `POST /api/breakdown` client could trigger this.
**Kotlin's `Breakdown.kt` had the identical `== null`-only check** in
`towVehicleInsufficient`/`trailerTotalInsufficient`/
`combinedInsufficient` and three per-row checks - it didn't crash (an
existing `if (row.limit > 0) ... else 0` guard on the division already
there), but would have silently reported a false `WARNING` ("over
limit") tone from the bogus zero instead of `INSUFFICIENT` - arguably
worse than crashing, since it's a wrong, undetected safety-relevant
answer with no indication anything was off.

**Fix (both platforms)**: treat an explicit `0` rated limit the same as
absent, matching the truthy-not-just-null convention this same function
already uses for `standalone_weight_lb`/`axle_count` (a real vehicle
can't have a 0 lb rating either). Python: changed the six `is None`
checks in `raw_items` to `not <raw_value>`. Kotlin: added a private
`Double?.isProvided()` extension (`this != null && this != 0.0`) and
used it in place of the `== null` checks. Regression tests added on
both platforms (`test_zero_rated_limit_is_treated_as_not_provided_not_crashed_on`
in `tests/test_breakdown.py`, `` `zero rated limit is treated as not
provided, not a false over-limit warning` `` in `BreakdownTest.kt`) plus
a new shared golden-vector case,
`zero_rated_limit_is_insufficient_not_a_crash`, in
`test-vectors/breakdown_cases.json`.

**✅ Real bug #2: `pin_weight_pct` of exactly `1.0` crashed the same
way.** Running the actual sweep (after fixing bug #1) surfaced this
one for real - 78 of the 378 combinations failed, every one at
`pct=1.0`. The axle-reading-estimate branch (used when a trailer-axle
scale reading exists but no stand-alone truck weight was entered)
divides by `1 - pin_weight_pct`:
`trailer_total_actual = trailer_axle / (1 - pin_weight_pct)`. A caller
passing `pin_weight_pct=1.0` (claiming 100% of the trailer's weight is
tongue weight - physically nonsensical, but nothing validates against
it) makes that divisor exactly `0`, crashing with `ZeroDivisionError` -
again reachable from `POST /api/breakdown` for real, since
`pin_weight_pct` has no Pydantic constraint either. **Kotlin's
identical division doesn't crash** (a `Double` divided by `0.0` yields
`Infinity`, not an exception) but silently propagates that `Infinity`
into `trailerTotalActual` and onward - same real bug, different failure
shape.

**A design nuance found while fixing this one**: an existing test,
`tests/test_api.py::test_breakdown_endpoint_pin_weight_pct_is_a_fraction_not_the_ui_percentage`,
*deliberately* asserts a **negative** result when a caller sends a
whole-number percentage (e.g. `15`) instead of the fraction (`0.15`) -
a real, pre-existing "fail loud and obviously, don't silently produce
something plausible-looking" design choice for a wrong-unit input. A
first attempt at this fix (`min(max(pin_weight_pct, 0.0), 0.99)`,
clamping the *entire* range) broke that test, since it also clamped
`15` down to `0.99` and turned the deliberately-obvious negative result
into a deceptively-plausible-looking large positive one. **Correct,
narrower fix**: only guard the literal `pin_weight_pct == 1.0` case
(snap it to `0.99`) - values genuinely above `1.0` are left completely
untouched, preserving the existing "obviously wrong" behavior on
purpose. Applied identically on both platforms (Python: a plain
`if pin_weight_pct == 1.0: pin_weight_pct = 0.99` guard at the top of
`compute_breakdown`; Kotlin: a `pinWeightPctSafe` local computed the
same way, used everywhere `pinWeightPct` previously was in the
tongue-weight math). Regression tests added on both platforms
(`test_pin_weight_pct_of_exactly_one_does_not_crash`,
`` `pin weight pct of exactly one does not produce Infinity` ``) plus a
second shared golden-vector case, `pin_weight_pct_of_one_does_not_crash`.

**Verification, in full.** Python: `uv run pytest -q` - 535 passed, 3
xfailed (pre-existing, unrelated OCR limitations), zero regressions;
the sweep itself (`tests/test_breakdown_combinatorial_sweep.py`) - 378
passed. Kotlin: `./gradlew test` - `BUILD SUCCESSFUL`; the golden
vectors test's own console output confirms `Golden vectors: 12/12 cases
fully supported by the current Kotlin port. Skipped:` (empty skip
list) - both new cases ran for real, not silently skipped.

**Scope decision**: the sweep test itself stays Python-only - it's an
internal-invariant check over `compute_breakdown`'s own input space, not
a named cross-platform contract, so it doesn't need (and wouldn't
meaningfully gain from) a Kotlin port the way individual golden-vector
cases do. Only the two *specific bugs* it found got promoted to the
shared `test-vectors/breakdown_cases.json` file, per this project's
existing convention (see `standalone_without_hitched_falls_back_to_axle_estimate`'s
own `_note` for the precedent this follows).
