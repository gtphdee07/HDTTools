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

## Agreed starting point — not yet started

1. **Design the pass-pool fixture schema.** Per-vehicle golden values +
   a marked "confirmed-passing" image pool, structured so a randomly
   resolved image can be mapped back to its golden values at test time.
   Python only. Zero new photos needed — `ExampleDocs/AddieTag.jpg`
   (truck) and `ExampleDocs/GooseTag.jpg` (trailer) are already real,
   already confirmed-passing under Tesseract today (per
   `tests/test_real_photo_ocr_accuracy.py`), and can prove the schema
   design before any new fixture-collection work happens.
2. **Build a minimal random-selection test mechanism** reading that
   schema — a real, working, small first version, not the full pool
   (which only has one image per vehicle today anyway).
3. Then, in dependency order: the fail-pool (parallel structure, once
   the pass-pool's shape is proven), the interface-contract suite
   (depends on both pools existing), manufacturer-diversity growth of
   both pools, and the Android inherit-vs-duplicate decision.

This was interrupted before entering Plan Mode for step 1 (a session
compaction intervened) — pick up a future session by starting there,
directly, rather than re-deriving the purpose/architecture discussion
above from scratch.
