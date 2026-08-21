# Future work: Pydantic JSON-Schema export for cross-language contract validation

Not started. Written 2026-08-21 as a parking spot for "Option C" from the
`web/` API-shape-drift discussion, so the idea survives without living in
daily context. Indexed from `web/TESTING.md`'s known gaps and the root
`TESTING.md`'s cross-platform section — if you're reading this cold,
those two files have the surrounding context this one assumes.

## The problem this would solve

`web/`'s test suite (and, to a lesser extent, `android/`'s) works from
hand-written fixtures that describe what the real Python API returns —
`web/src/types.ts`'s interfaces, and every test's `mockFetchOk(...)`/
fake-prop object. Nothing derives those fixtures *from* `src/hdttools/api/schemas.py`'s
actual Pydantic models; a human keeps them in sync by hand. A field
rename, drop, or type change in `schemas.py` would go completely
uncaught by every test in `web/` — they'd all stay green, because none
of them touch real Python output.

**Option B** (built 2026-08-21, see `NEXT_STEPS.md` for that writeup)
closes this for `BreakdownItemOut`/`VerdictOut` specifically, via a
shared key-list fixture (`test-vectors/breakdown_response_shape_contract.json`)
that a real Python test and a Web type-literal test both check against.
It's a manually-synced tripwire: change the real shape, the shared file
goes stale, one side's test fails, a human updates the file and both
sides' code together. That's proportionate for two response shapes, but
doesn't scale cleanly to `TruckTagOut`/`TrailerTagOut`/`ScaleTicketOut`
(and their nested `TireSpecOut`) without three more hand-maintained
fixture files, each needing the same manual-sync discipline.

**Option C** is the version that doesn't need manual syncing: export the
*real* Pydantic schema, and validate everything else against that export
directly, so there's nothing left to hand-maintain.

## What "done" looks like

1. A generation step (script or a `uv run` command) that calls
   `.model_json_schema()` on each response model FastAPI actually returns
   — at minimum `BreakdownItemOut`, `VerdictOut`, `TruckTagOut`,
   `TrailerTagOut`, `ScaleTicketOut` (and confirm whether `TireSpecOut`
   needs its own file or comes along fine as a nested `$ref` inside the
   parent schemas — Pydantic v2 usually inlines nested models as
   `$defs`/`$ref`, which should be fine, but verify the emitted schema
   is actually usable standalone by whatever Web validates against it).
2. Those schemas get written to disk somewhere shared/version-controlled
   — `test-vectors/schemas/*.schema.json` fits this repo's existing
   `test-vectors/` convention best.
3. **A staleness check, not just a generator.** The exported files need
   to be checked into git AND proven current — a Python test that
   regenerates each schema in memory and asserts it matches the checked-in
   file byte-for-byte (or as parsed JSON) is the cheapest way to guarantee
   the committed schema never silently drifts from the real models. Without
   this check, Option C degrades into the same "someone has to remember"
   problem Option B already has, just with an extra manual step (re-run
   the generator) instead of zero.
4. On the Web side: pick a JSON Schema validator (`ajv` is the standard
   choice, MIT-licensed, no backend dependency) as a new devDependency,
   and write tests that validate the actual fixture objects used
   elsewhere in the suite (`RESULT` in `App.interaction.test.tsx`, the
   `item()` helper in `ResultsStep.test.tsx`, `mockFetchOk(...)` bodies in
   `api.test.ts`) against the corresponding exported schema file — real
   JSON Schema validation (required fields, types, enums), not just a
   key-set comparison the way Option B's tripwire test does it.

## Open decisions to make when this is actually picked up

- **Full JSON Schema validation vs. key-set comparison.** Full validation
  (via `ajv`) catches type mismatches (a field that's a string in the
  schema but a number in a fixture) that a bare key-set check can't —
  probably worth the extra dependency once there's more than one or two
  shapes to check, which is exactly the scaling problem Option C exists
  to solve.
- **Schema draft version compatibility.** Confirm which JSON Schema draft
  Pydantic v2's `.model_json_schema()` emits by default (it targets
  2020-12-compatible output) actually validates cleanly under whatever
  `ajv` version gets installed — `ajv` needs draft-2020-12 support
  (`ajv/dist/2020` in some versions) or the schemas may need
  `dialect`/`$schema` adjustment before Web can consume them.
- **Automatic regeneration vs. a manual command.** Whether the export
  step runs as part of `uv run pytest` itself (e.g., a session-scoped
  fixture that regenerates and diffs) or stays a separate command a human
  runs occasionally and the staleness-check test just fails loudly when
  it's out of date. Leaning toward the latter — matches this repo's "no
  CI, everything run manually" model (see `workers/scan-proxy/TESTING.md`)
  better than a step baked silently into every test run.
- **Where the generator itself lives** — a small standalone script under
  `src/hdttools/api/` (e.g. `export_schemas.py`), not a pytest fixture
  with side effects, so it can be run and inspected independently of the
  test suite.

## When to actually build this

Only if field drift on this boundary becomes a recurring real problem —
Option B already covers the two highest-traffic shapes
(`BreakdownItemOut`/`VerdictOut`) with meaningfully less machinery. Build
this when either (a) the `TruckTagOut`/`TrailerTagOut`/`ScaleTicketOut`
boundary actually breaks from drift the way `BreakdownItemOut` risked
doing, or (b) hand-maintaining a fourth or fifth Option-B-style fixture
file starts feeling like the wrong tradeoff on its own merits.
