# Pass-pool regression test: real Tesseract against a randomly-resolved image

## Context

Item #13 (`NEXT_STEPS.md`, full design in
`FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md`) is the constrained-random
OCR testing architecture. Steps 1-2 of its agreed starting point are
already done this session: `ExampleDocs/golden_fields.json` has a
`pass_pool` section grouping real photos by vehicle per doc_type, and
`scripts/pass_pool.py`'s `resolve_pass_pool_image(doc_type, rng=None)`
picks one registered image at random and returns its golden-truth
`"photos"` entry (fields + any `known_ocr_limitations`, carried through
rather than stripped).

Nothing calls that resolver against real OCR yet — `tests/test_pass_pool.py`
only proves the schema/resolver mechanics with seeded RNGs, no image
decoding involved. The next step is the actual regression test: run
real Tesseract against whichever image the resolver picks, and prove
the app's real extraction still behaves the way `golden_fields.json`
says it should. A failure here is the signal item #13 exists to produce
— a real change in the extraction API (Tesseract itself, `ocr_common.py`,
or a `*_ocr.py` parser), not an accuracy-tuning question, since every
pool member's exact behavior (including its documented limitations) is
already known before it's added to the pool.

## Goal

A real, passing regression test that resolves a random pass-pool image
per doc_type, runs it through the real OCR pipeline, and asserts
extraction still matches the documented golden state — flagging as a
failure both a new mismatch (a real regression) and an unexpected match
on a previously-limited field (a real improvement worth documenting),
per item #13's own stated goal: "detect any change in extraction
performance, better or worse."

## Steps

1. **New test file `tests/test_pass_pool_regression.py`**, parametrized
   over `doc_type` values read dynamically from `golden_fields.json`'s
   `pass_pool` section (skipping the `_readme` key) — same
   "no new test code needed when the pool grows" philosophy
   `tests/test_real_photo_ocr_accuracy.py` already uses for `"photos"`.
   Today this yields two parametrized cases: `truck_tag`, `trailer_tag`.

2. **Per doc_type, the test**:
   - Calls `pass_pool.resolve_pass_pool_image(doc_type)` with an
     **unseeded** `random.Random()` (real randomness — "different
     answers back... versus the same ones, all the time" was the
     project owner's own framing for why this can't be a fixed pick).
   - Runs the same real pipeline `test_real_photo_ocr_accuracy.py`
     already uses: `ensure_tesseract_configured()` →
     `open_image()`/`preprocess_image()`/`ocr_text()` → the doc_type's
     `_parse_fields` (a small local `doc_type -> parser` dict,
     duplicating that file's private `_PARSERS` rather than importing
     a leading-underscore name across test modules).
   - Computes `mismatched = {field for field, expected in
     photo["fields"].items() if extracted.get(field) != expected}`.
   - Asserts `mismatched == set(photo.get("known_ocr_limitations", {}))`
     — the single invariant that catches both directions of drift, with
     a failure message naming the resolved filename and both sets so a
     real failure is immediately actionable.

3. **Update `NEXT_STEPS.md` item #13** and
   `FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md`'s step-3 list to move "an
   actual pass-pool regression test" from not-started to done, noting
   real Tesseract was actually run (not assumed) and it passed cleanly
   against both current pool members.

## Definition of Done

- `tests/test_pass_pool_regression.py` exists, passes for real against
  real Tesseract (not mocked), for both currently-registered doc_types.
- Running it repeatedly (unseeded random pick) stays green — today
  trivially true since each doc_type has exactly one pool image, but
  the mechanism is exercised for real, not just proven on paper.
- Full suite (`uv run pytest -q`) still passes, no regressions.
- `NEXT_STEPS.md` / `FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md` reflect
  the real state: pass-pool schema, resolver, and now the first real
  regression test all done; fail-pool/interface-contract suite still
  open.

## Verification

1. `uv run pytest -q tests/test_pass_pool_regression.py -v` — read the
   real per-doc_type result, confirm it actually invoked Tesseract
   (not a cached/mocked path).
2. `uv run pytest -q` — full suite, confirm no regressions.
3. Manually re-run step 1 a few times to confirm the random pick path
   executes without flakiness (even though today it always resolves to
   the same single image per doc_type).
