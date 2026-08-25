# Real-photo OCR degradation testing + structured combinatorial math sweep

## Context

`ExampleDocs/F-150Tags/` contains 10 real photos of the same physical
Ford tow-vehicle weight tag ("The Blue Goose"), ranging from one clear
shot to several taken at bad angles/shadow/sun glare, plus a
`F-150Spec.txt` with the hand-transcribed ground truth (`GVWR: 7100 LB`,
`GAWR: 3525 LB` front, `REAR GAWR: 3800`) — confirmed against the actual
photographed tag, which prints the full `KG (LB)` pairing the parser
expects (`GVWR: 3221 KG (7100 LB)`, etc.), so this is a valid,
parser-compatible fixture set. This is new *in kind*, not just in
quantity: every existing `golden_fields.json` entry is one photo per
document; this is the first case of *many quality levels of the same
document*, enabling tests the existing fixtures can't:

- A real, numeric answer to "how much image-quality degradation can OCR
  actually tolerate," using the existing `xfail(strict=True)` pattern
  `tests/test_real_photo_ocr_accuracy.py` already has for known misreads.
- A genuinely new test layer this project has never had: what happens
  when OCR *completely* fails on a real (not synthetic) bad photo — does
  the app degrade gracefully to the same "Not Enough Information"
  handling as an explicit skip, or silently treat garbage as data?

Separately, `src/hdttools/api/breakdown.py`'s `compute_breakdown`/
`verdict_for` — the core towing-safety verdict logic — is tested today
only via ~30 hand-written examples plus 10 shared golden vectors
(`test-vectors/breakdown_cases.json`, cross-platform with Kotlin). No
`hypothesis` or any combinatorial/property-based testing exists yet
(confirmed absent from dev deps and from all planning docs) — a real,
previously-undiscussed gap, even though the code's own logic already
implies a well-understood combinatorial space (which of truck/trailer/
scale are present/absent/partial, `standalone_weight_lb` present/absent/
zero, three different tongue-weight-estimate branches, boundary values
sitting exactly at a GAWR/GVWR limit).

Decided this session: a **structured sweep** over that known space
(`itertools.product`, no new dependency) rather than `hypothesis`-driven
open-ended fuzzing — the interesting space is small and already
enumerable, not continuous.

## Goal

1. A `scans/{truck,trailer}/<vehicle-name>/` fixture convention for
   future multi-photo scans, starting with the F-150 set.
2. Real, empirical data on how OCR accuracy degrades across the 10 F-150
   photos, wired into the existing golden-fields/xfail pattern.
3. A new failure-path test proving a genuinely OCR-unreadable photo
   degrades to the same "Not Enough Information" verdict as an explicit
   skip, not silent bad data.
4. A full-flow test pairing the real F-150 truck tag with synthetic
   trailer/scale numbers, proving the whole app (not just the parser)
   handles a real photo correctly end-to-end.
5. A structured combinatorial sweep over `compute_breakdown`/
   `verdict_for`'s known interesting-value space, catching invariant
   violations (crashes, invalid enum values) that hand-written examples
   don't cover — with any real bug found promoted to a permanent,
   cross-platform-shared case.

## Steps

### OCR track

1. **Move the fixture folder**: `ExampleDocs/F-150Tags/` →
   `ExampleDocs/scans/truck/f150/` (10 `.jpg` files + `F-150Spec.txt`,
   kept as human-readable provenance alongside the machine-readable
   ground truth in `golden_fields.json`). Nothing else needs touching —
   confirmed `tests/test_real_photo_ocr_accuracy.py:68` builds photo
   paths via a plain `_EXAMPLE_DOCS / filename` pathlib join, so a
   nested relative-path string as the JSON key (e.g.
   `"scans/truck/f150/20260824_141530.jpg"`) works with zero code
   changes. `AddieTag.jpg`/`GooseTag.jpg`/`CatScale-*.jpg` stay exactly
   where they are (top-level `ExampleDocs/`) — not moved, per this
   session's decision, since they're referenced from `golden_fields.json`,
   three test files, an Android instrumented-test asset copy, and two
   other product lines' `TESTING.md` files.

2. **Add all 10 photos to `golden_fields.json`'s `"photos"` section**,
   each with `doc_type: "truck_tag"` and the same three ground-truth
   values (`manufacturer: "FORD MOTOR CO"`, `gvwr_lb: 7100.0`,
   `front_gawr_lb: 3525.0`, `rear_gawr_lb: 3800.0`) — confirmed correct
   against the real photographed tag, not just the spec.txt transcription.

