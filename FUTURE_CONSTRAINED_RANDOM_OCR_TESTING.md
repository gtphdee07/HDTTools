# Future: constrained-random real-image regression testing for OCR/vision extraction

Written 2026-08-25, originally a parked-topic doc in the same shape as
`FUTURE_API_SCHEMA_VALIDATION.md` (a design worked out in full, not yet
built) — **updated same day**: most of this design is now built and
verified for real (pass-pool, fail-pool, interface-contract suite,
directory-convention auto-discovery, and Android's own duplicate
pass-pool/fail-pool — see the "Agreed starting point" list below for
exactly what's done vs. still open). Kept as a design-reference doc
rather than folded entirely into `NEXT_STEPS.md`, since the reasoning
behind each decision here is worth more than a one-line summary. See
`NEXT_STEPS.md` item #13 for the current terse status line.

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

## Three architecture pieces (all designed, all built — see "Agreed starting point" below)

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

**✅ The growth mechanism itself is done, 2026-08-25** (directly
requested: *"drop in some images, and some sort of file that provides
the expected OCR data, and have the test cases automatically pick up
the new images in their next run"*). New `scripts/vehicle_discovery.py`
walks `ExampleDocs/scans/<truck|trailer|scale>/<vehicle_slug>/` for a
`vehicle.json` sidecar (`{"pool": "pass", "fields": {...}}` or
`{"pool": "fail", "expected_none_fields": [...]}` — `doc_type` is
deliberately *not* a field in it, inferred instead from which bucket
directory the vehicle sits under, one source of truth not two) plus
every image file already sitting next to it — dropping in one more
photo of an already-registered vehicle needs zero file edits at all,
only a brand-new vehicle needs a new `vehicle.json` written.
`scripts/pass_pool.py`/`fail_pool.py` merge discovered vehicles into
the same structure the legacy `golden_fields.json` entries already use;
both gained `registered_doc_types()` so the two regression tests
parametrize from the merged view automatically. TDD'd in
`tests/test_vehicle_discovery.py` (10 cases, including fail-loud
`ValueError`s on a malformed sidecar or an image-less vehicle folder —
matching this project's convention of failing loud, not skipping a
malformed entry quietly).

Proven two ways, not just unit-tested in isolation: the fail-pool's
F-150 vehicle was actually migrated for real —
`ExampleDocs/scans/truck/f150/` → `.../f150_blue_goose_uncropped/` with
a real `vehicle.json`, its `golden_fields.json` entry deleted — and
`tests/test_fail_pool_regression.py` still passes, now sourced entirely
from the directory. The pass-pool half got a real `tmp_path` integration
test instead (no spare unentangled real photo existed to migrate the
same way — `AddieTag.jpg`/`GooseTag.jpg` both feed other tests): copies
`CatScale-GooseOnly.jpg`'s real bytes into an isolated temp tree,
proving `resolve_pass_pool_image` and real Tesseract both work against
a directory-discovered vehicle end-to-end. Full suite clean (554
passed, 3 xfailed).

**What's still not done**: actually adding new manufacturer/format
photos (a real Chevy label, an RV tag from a manufacturer other than
Brinkley). The mechanism is ready for it — drop a folder in, no code
changes — but no such real photos exist yet.

## Cross-platform scope — decided and built, 2026-08-25: duplicate, not inherit

The premise this question was originally weighed against turned out to
be wrong: the pass-pool/fail-pool actually built in Python this session
(`scripts/pass_pool.py`/`fail_pool.py`) tests **Tesseract**, not Claude
vision — Python's production app (Streamlit + FastAPI) never calls
Claude at all (see `NEXT_STEPS.md` item #16, the separately-recorded
build-time-switch gap). So there was never a Python Claude-vision path
for Android to "inherit" from in the first place; Android's real scan
feature is the *only* live path in this repo that calls Claude vision on
a real user's photo. Decided: Android builds its **own** real
pass-pool/fail-pool, specifically to exercise `PhotoEncoding.kt`'s real
resize/compress path (1600px long edge, JPEG quality 85) that the one
existing real-vision test (`realScanDecrementsBalance`) deliberately
bypasses and never golden-value-checks.

**Built and verified for real**: new `ScanFixturePool`
(`android/app/src/androidTest/java/com/rigcheck/app/testsupport/`,
TDD'd against a fake `FixtureFileSource` in `ScanFixturePoolTest.kt`)
mirrors `scripts/vehicle_discovery.py`'s exact directory convention
against `androidTest/assets/scans/<bucket>/<vehicle_slug>/vehicle.json`.
Two new cases in `PaywallScreenWeeklyTest.kt`
(`scanPassPoolRandomPickMatchesGoldenFields`,
`scanFailPoolRandomPickReturnsNullForMissingFields`) resolve a random
photo per pool, run it through the real `encodePhotoForScan()` path, and
check real extracted values — not just "fields non-empty." Passed for
real via `.\test-weekly.ps1` (6/6 tests).

**This decision paid for itself immediately**: building this test
surfaced a real, previously-unknown bug on its very first real run — the
deployed Worker was pinned to `claude-haiku-4-5-20251001` (a cheaper
model choice never validated against this task), which returned
confident, wrong GVWR/GAWR values even for `AddieTag.jpg`, the easiest
fixture in the repo. Fixed by switching to `claude-sonnet-5` (full
narrative: `NEXT_STEPS.md` item #15, `ARCHIVE_MONETIZATION.md`) — a bug
that specifically lived in the real deployed configuration, which
neither Python's direct-Claude path nor a mocked scan-proxy unit test
could ever have caught. Concrete vindication of "duplicate," not a
theoretical one.

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
   photos (still on disk, never re-added to `"photos"` — later migrated
   to `ExampleDocs/scans/truck/f150_blue_goose_uncropped/`, see step 6's
   directory-convention entry below — see item #11's "document, don't build"
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
5. ✅ **Done, 2026-08-25 — the interface-contract suite.** Per this
   doc's own scoping decision above (a documented command, not new
   automation or new test code), `DEV_ENVIRONMENT.md`'s "Python /
   backend / Streamlit" section now documents the combined command:
   ```bash
   uv run pytest -q tests/test_pass_pool_regression.py tests/test_fail_pool_regression.py -v
   ```
   Run for real to confirm it works (4 passed, both pools together in
   one invocation), with a note to re-run it a few times on a real
   dependency bump for broader coverage, since each run samples one
   random image per pool/doc_type. Confirmed with the project owner
   directly that this minimal, documentation-only scope was correct
   rather than building a new exhaustive-sweep script — consistent with
   this doc's own "manual trigger only, no automation" scoping decision
   above. All three core pieces of this design (pass-pool, fail-pool,
   interface-contract suite) are now done.
6. ✅ **Done, 2026-08-25 — directory-convention auto-discovery**
   (`scripts/vehicle_discovery.py`) **and the Android inherit-vs-duplicate
   decision** (Android duplicates, builds its own pass-pool/fail-pool —
   see "Cross-platform scope" and "Manufacturer/format diversity
   priority" above for full detail on both, including the real
   Haiku-4.5-vs-Sonnet-5 bug this decision immediately caught).
7. **Still open**:
   - Actually adding new manufacturer/format photos to the Python pools
     — the growth mechanism itself is done (step 6 above), but no real
     Chevy/other-manufacturer photos exist yet to drop into it.
   - Growing Android's own pass-pool/fail-pool past its two initial
     fixtures — the other 9 F-150 photos item #11 found Claude reads
     correctly under `claude-sonnet-5` are ready-made, zero-new-photography
     pass-pool material, not yet added.
