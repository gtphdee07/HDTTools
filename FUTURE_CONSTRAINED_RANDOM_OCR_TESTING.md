# Future: constrained-random real-image regression testing for OCR/vision extraction

Written 2026-08-25. Parked-topic doc, same shape as
`FUTURE_API_SCHEMA_VALIDATION.md` — a design worked out in full, not yet
built. See `NEXT_STEPS.md` item #13 for current status.

## How this started

Item #11's F-150 investigation (`ARCHIVE_WEB_STREAMLIT.md`) found two
real, different-shaped OCR gaps using 10 real photos of one physical
tag. Item #12's combinatorial sweep (`ARCHIVE_BREAKDOWN_SWEEP.md`) then
proved that a *structured, non-hand-written* test approach — generate
many cases from a small set of representative dimensions, assert
invariants rather than exact values — finds real bugs hand-written
examples miss. This doc is what happens when the project owner (a
hardware/RTL verification engineer by background — see this repo's
`user_verification_engineering_background` framing) asked to apply the
same *constrained-random* discipline to real-image OCR testing
specifically, rather than to `compute_breakdown`'s pure math.

## The purpose question, answered first

The wrong framing: "add more OCR accuracy testing with more images."
That question is already answered by item #11 — Tesseract fails on raw
photos regardless of quality (a framing/no-crop gap, not an accuracy
one); Claude vision is robust to angle/rotation but not to a photo that
literally excludes the needed text. More images of the same F-150 tag,
in the same style, wouldn't add new information to that finding.

**The right framing**, arrived at through direct discussion: prove the
app's verdict logic holds up across *real/manual source combinations*,
using a small constrained-random matrix instead of hand-written
one-offs — not "is this specific case still right" (what golden vectors
already do) but "does the app hold up across a much larger space than
anyone would hand-write." This is an Interaction/integration-level
question, not a Function-level one, in this repo's own `TESTING.md`
taxonomy.

## Three architecture pieces (all designed, none built)

### 1. Pass-pool — random selection with resolvable golden truth

Per real vehicle: one golden-value set, plus a marked pool of
confirmed-legible real images that all share it. At test execution
time, randomly select one (or N) images per component (truck/trailer/
scale) from the pool, resolve the golden values for whichever got
picked, and assert real extraction matches.

- **Only images already known to pass go in this pool.** A failure here
  therefore means a real regression in the extraction API itself
  (the Tesseract call, or the Claude vision call) — not an
  accuracy-tuning signal, since accuracy was already confirmed for every
  image in the pool before it was added.
- **"Different answers back from tests, not the same ones every time"**
  was the project owner's own framing for why this needs to be
  *random* at execution time, not a fixed enumerated list like the
  existing golden-vector pattern — the point is exercising more of the
  space than a fixed set of hand-picked cases would, run after run.
- **Concrete build gap this creates**: `ExampleDocs/golden_fields.json`'s
  current schema is one photo → one set of expected field values. It
  has no notion of "N interchangeable images sharing one truth,
  resolvable after a random pick." This is the actual first thing to
  design (see "Agreed starting point" below) — not a re-application of
  the F-150 `photos` entries tried and reverted in item #11's own
  investigation (that shape doesn't fit this need either; see that
  item's narrative for why the per-field-xfail pattern didn't work for
  a "whole document fails identically" case, a related but different
  problem).

### 2. Fail-pool — known-bad images testing the failure path itself

A separate, parallel pool: known-illegible images, each carrying an
expected *failure signature* — which fields should come back empty/
`None`, and that the app correctly reaches the "Not Enough Information"/
manual-entry path — rather than a golden value to match.

- Generalizes the single already-deferred "failure-path test" idea from
  item #11's original plan (confirm a real OCR failure funnels into the
  same blank-rig/insufficient path `tests/test_breakdown.py`'s
  `test_blank_rig_reports_not_enough_information_not_a_false_pass`
  already proves) into a repeatable, growable regression category,
  rather than a single one-off test.
- A photo in this pool returning something *other than* its recorded
  expected failure shape is the same class of signal as the pass-pool's
  failure: a real regression, this time in the failure-handling path
  specifically (e.g. the app starts silently accepting garbage OCR
  output as real data, instead of degrading gracefully).

### 3. Interface-contract suite — runs both pools, triggered manually

A dedicated regression suite (distinct from scan-proxy/Android's
existing External suites, which test billing/API *mechanics* — does a
real scan succeed, does credit spending work — not extraction
*correctness*) that runs both pools together. Its stated goal: detect
any change in extraction performance, better or worse, when something
external to this codebase changes underneath it.

## Scoping decision: manual trigger only, no automation (2026-08-25)