3. **Run the real OCR pipeline against all 10 photos** (the same
   non-interactive call sequence `test_real_photo_ocr_accuracy.py`
   already uses: `ocr_common.open_image`/`preprocess_image`/`ocr_text`
   then `truck_tag_ocr._parse_fields`) to determine, empirically, which
   photos misread which field. For each real misread, add a
   `known_ocr_limitations` entry with the real reason, matching the
   existing pattern exactly (e.g. `GooseTag.jpg`'s digit-drop note).
   This step **must run for real** — the failure-path test in step 4
   depends on knowing which photo, if any, is a genuine total failure
   (all three fields unusable), not a guess.

4. **Add a failure-path test** for whichever photo step 3 identifies as
   a total failure (if any is — if all 10 photos produce at least
   partial real output, this step is skipped and noted as such, not
   forced). New test confirming that when `truck_tag_ocr`'s real parse
   of that photo returns empty/unusable fields, `compute_breakdown`
   given that empty dict reaches the *same* code path already proven in
   `tests/test_breakdown.py::test_blank_rig_reports_not_enough_information_not_a_false_pass`
   (`compute_breakdown({}, {}, {})` → every row `insufficient`, verdict
   `status: "insufficient"`, headline `"Not Enough Information"`) — i.e.
   prove a *real* OCR failure funnels into the *already-tested* blank-rig
   path, rather than writing new breakdown-logic assertions from scratch.

5. **Add a full-flow test**: the real F-150 truck photo (via real OCR,
   not golden-fields lookup) paired with hand-constructed, synthetic
   trailer/scale dicts (not real photos), run through the same pattern
   `tests/test_streamlit_app.py::test_full_walkthrough_with_real_photos_reaches_a_real_verdict`
   uses, confirming a real, correct verdict. This does **not** go into
   `golden_fields.json`'s `"rigs"` array — that array's own docstring
   states rigs are real, physically-weighed-together events, not an
   assumed-compatible mix of independently-real photos, and a synthetic
   trailer/scale pairing would violate that invariant. Instead: a
   small, clearly-named standalone test with the synthetic values
   defined directly in test code.

### Math track

6. **New test file** `tests/test_breakdown_combinatorial_sweep.py`.
   `itertools.product` over the known interesting-value dimensions
   already present in `compute_breakdown`/`verdict_for`
   (`src/hdttools/api/breakdown.py`):
   - truck/trailer/scale dicts: present (realistic values) / empty `{}`
   - `standalone_weight_lb`: present-positive / present-zero (the
     existing truthiness quirk, line ~72) / absent
   - the three tongue-weight-estimate branches: hitched+standalone
     present, axle-reading-only estimate, no-scale-data GVWR fallback
   - `axle_count` and `pin_weight_pct`: default vs. custom (including
     extreme `pin_weight_pct` values like `0.0` and `1.0` to probe the
     `max(0.0, ...)` tongue-weight clamp at line 82 and the `min(100,
     ...)` pct cap at line 207)
   - boundary values: `actual` exactly equal to `limit` (0% over/under
     edge)

   For every generated combination, assert real invariants (not exact
   values — this is a sweep, not a golden-vector file):
   - `compute_breakdown`/`verdict_for` never raises
   - every row's `tone` is one of `{success, warning, insufficient}`
   - `verdict_for`'s `status` is one of `{pass, fail, partial,
     insufficient}`
   - `estimated` is never `true` on an `insufficient` row (already a
     hand-tested property for one case — the sweep checks it holds
     across the whole generated space)
   - `pct` is never negative and never exceeds 100

7. **Promote any real bug the sweep finds** to a new named case in
   `test-vectors/breakdown_cases.json` (the file already shared
   cross-platform with `BreakdownGoldenVectorTest.kt`), with a
   descriptive name and comment — matching how this project already
   turns a found-by-tooling issue into a permanent regression case,
   rather than just leaving it living inside the sweep. The
   Python-only sweep itself does **not** get a Kotlin port — it's an
   internal-invariant check, not a named cross-platform contract; only
   promoted individual cases are cross-platform.

## Files

- `ExampleDocs/scans/truck/f150/` (moved from `ExampleDocs/F-150Tags/`)
- `ExampleDocs/golden_fields.json` — 10 new `"photos"` entries
- `tests/test_real_photo_ocr_accuracy.py` — no code change needed (data-driven)
- New test(s) in/near `tests/test_streamlit_app.py` or a new file —
  failure-path test + full-flow synthetic-pairing test
- `tests/test_breakdown_combinatorial_sweep.py` (new)
- `test-vectors/breakdown_cases.json` — only if the sweep finds a real bug

## Definition of Done

- All 10 F-150 photos live under `ExampleDocs/scans/truck/f150/`, wired
  into `golden_fields.json` with real (not assumed) per-field pass/fail
  data from an actual OCR run.
- The failure-path test exists and passes *if* a genuine total-failure
  photo exists in the set; otherwise this is explicitly noted as
  not-applicable with the real reason (e.g. "all 10 photos produced at
  least partial output").
- The full-flow synthetic-pairing test passes for real, reaching a real
  verdict.
- The combinatorial sweep runs clean (or any real finding is promoted to
  a permanent golden-vector case, not left as a silently-passing
  workaround).
- Full existing Python suite still passes (`uv run pytest -q`).

## Verification

1. `uv run pytest -q tests/test_real_photo_ocr_accuracy.py -v` — real
   per-photo, per-field results read directly, not assumed.
2. `uv run pytest -q tests/test_breakdown_combinatorial_sweep.py -v`
3. `uv run pytest -q` — full suite, confirm no regressions from the
   fixture move or new tests.
4. Read back `golden_fields.json`'s new entries and any promoted
   `test-vectors/breakdown_cases.json` case to confirm they're real,
   accurate, and match this project's existing documentation
   conventions (`known_ocr_limitations` reasons, named-case comments).
