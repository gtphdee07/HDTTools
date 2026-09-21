# Archive: Web + Streamlit feature history

Detailed narrative for Web/Streamlit feature work, moved out of
`NEXT_STEPS.md` 2026-08-23 to keep that file's current-status section
cheap to read. Current status/roadmap lives in `NEXT_STEPS.md` — this
file is history, not a place to look for "what's next."

**Entry-tag convention** (for `Grep`-based lookup instead of reading this
whole file): entries lead with `✅ **Real bug`, `**Decided`, `**Design
correction`, or similar bold tags — grep for those to filter by type.

---

## 🖼️ Web + Streamlit: skip-image entry and predictive tow-vehicle-alone weight — done 2026-08-20

Two related, real-world-driven requests, scoped to Web + Streamlit only
(Android/CLI untouched this round): (1) users may have 0-3 of (truck tag,
trailer tag, scale ticket) photos and need a way to skip straight to manual
entry instead of being blocked at the upload screen; (2) growing interest in
*pre-purchase* "can I tow this" estimation, which needs a tow-vehicle-alone
weight even before a real rig exists to put on a scale.

**Backend (`src/hdttools/api/breakdown.py`, the shared source of truth):**
- `compute_breakdown` gained a `pin_weight_pct` parameter (default 0.20,
  was the hardcoded `DEFAULT_AXLE_TO_TOTAL_RATIO = 0.8`) and a new 3-way
  branch for "Trailer Total (GVWR)": exact tongue-weight math when
  `standalone_weight_lb` is known, `trailer_axle / (1 - pin_weight_pct)`
  when a real trailer-axle scale reading exists, or — new — an estimate
  off the trailer's *rated* GVWR when there's no scale reading at all
  (the pre-purchase case).
- New `"insufficient"` tone + verdict tier ("Not Enough Information" when
  every row lacks data, "Partially Checked" when some do) sits alongside
  the existing pass/fail, driven by per-row **source-field presence**
  (`x_raw is None`), not `limit <= 0` — the latter was tried first and
  found wrong via test-writing (a row can have a real limit but a missing
  actual, which `limit<=0` would silently show as a false pass).
- Fixed a latent bug in both `main.py` and `streamlit_app/app.py`: each
  derived pass/fail by sniffing whether the headline starts with "Not" —
  broken once "Not Enough Information" also starts with "Not". Both now
  read `verdict_for`'s new explicit `status` field instead.
- 65/65 `uv run pytest -q` passing (was 54 before this feature).

**Web**: `UploadStep` gained an "I don't have this image" button (skips
straight to the blank review form, reusing the same rendering path a real
empty-OCR-result already takes); `ReviewStep`'s truck step gained a
tow-vehicle-only scale-ticket scanner (reuses the existing scale-ticket OCR
pipeline, maps the reading onto `standalone_weight_lb`) and, when that's
still empty, a 15-25% pin-weight slider defaulting to 20%. Verified live via
a Playwright walkthrough: 0 images at all → "Not Enough Information" with
correct "Not enough info" badges on every row, zero console errors.