Explicit, direct decision from the project owner: *"I don't expect to
develop the hooks to auto recognize a dependency change and autorun the
regression script. I just need a set of script commands that I can
manually run when I need to test different parts of the design, based
on changes. I can be the event trigger, for now."*

This removes an entire category of work that was briefly on the table
(a Tesseract-version-recording/comparison mechanism, CI hooks, automated
drift detection). What's actually needed is much smaller: a documented
set of real, copy-pasteable commands (matching `DEV_ENVIRONMENT.md`'s
existing style) that the project owner runs by hand — one for the
pass-pool regression, one for the fail-pool regression, maybe a combined
"run both, this is the dependency-upgrade check" command.

**Tesseract's version is already directly checkable, no new tooling
needed**: confirmed live, 2026-08-25 —

```bash
"/c/Program Files/Tesseract-OCR/tesseract.exe" --version
```

```
tesseract v5.5.3.20260724
 leptonica-1.87.0
 ...
```

(bare `tesseract` is not on PATH, same situation as `adb` — see
`DEV_ENVIRONMENT.md`). That's sufficient as a manual before/after
comparison; no recording mechanism is needed since nothing auto-triggers
on it.

## Real correction: `claude-sonnet-5` needs no dated-snapshot pin

Earlier in the same conversation that produced this design, an
incorrect claim was made: that `src/hdttools/vision_client.py`'s
`DEFAULT_MODEL = "claude-sonnet-5"` was a "rolling alias" that could
silently drift to different underlying-model behavior, unlike
`workers/scan-proxy/src/claude.ts`'s dated
`"claude-haiku-4-5-20251001"` — reasoning purely by pattern-matching
against the *older* generation's naming convention, not verified.

**Verified for real, 2026-08-25**, via a live call to Anthropic's own
`/v1/models` endpoint:

```
claude-opus-5, claude-sonnet-5, claude-fable-5                 (no date)
claude-opus-4-8, claude-opus-4-7, claude-sonnet-4-6, claude-opus-4-6  (no date)
claude-opus-4-5-20251101, claude-haiku-4-5-20251001,
claude-sonnet-4-5-20250929                                     (dated)
```

The current model generation (5.x, and recent 4.x point releases) has
**no dated-snapshot variant at all** — dated IDs only exist for already-
*superseded* generations, apparently added once each was frozen in place
by a successor. `vision_client.py`'s bare `"claude-sonnet-5"` is
therefore already the correct, most-specific identifier available; there
is no more-pinned alternative to switch to, and no code change is
needed here.

**The real risk shape for the current generation is different than
originally assumed**: not silent behavioral drift under a stable-looking
ID, but a hard deprecation error once `claude-sonnet-5` is eventually
retired for a successor — calls would start failing outright, forcing a
visible, unmissable upgrade decision rather than a silent one. Arguably
a *better* failure mode for the project owner's stated goal ("know if I
can move to it, or need to stay back-revved") than what a rolling alias
would have produced — you cannot miss a hard error the way you could
miss silent drift.

## Manufacturer/format diversity priority

Both pools should grow across manufacturers — the motivating example
raised directly was a hypothetical Chevy label — not just more angles of
the same Ford F-150 tag. `NEXT_STEPS.md`'s own pre-existing "Natural next
steps" section already flags this exact gap: only one truck manufacturer
(Ford) and one trailer manufacturer (Brinkley RV) have ever been tested.
Format generalization, not image-quality robustness, is what an external
dependency version bump actually risks breaking — the "Chevy label"
scenario is a format question, not an angle/lighting one.

## Cross-platform scope — open question, not yet decided

Claude vision itself isn't platform-specific — Python's `vision_client.py`
and Android's scan feature (via `workers/scan-proxy`) both call the same
kind of prompt/schema against the same model family. Android already has
one real Claude-vision test today (`realScanDecrementsBalance`, sending a
real base64-encoded `AddieTag.jpg` through the real deployed Worker).
Building the pass-pool/fail-pool in Python first likely answers "does
the model handle diverse real photos" for Android's scan feature too,
without needing to duplicate real API spend on both platforms for the
same underlying question — unless Android's own image-encoding/
downscaling path (`PhotoEncoding.kt`) is independently suspected to
matter. Not resolved; revisit once Python's version exists to compare
against.

## Agreed starting point

