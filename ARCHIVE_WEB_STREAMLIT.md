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