**Streamlit**: same shape (`_module_step` skip button, `_render_review`,
`_render_standalone_ticket_section`) — but this is where a **real,
crash-causing bug** was caught live, not by pytest: `st.number_input`
cannot return `None`, so simply *rendering* the review screen was silently
turning every un-entered numeric field into a real `0.0` instead of leaving
it blank. That defeated the new presence-based insufficient-tracking (a
literal `0.0` isn't `None`) and then hit a `ZeroDivisionError` computing a
percentage against a `0` limit once a fully-skipped rig reached Results.
Fixed by passing `value=None` to `st.number_input` (supported since
Streamlit ~1.23; this project runs 1.61.1) instead of defaulting to `0.0` —
it now renders a genuinely blank input and returns `None` until the user
types something. Also fixed a smaller UX bug found the same way: the
"Tesseract returned no text at all" warning was showing after a deliberate
skip too (no OCR ever ran) — now gated behind a new
`st.session_state[f"{module_key}_skipped"]` flag, showing "No photo
provided" instead.
- **`tests/test_streamlit_app.py` (new)** — the project's first Streamlit
  UI-level automated tests, via `streamlit.testing.v1.AppTest`. Two tests:
  the full skip-everything-reaches-Results-without-crashing regression
  (this is what pins down the `ZeroDivisionError` fix — `compute_breakdown`'s
  own unit tests can't see this bug, since they call it directly with
  genuinely-`None` dicts, never through `app.py`'s widget layer), and the
  skip-notice-vs-OCR-warning distinction. See the corrected `AppTest`-on-
  Windows note in `ARCHIVE_TESTING.md` (search "Correction, 2026-08-20") —
  it does *not* hang on this machine, contrary to an earlier session's
  finding.
- Verified live via Playwright, same walkthrough as Web: 0 images at all →
  "Not Enough Information", all six rows showing "Not enough info", no
  exceptions.

Scope deliberately left for a follow-up round (per the plan this was built
from): no new predictive/cargo-capacity *output* row yet — just the two
input mechanisms (skip button, tow-vehicle-alone weight source).

**Follow-up done, 2026-08-20 — the output row above, plus a legal
disclaimer.** "Tow Vehicle Total (GVWR)" previously stayed "Not enough
info" forever in the pre-purchase scenario (a tow-vehicle-alone reading
known, but no real hitched combined scale reading) — its insufficiency
check only ever recognized a real `steer_axle_lb`+`drive_axle_lb` pair.
Fixed by giving `compute_breakdown` a second, independent branch for the
truck-side total: when there's no hitched reading but a real stand-alone
one exists, estimate the missing tongue weight off the trailer-side total
(`trailer_total_actual * pin_weight_pct`) and add it onto the stand-alone
weight — same math shape as the existing trailer-side estimate, just
mirrored onto the truck side.
- **Real bug fixed in passing, found while redesigning this**: the old
  trailer-total branch gated its three-way logic on `if standalone_weight`
  truthy *alone*, not on whether a real hitched reading also existed — so
  a user with *only* a tow-vehicle-alone reading (the exact pre-purchase
  case) silently got `tongue_weight = max(0, 0 - standalone) = 0`, losing
  the tongue-weight estimate entirely instead of falling back to the
  axle-based or GVWR-fallback estimate. Fixed by decoupling
  `have_hitched`/`have_standalone` explicitly. Regression test:
  `tests/test_breakdown.py::test_truck_and_trailer_totals_both_estimate_when_only_a_trailer_axle_reading_exists`
  (asserts the trailer total comes out to the correct 14,225 lb estimate,
  not the bug's 11,380 lb symptom).
- **New `estimated: bool` field** on each breakdown item (additive,
  `BreakdownItemOut`/`BreakdownItem` in both schema layers) — `True` only
  when a row's number came from `pin_weight_pct` math rather than a real
  reading; always `False` on insufficient rows (a row can internally take
  an estimate branch while still being insufficient for an unrelated
  reason, e.g. no trailer GVWR at all — the flag must not leak `true` in
  that case; see the corresponding pytest case).
- **New persistent legal disclaimer** — explicitly requested with real
  content, not just a generic warning: build/trim options change real
  payload, passengers/cargo aren't accounted for, the specific vehicle's
  own certification label must be checked before buying, and the
  consumer alone is responsible for safe towing and FMCSA/DOT compliance
  (federal and state). Deliberately **not** the existing one-time
  `DisclaimerModal`/`DISCLAIMER_TEXT` (acknowledged once, then gone) —
  this one re-renders every time any row has `estimated: true`:
  `web/src/components/PredictiveEstimateNotice.tsx` (amber `--state-warning`
  callout, visually distinct from the mauve `--state-info` "insufficient"
  styling) and Streamlit's `PREDICTIVE_ESTIMATE_NOTICE` via `st.warning`.
- Verified live on both platforms (Playwright for Web, `AppTest` for
  Streamlit) with the same scenario: truck tag + stand-alone weight
  entered, trailer tag entered, scale ticket fully skipped — confirms
  "Tow Vehicle Total (GVWR)" renders a real "5,500 lb to spare" badge
  (was "Not enough info"), and the new disclaimer renders on both.
- `uv run pytest -q`: 70/70 passing (was 65). `npm run build` clean.

**Follow-up, 2026-08-20 (same day) — Scale Ticket step now points at the
predictive path explicitly.** The generic "I don't have this image" skip
button didn't tell anyone that skipping the *scale* step specifically is
what unlocks the estimate above. `UploadStep.tsx`'s scale-module rendering
(and Streamlit's `_module_step` for `module_key == "scale"`) now show:
an italic caption ("No CAT scale ticket? You can skip this step and still
build an estimated model from your truck and trailer tag ratings.") plus
*two* buttons instead of one — "No Image / Enter Weight Manually" (renamed
from the old generic label, same skip action) and "Build Estimated Model /
No CAT scale info" (new, same skip action, framed for the predictive use
case). Both buttons call the identical underlying skip handler — this is
purely a messaging/framing change, no new behavior. Truck Tag and Trailer
Tag steps are unchanged (still one generic "I don't have this image"
button each). Verified live on both platforms (Playwright screenshot for
Web, `AppTest` for Streamlit). `uv run pytest -q`: still 70/70. `npm run
build`: clean.

**Follow-up, 2026-08-20 (same day) — real tow-vehicle-only photo added,
real bug found and fixed via it.** `ExampleDocs/CatScale-GooseOnly.jpg` is
a real CAT Scale ticket weighing just the tow vehicle (tractor# GOOSE, no
trailer hitched — trailer axle reads 00 LB). Used to close a
long-flagged gap: this repo had never had a test that runs real Tesseract
OCR against a real photo file, only hand-transcribed text.
- ✅ **Real bug found and fixed, Streamlit only**: scanning a
  tow-vehicle-only ticket correctly set `truck["standalone_weight_lb"]`,
  but the very next render of the review form silently overwrote it back
  to blank. Root cause: `_render_review`'s `st.number_input(key=
  "truck_standalone_weight_lb", ...)` had already been instantiated
  earlier in the run (in a prior page load, before the scan), so its own
  cached widget state — still blank — took priority over the freshly
  updated data dict on the next rerun, per Streamlit's standard "a new
  `value=` is ignored once a keyed widget already has session-state" rule.
  Never caught before because the only prior verification of this feature
  was a screenshot of the upload UI rendering, not an actual scan-and-
  confirm-the-field-updates walkthrough. Fixed via the standard Streamlit
  workaround: stash the new value in a scratch `_pending_standalone_weight_lb`
  key and apply it to the widget's own key at the *top* of `_module_step`,
  before `_render_review` instantiates the widget (setting a widget's key
  *after* it's already been instantiated this run raises a
  `StreamlitAPIException` — tried that first, had to switch approaches).
  Verified against the real live app via Playwright, not just `AppTest`.
- **New tests, all real-photo/real-OCR, not mocked**:
  `tests/test_scale_ticket_ocr_parsing.py::test_parse_fields_on_a_real_tow_vehicle_only_ticket`
  (ground-truth `_parse_fields` coverage using this ticket's actual
  Tesseract output — documents, doesn't fix, some unrelated cosmetic OCR
  garbling in `tractor_number`/`trailer_number`/`location_name`, none of
  which feed into `compute_breakdown`). `tests/test_scale_ticket_real_photo.py`
  (new file — the first test in this repo to run real Tesseract against a
  real `ExampleDocs/` image end to end, both at the `scale_ticket_ocr`
  module level and through the real `/api/extract/scale-ticket` FastAPI
  endpoint with nothing mocked). `tests/test_streamlit_app.py::
  test_scanning_a_real_tow_vehicle_only_photo_fills_in_standalone_weight`
  (the regression test for the bug above, uploading the real photo through
  `AppTest`'s `file_uploader.set_value(...)`).
- **Unrelated environment note**: hit the recurring "websockets" file-lock
  quirk (see `NEXT_STEPS.md`'s "Fresh-machine setup checklist") badly
  enough this session that the package ended up genuinely corrupted (missing
  `__version__`, Streamlit failed to boot at all) rather than just the
  usual cosmetic warning — fixed by manually deleting
  `.venv/Lib/site-packages/websockets*` and letting `uv sync --extra
  streamlit` reinstall clean. If `streamlit run` ever fails with
  `ImportError: cannot import name '__version__' from 'websockets'`, this
  is the fix.
- `uv run pytest -q`: 74/74 passing (was 70).

**Follow-up, 2026-08-20 (same day) — WTWT branding in the Streamlit
sidebar, and a real test-isolation bug found in the process.**
`streamlit_app/assets/wtwt_logo.png` (the "Wandering Trails Wagging
Tails" logo — RV, mountains, two dogs — provided by the user) now renders
via `st.image(..., width=160)` at the top of the sidebar, unconditionally
(the sidebar itself used to only render at all once a check existed in
session history; restructured so branding shows from the very first page
load, with "This session's checks" nested conditionally beneath it).
- ✅ **Real bug found and fixed**: `tests/test_streamlit_app.py`'s
  `AppTest`-driven tests run the real (non-mocked) `app.py`, including its
  real `recent_rigs.py` persistence layer — which has always written
  straight to `~/.rigcheck/recent_rigs.json`, the developer's actual local
  file, with no test-time override. Every prior run of this test file
  silently left synthetic "Test Rig"/"Predictive Verify"/etc. entries in
  the real recent-rigs list (confirmed and cleaned up manually this
  session; also found via a live screenshot showing them cluttering the
  rig picker). Fixed with an autouse `monkeypatch` fixture that redirects
  `recent_rigs.RECENT_RIGS_PATH` to a `tmp_path` for every test in the
  file — verified the real file's mtime is now untouched by a full test
  run. **If any *other* future Streamlit test file drives a full checkout
  through `AppTest`, it needs this same fixture** — it isn't automatic
  across files.
- `uv run pytest -q`: still 74/74.

---

## ✅ Real four-photo walkthrough + Python coverage wired up (roadmap items #6/#4a, plus #7's truck/trailer real-photo gap) — 2026-08-24

**The actual gap, precisely.** `test_streamlit_app.py` already had one
real-photo `AppTest` case (the standalone tow-vehicle-only scan, above) —
proof the pattern works and finds real bugs a mocked test can't. But
nothing drove all three main modules (truck, trailer, scale) with real
photos in one continuous walkthrough to a real Results verdict; every
"full walkthrough" anywhere in this repo (this file's own tests and
`web/`'s Playwright suite) only ever exercised the zero-image,
skip-everything path.

**Golden ground-truth data, supplied directly by the user, not guessed
from a first OCR run.** New `ExampleDocs/golden_fields.json`, structured
like `test-vectors/breakdown_cases.json` (a self-documenting `_readme`,
same shared-vectors spirit) but split into two parts on the user's own
insight: `"photos"` (independent, per-document ground truth - what OCR
*should* read off one specific image) and `"rigs"` (valid,
physically-coherent `(truck, trailer, scale)` tuples - because a scale
ticket's axle weights are only physically meaningful for the *exact*
combination actually weighed together; a truck tag and trailer tag can
each be independently real while still being an invalid pairing for a
mismatched scale ticket). The user also pointed out mid-build that the
walkthrough should eventually exercise varied combinations rather than
always the same pairing - resolved as `@pytest.mark.parametrize` over
`"rigs"` rather than `random.choice`, since true runtime randomness in a
test makes failures non-reproducible and silently skips untested
combinations on any given run; parametrization gets the same real goal
(a growing pool means growing coverage) with full determinism.

**Four real photos, one real rig.** `AddieTag.jpg` (truck, Ford,
GVWR 14000/6000/9900), `GooseTag.jpg` (trailer, Brinkley RV,
GVWR 23500/8000-per-axle/3 axles/UVW 20554), `CatScale-Ticket.jpg` (the
full rig weighed together: steer 5640/drive 9080/trailer-axle
19680/gross 34400), and `CatScale-GooseOnly.jpg` (the *same* truck
weighed alone: steer 5560/drive 4420/gross 9980 - already used by the
existing standalone test, now sourced from the same golden file instead
of a second hardcoded copy of the same numbers). **Known naming
curiosity, not a data error**: the scale ticket's own printed text reads
"TRACTOR # GOOSE TRAILER # ADDIE" - the fleet nicknames on the ticket
are reversed from the photo filenames (confirmed with the user directly:
`AddieTag.jpg` is the truck, `GooseTag.jpg` is the trailer) - doesn't
affect any field's correctness, just worth knowing if it's ever
confusing later.

**The real verdict, computed for real, not guessed.** With all four
photos scanned (the standalone reading present), `compute_breakdown`
takes its more precise tongue-weight branch rather than the
`pin_weight_pct`-estimate one: Tow Vehicle Total (steer+drive=14,720 vs
GVWR 14,000, 720 lb over) and Trailer Total (19,680 axle + 4,740 lb
tongue weight = 24,420 vs GVWR 23,500, 920 lb over) both exceed their
limits, landing on a genuine **"Not Safe to Tow"** verdict - run through
the real `compute_breakdown`/`verdict_for` functions directly (not
hand-derived arithmetic trusted blindly) before being written into
`golden_fields.json`, then proven again for real by the walkthrough test
itself reaching that same verdict through the full UI.

**✅ Real bug #1, found and fixed**: `truck_tag_ocr._kg_lb`'s regex
required `label:?\s*` immediately before the digit group. Real OCR on
`AddieTag.jpg` produced `"REARGAWR: <?>4491KG(99001B)"` - a stray
replacement-character glyph right after the colon - which matched
`front_gawr` fine (clean text) but made `rear_gawr_kg`/`rear_gawr_lb`
both return `None` on the very same tag. Fixed by widening the
label-to-value gap from `:?\s*` to `\W{0,4}` (tolerates a few stray
non-word characters, never crosses into the actual digits since `\W`
excludes them) - same spirit as the `[L1I][B8]` tolerance already built
into this function for the "9900 LB" → "99001B" class of OCR noise, just
not comprehensive enough before this.

**✅ Real bug #2, found and fixed**: `scale_ticket_ocr`'s `location_name`
regex required `LOCATION:?\s*` before the location text. Real OCR on
`CatScale-GooseOnly.jpg` produced `"Location, LOVES COUNTRY STORES..."`
(a comma, not a colon) - so the comma itself became the first character
of the captured `location_name` instead of being skipped. Fixed by
widening the prefix to `LOCATION[:;,]?\s*`.

**Two genuine, real OCR-accuracy limits found - documented, not chased
or hidden.** Both `xfail(strict=True)` in `test_real_photo_ocr_accuracy.py`
with the real reason recorded on `golden_fields.json`'s
`known_ocr_limitations`, so a value real OCR doesn't actually produce is
never silently asserted as passing, and if either genuinely starts
passing later, the strict xfail turns into a hard failure demanding the
note be removed, not a silent pass:
1. `GooseTag.jpg`'s `gawr_per_axle_lb` reads as `800.0`, not `8000.0` - a
   genuine digit-drop on the repeated trailing zero (the paired kg value,
   3629, parses correctly and converts to the real 8000 lb, confirming
   what's actually printed). No safe regex change reliably distinguishes
   a genuine 3-digit reading from a dropped-zero 4-digit one without risk
   of introducing false corrections elsewhere - a real character-recognition
   miss, not a pattern-matching bug.
2. `CatScale-Ticket.jpg`'s `location_name` returns `None` entirely - its
   real OCR read "GROSS WEIGHT" as `"crossweicHT"` (the leading G misread
   as a c, a different letter, not just noise around a correct one), so
   the boundary keyword the capture group looks for to know where to stop
   never matches. `CatScale-GooseOnly.jpg`'s otherwise-identical ticket
   format has a different, real limit instead: its capture *does* find
   the right boundary but swallows unrelated column-2 boilerplate text
   along the way (`scale_ticket_ocr.py`'s own module docstring already
   documents this two-column-layout jumbling as a known limitation of
   plain linear OCR reading order). Not chased further - not worth a
   fragile G/c-substitution heuristic for one label on one boundary
   pattern.

**Manual-only fields, entered like a real user would.** `axle_count`
(trailer) is never present in real `_parse_fields()` output (confirmed
by `test_ocr_output_key_contracts.py`'s existing exclusion list) - the
walkthrough test drives its `number_input` widget directly after the
trailer upload, exactly as a real user filling in a field OCR can't
read would.

**Verification, in full.** `uv run pytest -q`: 116 (was 95) - 113
passing, 3 deliberate `xfail`. Zero regression on every pre-existing
test. Python coverage wired up in the same pass (roadmap item #4a,
"nearly free" as planned): `[tool.coverage.run]`'s `source` widened to
include `streamlit_app`; `uv run pytest --cov --cov-report=term-missing`
now works bare (no `--cov=PATH` needed - coverage.py picks up the
configured `source` automatically). Real numbers: 79% total,
`streamlit_app/app.py` 80%, `fields.py` 100%, `recent_rigs.py` 79% - see
`tests/TESTING.md`'s new "Coverage" section.

---

## 🔍 Real-photo OCR robustness investigation: Tesseract vs. Claude vision - closed 2026-08-24

Started from a real test-planning idea (roadmap item #11): the user had
10 real photos of the same physical Ford tow-vehicle tag - one clear
shot plus 9 more at varying angle/shadow/sun-glare quality
(`ExampleDocs/scans/truck/f150/`, moved there from a flat
`ExampleDocs/F-150Tags/` as the new convention for future multi-photo
scan sets; ground truth `GVWR: 7100 LB`, `GAWR: 3525 LB` front,
`REAR GAWR: 3800 LB`, confirmed against the real photographed tag's own
`KG (LB)` printing, not just the hand-transcribed `F-150Spec.txt`). The
plan was a straightforward "quality gradient" test: run all 10 through
the existing Tesseract-based OCR path and see how far accuracy degrades.
It didn't work out that way - the investigation found something more
useful than the planned test.

**✅ Real finding #1: Tesseract fails on all 10 raw photos, and it's not
about quality.** Running the real, non-interactive pipeline
(`ocr_common.open_image`/`preprocess_image`/`ocr_text` then
`truck_tag_ocr._parse_fields`, the same sequence
`test_real_photo_ocr_accuracy.py` uses) against all 10 photos returned
`None` for every field, on every photo - including the best-framed,
clearest-looking shot in the set. The cause: these are realistic,
un-cropped phone photos (a wider dashboard/door-jamb shot with the tag
as one region among tire-info stickers, the hitch, reflections),
and `preprocess_image()` never crops - it only grayscales, autocontrasts,
and upscales the *whole* frame. `pytesseract`'s `--psm 6` (assume one
uniform text block) can't isolate the tag's own lines from that
surrounding clutter, regardless of how sharp or well-lit the photo is.
Confirmed with a manual crop test: cropping just the tag region out of
one photo immediately produced a real, correct match
(`rear_gawr_lb: 3800.0`) from previously all-`None` output. This is a
real, previously-undiscovered product gap, not a per-photo quirk like
`GooseTag.jpg`'s digit-drop above - it's documented as a known
limitation in `NEXT_STEPS.md` rather than chased with per-photo crop
tuning this session (manual crop+rotation work across 10 differently-
framed/rotated photos was judged not worth it right now).

**✅ Real finding #2: Claude vision handles the same raw photos with no
preprocessing at all - 9/10 perfect.** The user asked to test the same
10 photos through "the Anthropic API flow" before deciding next steps.
This project already has a direct Python path for this
(`src/hdttools/vision_client.py::extract_via_claude` +
`truck_tag.py`'s system prompt/schema - the same extraction shape
`workers/scan-proxy/src/claude.ts`/`docTypes.ts` port to TypeScript for
the mobile app's real scan endpoint) - called directly against all 10
real photos, `claude-sonnet-5`, no crop, no preprocessing. Real result:
**9 of 10 photos extracted all three fields perfectly**, including the
most extreme shot in the set (the tag rotated ~90°, occupying maybe 10%
of a mostly-out-of-focus frame) - something Tesseract couldn't do at
any framing. The one failure (`20260824_141545.jpg`) is fully explained
by looking at the photo: it's framed so the top portion of the tag
(manufacturer/date/GVWR/REAR GAWR lines) is literally outside the frame,
only the lower half (tire specs, VIN, barcode) is visible - the data
genuinely isn't in the picture, not a robustness failure. Real cost:
10 billed Claude vision calls, ~$0.30-0.50 total (not repeated - this
was a one-time investigation, not an added recurring test).

**✅ Real finding #3: the Claude-vision path has zero real-photo test
coverage today, unlike the Tesseract path.** Checked both
`tests/test_vision_client.py` and `tests/test_readers_integration.py` -
both fully mock `extract_via_claude`/`vision_client`, no real image, no
real API call, anywhere in the suite. `test_real_photo_ocr_accuracy.py`
only exercises Tesseract. Given finding #2 shows the vision path is
genuinely robust and this photo set would make a strong first real
regression test for it, this is flagged in `NEXT_STEPS.md`'s "Tests
still outstanding" rather than built this session - a real-money-per-run
test needs an External-tier equivalent for Python first (this project
doesn't have one today; `scan-proxy`'s `test-release.ps1`/
`test-weekly.ps1` are the existing cross-platform pattern to follow).

**Decided: document, don't build new test code this round.** Both
findings are real and worth capturing, but neither is finished/actionable
enough yet to turn into permanent test code today - the Tesseract fix
needs a real design decision (auto-crop preprocessing vs. in-app user
guidance), and the Claude-vision test needs the External-tier-equivalent
question settled first. `golden_fields.json`'s per-field `xfail` pattern
was tried and reverted (added all 10 photos, ran the real test, saw 40
uniform failures, then removed them) - not because it's a bad pattern,
but because it's the wrong shape for "the whole document fails
identically for one structural reason," not a per-field quirk. The 10
photos themselves stay at `ExampleDocs/scans/truck/f150/` for whenever
either test gets built for real.

✅ **Superseded 2026-08-25**: the fail-pool test got built for real
(item #13, `FUTURE_CONSTRAINED_RANDOM_OCR_TESTING.md`) — these 10
photos moved to `ExampleDocs/scans/truck/f150_blue_goose_uncropped/`
with a `vehicle.json` sidecar, auto-discovered by
`scripts/vehicle_discovery.py` rather than referenced from
`golden_fields.json` directly.

---

## 🔀 Build-time OCR-backend choice for Streamlit/web (item #16) — done 2026-09-09

Built the flag item #16 recorded 2026-08-25: `HDTTOOLS_OCR_BACKEND`
(`ocr_common.get_ocr_backend()`, default `"tesseract"`, `"claude"` the
only other valid value, `ValueError` on anything else — fail loud, no
silent fallback), read by both `src/hdttools/api/main.py` and
`streamlit_app/app.py` to choose Tesseract-style vs Claude-vision-style
extraction per doc_type. TDD throughout (`TDD_METHODOLOGY.md`): every
new function's test written first, watched fail for real, then
implemented; full `uv run pytest -q` re-run after each step.

**Real refactor: `vision_client.extract_via_claude` now takes bytes, not
a path.** Before this, it took `image_path: Path` and read bytes off
disk itself — dead weight for both real callers (`main.py`'s
`UploadFile`, Streamlit's `UploadedFile`), which already have the image
as in-memory bytes. Changed the signature to
`(image_bytes: bytes, media_type: str, ...)`; the three existing
interactive callers (`truck_tag.py`/`trailer_tag.py`/`scale_ticket.py`)
now compute both at their own call site via a small new
`vision_client.image_bytes_and_media_type()` helper (one
`mimetypes.guess_type` line, not three copies). `tests/test_vision_client.py`
was rewritten to the new signature first, watched fail
(`TypeError: got an unexpected keyword argument 'image_bytes'`), then
the implementation changed — real Red confirmed, not assumed.

**New headless, pure extractor functions** — `truck_tag.extract_truck_tag_fields`,
`trailer_tag.extract_trailer_tag_fields`, `scale_ticket.extract_scale_ticket_fields`
(each `(image_bytes, media_type) -> dict`) — wrap `extract_via_claude`
with that module's own `_SYSTEM_PROMPT`/`_SCHEMA` and do the same
`TireSpec(**fields.pop(...))` unpacking `read_truck_tag()`/
`read_trailer_tag()` used to do inline; both `read_*` functions were
refactored to call the new function, removing the duplication.
`tests/test_readers_integration.py` gained Function-tier tests for all
three (mocking `extract_via_claude` the same way `test_vision_client.py`
does); `tests/test_ocr_output_key_contracts.py` gained the same
schema-direction contract check these functions now share with
`_parse_fields()` (fake Claude responses shaped from each module's own
`_SCHEMA` via a small `_fake_claude_fields()` helper, so the check
tracks future schema edits automatically).

**`main.py`**: the three near-duplicate route bodies collapsed into one
`_extract_fields(doc_type, file)` dispatch, keyed by two
`(module, attribute-name)` dicts (`_TESSERACT_PARSERS`/
`_CLAUDE_EXTRACTORS`) resolved via `getattr()` at call time rather than
bound function objects — deliberately, so `tests/test_api.py`'s existing
`monkeypatch.setattr(main.truck_tag_ocr, "_parse_fields", ...)` pattern
(and the new matching Claude-side one) still takes effect, the same way
the original routes' direct attribute access did. Tesseract branch is
byte-for-byte the old behavior; Claude branch validates content-type the
same way, reads raw bytes, calls the matching extractor, and normalizes
any exception to `HTTPException(502, ...)` — distinct from the existing
400 "not a valid image" case, since a 502 here means the upstream Claude
call itself failed, not a bad upload. 6 new `test_api.py` cases (3
per-route dispatch, rejected-upload, 502-normalization, invalid-env-value).

**`app.py`**: `_extract_fields` branches the same way, with a matching
`_CLAUDE_EXTRACTORS` dict; the Claude branch calls
`uploaded_file.getvalue()`/`.type` and returns `(fields, "")` for the
raw-text slot (both branches already shared the same `FIELDS`-based
`keep`-filtering, unaffected by the branch). **Real edge, exactly as
anticipated in the plan**: the `elif not raw_text.strip(): st.warning("Tesseract
returned no text...")` at `app.py`'s review-render step would otherwise
fire on *every* successful Claude extraction, since `raw_text` is always
`""` on that path — fixed by gating it on
`get_ocr_backend() == "tesseract"` too. 4 new `test_streamlit_app.py`
cases (one Claude-backend upload per module, plus a case proving the
warning stays suppressed) — confirmed the "fix" was real by watching the
new warning-suppression test fail first for the *right* reason (an
`AttributeError`/`KeyError` from the dispatch not existing yet, not a
warning actually firing), then pass for the right reason once both the
dispatch and the gate were in.

**New External-tier test (first for this Python platform)**:
`tests/test_claude_vision_external.py`, `@pytest.mark.skipif`'d unless a
real `ANTHROPIC_API_KEY` is set, one real Claude vision call per doc type
against a random pass-pool image (`scripts/pass_pool.py`, item #13's
existing infra — no new fixtures). Corrects `tests/TESTING.md`'s
now-stale "No External suite exists here today... N/A" line from
2026-08-21, true only until this file existed.

✅ **Real environment gotcha, confirmed 2026-09-09**: this dev machine
has `ANTHROPIC_API_KEY` set ambiently (ambient env var, not a
per-session export) — the same class of surprise
`TDD_METHODOLOGY.md`'s scan-proxy section already documents for that
platform ("`ANTHROPIC_API_KEY` was found ambiently set in this dev
machine's shell once, unintentionally"), now confirmed on the Python
side too. Consequence: a routine `uv run pytest -q` on this machine does
**not** skip the new External suite — it makes real, billed Claude API
calls every single run. Every mocked-only test run this session
explicitly unset the var first (`unset ANTHROPIC_API_KEY && uv run
pytest -q`); the one deliberate real run (see below) was run separately,
once, on purpose. Anyone continuing this work on this machine should
check `$env:ANTHROPIC_API_KEY`/`echo $ANTHROPIC_API_KEY` before a casual
full-suite run.

✅ **Real finding from the one deliberate External-tier run, 2026-09-09
— 2 of 3 doc types passed for real, 1 surfaced a genuine ground-truth
question, not a code bug.** `trailer_tag` and `scale_ticket` passed
outright: real Claude vision calls against
`ExampleDocs/scans/trailer` (via `GooseTag.jpg`, resolved by the
pass-pool) and the `brinkley_goose_willis_tx` scale vehicle matched
their documented golden fields exactly. `truck_tag` (`AddieTag.jpg`)
failed on exactly one field: `manufacturer`. Claude read
`"FORD MOTOR CO."` (with a trailing period); `golden_fields.json`'s
documented ground truth is `"FORD MOTOR CO"` (no period). Investigated,
not assumed: (1) visually inspected `AddieTag.jpg` directly — the
physical label plainly prints "MFD. BY FORD MOTOR CO." with a trailing
period; (2) ran real Tesseract against the same photo and confirmed it
*also* drops the period (`truck_tag_ocr._parse_fields` returns
`"FORD MOTOR CO"` for real, matching the documented golden value
exactly) — so the documented ground truth was set to match Tesseract's
own real (slightly imprecise) output, not independently re-verified
against the physical label's punctuation. This means Claude vision's
answer here is *more* accurate than the current documented golden value,
not a Claude regression — but `golden_fields.json`'s own `_readme`
states its "fields" values are "provided directly by the project owner
from the physical tags/tickets," not derived from any OCR/vision output
including Claude's, so this session deliberately did **not** edit that
file to "fix" the value based on its own visual read (that would mean
the system under test partly defining its own ground truth). **Left
open for the project owner**: whether to update
`golden_fields.json`'s `AddieTag.jpg` → `manufacturer` to
`"FORD MOTOR CO."` (matching the physical label) plus add a
`known_ocr_limitations` entry documenting that Tesseract drops the
trailing period, or leave it as-is. Either way, this is a real, working
proof that `HDTTOOLS_OCR_BACKEND=claude` calls genuine Claude vision
end-to-end successfully for all three doc types — the one mismatch is a
fixture-precision question, not a broken extraction path.

✅ **Resolved by the project owner, 2026-09-09: updated to
`"FORD MOTOR CO."`.** `golden_fields.json`'s `AddieTag.jpg` →
`manufacturer` now reads `"FORD MOTOR CO."` (matching the physical
label), with a `known_ocr_limitations` entry documenting that real
Tesseract drops the trailing period. Ripple effects confirmed for real,
not assumed: `tests/test_real_photo_ocr_accuracy.py`'s manufacturer case
for this photo moved from a plain pass to `xfail(strict=True)` (3→4
total xfails app-wide, `584 passed, 3 skipped, 4 xfailed` full-suite);
`tests/test_pass_pool_regression.py`'s `mismatched == known_ocr_limitations`
set-equality check needed no code change (manufacturer now correctly
appears on both sides); `tests/test_streamlit_app.py`'s full walkthrough
already skips any field listed under `known_ocr_limitations`, so it
needed no change either. Re-ran the real External-tier test once more
after the fix: all 3 doc types now pass cleanly, including `truck_tag`.

---

## 🐛 Real bug: Streamlit Community Cloud deploy crashed on tkinter import — found and fixed 2026-09-18

**The bug**: deploying `streamlit_app/app.py` to Streamlit Community
Cloud (the app's first real hosted deployment) crashed at import time:
`ImportError: libtk8.6.so: cannot open shared object file` from
`tkinter/__init__.py`, via `app.py` → `hdttools.scale_ticket` →
`hdttools.review_form` → `import tkinter as tk`. Streamlit Cloud's
Python 3.14 image doesn't ship tkinter's system library — a headless
server image has no display to back a GUI toolkit.

**Why this was surprising**: `app.py` never calls anything
tkinter-based. It only ever calls the headless `extract_*_fields`
functions (item #16) — `review_and_edit`/`select_image_file` exist
solely for the desktop CLI's interactive `read_*_tag()` flow. But
`scale_ticket.py`/`trailer_tag.py`/`truck_tag.py` each do a *module-level*
`from .review_form import review_and_edit` and (via `vision_client.py`)
`from .file_picker import select_image_file, prompt_vehicle_name` —
so merely importing the module for its headless function pulls in
tkinter transitively, unconditionally, whether or not the tkinter-based
functions are ever called. `src/hdttools/__init__.py` already had a
`try/except ImportError` guard around this for `import hdttools` at the
package level (comment there: "tkinter isn't always present ... e.g.
some Docker/Streamlit Cloud images"), anticipating exactly this class of
problem — but that guard doesn't help `from hdttools import
scale_ticket`, which imports the submodule directly and bypasses it.
`src/hdttools/api/main.py` (FastAPI) has the identical latent bug, just
never triggered because it hasn't been deployed to a tkinter-less host
yet.

**The fix**: pushed the same "tkinter is optional" pattern down into the
two modules that actually do the importing — `file_picker.py` and
`review_form.py` — instead of only guarding it one level up. Each now
wraps its own `import tkinter`/`from tkinter import ...` in
`try/except ImportError`, setting the names to `None` on failure, so the
module itself always imports successfully. `select_image_file()` and
`review_and_edit()` each check for `None` as their first statement and
raise a clear `RuntimeError` ("tkinter is not available in this
environment... use the headless extract_*_fields functions instead")
rather than letting a bare `AttributeError`/`ImportError` surface deep
inside tkinter's C extension. `tests/test_file_picker.py`'s existing
`monkeypatch.setattr(file_picker.tk, "Tk", ...)`-style tests keep working
unchanged, since `tk`/`filedialog`/`ttk` are real module attributes
whenever tkinter genuinely is present.

**Verification**: new `tests/test_optional_tkinter_import.py` — a real
subprocess with `sys.modules["tkinter"] = None` (forces any `import
tkinter` to raise `ImportError`, simulating the actual missing-library
condition rather than monkeypatching this test process's own already-
imported modules) — confirms `hdttools.scale_ticket`/`trailer_tag`/
`truck_tag`/`file_picker`/`review_form` all import cleanly, and that
calling `select_image_file`/`review_and_edit` under that condition
raises the new clear `RuntimeError`. Watched it fail for real against
the un-fixed code first (`ModuleNotFoundError: import of tkinter halted`,
matching the real Streamlit Cloud traceback almost verbatim) before
implementing the guard. Also manually reproduced the exact production
scenario against the real `streamlit_app/app.py` file (not just the
`hdttools` submodules) via the same `sys.modules["tkinter"] = None`
trick — clean import — then launched the real app with `streamlit run`
and confirmed it serves `HTTP 200` locally. Full `uv run pytest -q`
suite: `585 passed, 3 skipped, 4 xfailed` (up from 584/3/4 — the one new
test), unaffected otherwise.

---

## 🐛 Real bug #2: Streamlit Community Cloud deploy crashed on `anthropic` import — found and fixed 2026-09-18 (same day as the tkinter fix above)

**The bug**: the very next redeploy after the tkinter fix crashed
differently: `ModuleNotFoundError: No module named 'anthropic'`, via
`app.py` → `hdttools.scale_ticket` → `hdttools.vision_client` →
`import anthropic`. Root cause, confirmed from the deploy log's own
`WARN`: Streamlit Community Cloud detected three possible dependency
sources (`streamlit_app/requirements.txt`, `uv.lock`, `pyproject.toml`)
and chose `streamlit_app/requirements.txt` — a separately maintained
file that only ever listed `streamlit`, `pillow`, `pytesseract`, and had
silently drifted out of sync with `pyproject.toml`'s real dependency
list (which does include `anthropic`) ever since item #16 added the
Claude-vision backend.

**Same shape as bug #1 above**: a module-level `import` of a dependency
the *deployed configuration* never actually exercises (this Streamlit
deployment runs `HDTTOOLS_OCR_BACKEND` at its default, `"tesseract"` —
`vision_client.extract_via_claude` is never called) still crashed the
whole app at import time, because `vision_client.py` imported
`anthropic` unconditionally rather than only when the Claude-vision path
is actually used.

**The fix, mirroring bug #1's pattern exactly**: `vision_client.py` now
wraps `import anthropic` in `try/except ImportError`, setting it to
`None` on failure; `extract_via_claude()` checks for `None` as its first
statement and raises a clear `RuntimeError` ("install it, or leave
HDTTOOLS_OCR_BACKEND unset/'tesseract' to avoid needing it") instead of
crashing app-wide at import time. `tests/test_vision_client.py`'s
existing `monkeypatch.setattr(vision_client.anthropic, "Anthropic", ...)`
keeps working unchanged, since `anthropic` stays a real module attribute
whenever it genuinely is installed. Also added `anthropic>=0.120.2` to
`streamlit_app/requirements.txt` itself (matching `pyproject.toml`'s
pin) — belt-and-suspenders, so if this specific deployment is ever
switched to `HDTTOOLS_OCR_BACKEND=claude`, it will actually work rather
than hit the new clear error instead of a crash.

**Verification**: new `tests/test_optional_anthropic_import.py`, same
real-subprocess-with-`sys.modules[...]=None` technique as bug #1's test
— watched it fail for real first (`ModuleNotFoundError: import of
anthropic halted`, matching the real traceback) before implementing the
guard. Also re-ran the same manual check against the real
`streamlit_app/app.py` file with `sys.modules["anthropic"] = None` —
clean import. Full `uv run pytest -q` suite: `586 passed, 3 skipped, 4
xfailed` (up from 585/3/4 — the one new test), unaffected otherwise.
**Lesson for next time**: `streamlit_app/requirements.txt` is a second,
manually-maintained dependency list that doesn't auto-track
`pyproject.toml` — worth checking by hand after any future change to
`pyproject.toml`'s base `dependencies`, since Streamlit Cloud prefers it
over `uv.lock`/`pyproject.toml` whenever it's present.

---

## 🔀 Decided: Tesseract dropped, Claude-vision-only OCR going forward — 2026-09-21

**Decided** (real project decision, confirmed directly with the user —
not just a working assumption for analysis purposes): Tesseract is being
retired as an OCR backend for Web/Streamlit. Claude-vision
(`vision_client.extract_via_claude`, the path item #16 above added
2026-09-09) becomes the only OCR backend once this ships. Android is
unaffected — it never had a Tesseract path.

**Why now**: surfaced while researching web hosting and the accounts/
paywall entitlement question (`ClaudePlans/2026-09-21-research-web-
hosting-and-entitlement-tradeoffs.md`'s addendum). Two of item #11's
2026-08-24 findings above directly motivated it — Tesseract fails on all
10 real-world raw photos in the test set while Claude vision handles the
same 10 with no preprocessing — plus the practical benefit that dropping
Tesseract removes the one hard blocker on edge-runtime hosting options
(Tesseract needs a real OS process; Claude vision is a plain HTTPS call).

**What this changes, once implemented** (not yet — tracked as
`NEXT_STEPS.md` roadmap item #22, not started):
- The free tier stops being "free Tesseract scan" and becomes
  "manual-entry-only" (scan-tokens = 0). No free OCR path survives.
- Item #16's `HDTTOOLS_OCR_BACKEND` flag and its Tesseract branch become
  dead code and get removed rather than kept as a build-time choice.
- Every scan on both platforms converges to the same shape Android's
  `workers/scan-proxy` already implements: check a credit, call Claude,
  deduct. Cost-gating correctness on that path becomes load-bearing for
  *all* scanning, not just Android's paid tier — there's no free
  local-compute fallback left to silently degrade to if gating has a
  gap.
- The known Tesseract-specific limitations documented earlier in this
  file (no-auto-crop needing a tight isolated photo, the dropped-digit
  misread class) become moot rather than needing an eventual fix.

**Not decided by this**: the separate entitlement-source-of-truth and
scan-gating-unification questions — see
`ClaudePlans/2026-09-21-entitlement-and-scan-gating-unification-impacts.md`,
still open, `NEXT_STEPS.md` item #20.

✅ **Real bug reproduced live, 2026-09-21, same day as the re-skin
verification pass** — the user tried a real truck-tag photo scan
against the freshly re-skinned Web wizard and reported "the truck label
scan didn't appear to work." Traced it end-to-end: the API call
genuinely succeeded (`200 OK`, confirmed in the `uvicorn` access log)
and the frontend's select-photo → Extract Data → Review flow all worked
mechanically (confirmed via a `puppeteer-core` walkthrough with a clean
reference photo, which populated the Review form correctly) — so this
isn't a re-skin regression. The real cause is the Tesseract-blank-fields
failure mode from finding #1 above, reproduced fresh against a real,
uncropped phone photo already in the repo
(`ExampleDocs/scans/truck/f150_blue_goose_uncropped/20260824_141527.jpg`):
Tesseract (today's default backend — `HDTTOOLS_OCR_BACKEND` is unset in
the dev environment) returned **every field null**, which the UI
correctly renders as a blank Review form — indistinguishable from
clicking "I don't have this image," so a user has no way to tell "OCR
ran and found nothing" from "OCR didn't run." Restarting the same
backend with `HDTTOOLS_OCR_BACKEND=claude` against the exact same photo
returned a fully correct read (manufacturer, VIN, GVWR, both GAWRs, tire
specs). This is not a new bug — it's a live, user-facing confirmation of
the exact failure mode that already motivated the Tesseract-drop
decision above; no code change made here, since item #22 already tracks
the real fix. Left the dev server running on `HDTTOOLS_OCR_BACKEND=claude`
for the rest of this session so the user's own testing actually works,
rather than leaving it on the known-broken default.

✅ **Done, screen-level UI re-skin (roadmap item #23, Web half) —
2026-09-21.** Full plan: `ClaudePlans/2026-09-21-screen-reskin-refresh-
screens.md`. Restyled the 7 "🔄 Refresh" Web screens to match the
`RigCheck Web` design canvas
(`https://claude.ai/artifact/XAShfYmhqyvjyJKQmjPcyQ`), same scope
exclusions and the same two standing decisions as the Android half (see
`ARCHIVE_ANDROID.md`'s matching entry): preserve every screen's existing
interaction behavior (no UX redesign), and the mockups' "Upgrade to
Claude scanning" teaser banners render as static/inert sections with a
disabled button (no real Paywall target until item #20 ships).

Files changed: new `components/Footer.tsx` (didn't exist before —
wordmark, Dashboard/History nav, disclaimer + copyright line, wired into
`App.tsx` below the routed screen content); `Header.tsx`'s nav reworked
from plain text buttons to filled pills on the active item (same
props/behavior, visual-only); `StepPills.tsx` rewritten from flat pills
to numbered-circle-plus-connector-line, with a "Rig" step added at the
front (the wizard's `step` prop already ran 0-4, so this needed no new
plumbing — just the label array and render logic); `Dashboard.tsx` (new
hero section — headline/subtext/CTA + a static 3-step icon graphic, "Your
Rigs" 4-up card grid with a colored dot + "Start check" link, a static
purple "Upgrade" teaser banner) and `History.tsx` (client-side filter
pills — All rigs / per-rig / Within limits / Over limit — plus a
table-style row grid) both gained a `onGoHistory`/`recentRigs` prop
respectively to support the new "View history" link and the truck+trailer
join column; `RigStep.tsx` (bordered radio-card-styled rows, kept as
plain clickable divs — **not** actual radio inputs — since the existing
behavior is click-to-navigate-immediately, not the mockup's
select-then-Continue); `UploadStep.tsx` (dashed dropzone with icon +
"Choose photo" button, a "What we read" sidebar card built from the
module's own `fields` list rather than new fabricated copy); `ProcessingStep.tsx`
(circular SVG progress ring + 3-item checklist); `ReviewStep.tsx`
(heading/spacing pass only — the mockup's split photo-preview panel and
per-field low-confidence borders were **not** built, since neither a
persisted photo nor per-field confidence data exists anywhere in the
Web pipeline to back them; fabricating either would have been fake UI,
not a restyle); `ResultsStep.tsx` (two-column layout: existing verdict
band + breakdown list on the left, a static "Scan the label again with
Claude" teaser card on the right, both scope-boundary-approved as
static/inert).

**Real scope adjustment made while building, not asked about first**:
the plan assumed `Dashboard.tsx`'s "Recent checks" cards could reuse
`ResultsStep.tsx`'s per-axle progress-bar rendering, but `HistoryEntry`
(`types.ts`) only ever stored `id`/`date`/`rigNickname`/`verdict` — no
per-axle breakdown survives past the moment a check completes. Extending
`HistoryEntry` to carry the full breakdown would have been a real data-
shape change, which the plan's own Definition of Done ruled out. Built
the cards with only what's real (verdict badge + a `recentRigs`-joined
truck/trailer subtitle) instead of fabricating axle bars against data
that doesn't exist.

**Test-file updates** (structure changed, not deleted, per
`TESTING.md`): `App.smoke.test.tsx` and `Dashboard.test.tsx`'s/
`History.test.tsx`'s nickname assertions switched to `getAllByText`
where the Footer/filter-pills now duplicate text that used to be
unique; `Dashboard.test.tsx` calls gained the new `onGoHistory` prop.
`npx tsc -b`, `npx vitest run` (71/71 passing), and `npm run build`
(Vite production build) all pass clean.

**Verified for real in a browser**, not just via tests: booted both
`vite` (port 5173 — the FastAPI backend's CORS allow-list is hardcoded
to that origin, so a non-default port silently produces "Failed to
fetch") and the real `uvicorn` backend (`uv run uvicorn
hdttools.api.main:app --port 8000`), then drove the full wizard flow
(Rig → Truck → Trailer → Scale → disclaimer → Results → back to
Dashboard) with `puppeteer-core` pointed at the machine's existing
Chrome install (no browser download needed), screenshotting every
screen and comparing each against its `.dc.html` mockup. Left
**uncommitted** pending explicit commit approval, same as the Android
half.