1. ✅ **Done, 2026-08-25 — pass-pool fixture schema.**
   `ExampleDocs/golden_fields.json` gained a `pass_pool` section: doc_type
   → list of `{vehicle, images}` groups, where every filename must already
   have a `"photos"` entry with a matching doc_type. Deliberately a
   *membership index*, not a second copy of field data — the resolver
   looks the filename back up in `"photos"` at resolve time, so golden
   values live in exactly one place. Today: `truck_tag` → `f150_blue_goose`
   → `["AddieTag.jpg"]`; `trailer_tag` → `brinkley_goose` →
   `["GooseTag.jpg"]`. `scale_ticket` deliberately not populated yet — a
   scale ticket is a weighing *event* tied to one specific truck+trailer
   pairing (see `golden_fields.json`'s own `"rigs"` docstring), not a
   persistent physical tag the way a truck/trailer tag is, so "group by
   vehicle" doesn't map cleanly yet; left for when the fail-pool/
   interface-contract work actually needs a scale entry.
   One real design decision resolved along the way: `GooseTag.jpg` has a
   known digit-drop limitation on one field (`gawr_per_axle_lb`), so it
   isn't a *perfect* real-OCR match — included anyway, since the
   resolver returns the image's full `"photos"` entry (fields *and* any
   `known_ocr_limitations`), letting a future pass-pool test xfail that
   one field the same way `tests/test_real_photo_ocr_accuracy.py`
   already does, rather than requiring pool membership to mean
   zero-limitation.
2. ✅ **Done, 2026-08-25 — minimal random-selection mechanism.**
   `scripts/pass_pool.py`'s `resolve_pass_pool_image(doc_type,
   rng=None)` — a standalone module (like `scripts/coverage_lib.py`),
   not part of the `hdttools` app package, since this is test
   infrastructure, not application code. Takes an optional seeded
   `random.Random` for deterministic tests; an unseeded call is what a
   real pass-pool regression test would use to get "different answers
   back... versus the same ones, all the time." TDD'd in
   `tests/test_pass_pool.py` — written first, watched fail for real
   (`ModuleNotFoundError: No module named 'pass_pool'`), then made to
   pass. Full suite (`uv run pytest -q`) confirmed clean afterward:
   539 passed, 3 xfailed.
3. ✅ **Done, 2026-08-25 — the first real pass-pool regression test.**
   `tests/test_pass_pool_regression.py`, parametrized over `doc_type`
   (read dynamically from `golden_fields.json`'s `pass_pool` keys, so a
   new doc_type needs no new test code). Per doc_type: resolves one
   image with an **unseeded** `random.Random()` (real randomness, not
   the seeded determinism `test_pass_pool.py` uses to keep its own
   assertions stable), runs it through the real Tesseract pipeline, and
   asserts `mismatched fields == documented known_ocr_limitations` —
   one invariant that flags both directions of drift: a new mismatch is
   a real regression, a previously-limited field suddenly matching is a
   real improvement worth updating `golden_fields.json` for. Run
   several times for real to rule out flakiness in the random-pick path
   (today trivially stable, since each doc_type has exactly one pool
   image) — passed clean every time; full suite (`uv run pytest -q`)
   also clean, 541 passed / 3 xfailed.
4. ✅ **Done, 2026-08-25 — the fail-pool.** Reuses item #11's 10 F-150
   photos (still on disk at `ExampleDocs/scans/truck/f150/`, never
   re-added to `"photos"` — see that item's "document, don't build"
   finding: all 10 fail identically for one structural reason, not a
   per-field quirk `"photos"`/`known_ocr_limitations` was designed
   for). New self-contained `fail_pool` section in `golden_fields.json`
   (no reference into `"photos"` needed, unlike `pass_pool` — the
   golden truth here *is* the failure signature: `expected_none_fields:
   ["manufacturer", "gvwr_lb", "front_gawr_lb", "rear_gawr_lb"]`,
   confirmed for real against all 10 photos, not assumed).
   `scripts/fail_pool.py`'s `resolve_fail_pool_image` mirrors
   `pass_pool.py`'s shape exactly. `tests/test_fail_pool_regression.py`
   TDD'd (watched fail with `ModuleNotFoundError` before the module
   existed), and proves two things: the `None` signature still holds
   under real Tesseract, and it still funnels into
   `compute_breakdown`/`verdict_for`'s real `"insufficient"`/"Not
   Enough Information" path — generalizing
   `test_blank_rig_reports_not_enough_information_not_a_false_pass`'s
   hand-written `{}` case to a real garbled-OCR photo, per this doc's
   own fail-pool design above. Re-run 5x to confirm stability across
   different random picks from the 10-image pool (a real exercise of
   the multi-image-per-vehicle case the pass-pool's schema supports but
   doesn't yet have real data for); full suite clean, 543 passed / 3
   xfailed.
5. **Not yet started, in dependency order**:
   - The interface-contract suite (depends on both pools existing —
     both now do).
   - Manufacturer-diversity growth of both pools (both cover only the
     Ford/Brinkley pairing today).
   - The Android inherit-vs-duplicate decision (still open, see above).
