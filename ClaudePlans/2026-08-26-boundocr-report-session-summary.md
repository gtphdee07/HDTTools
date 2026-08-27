# BoundOCR Report — Session Summary (2026-08-26, updated 2026-08-27)

Keywords for grep: BoundOCR, contour_quad, locate_label, pyzbar, barcode,
EasyOCR, PaddleOCR, PaddlePaddle, PaddleX, Tesseract, pytesseract, Claude
vision, extract_via_claude, truck_tag, F-150, Ford, GM truck, GVWR, GAWR,
RGAWR, GCWR, MAX PAYLOAD, TWR, VIN, xfail, TDD, Red, Green, perspective
correction, warp_to_quad, pad_quad, order_quad_points, gate_fields,
FIELD_VALIDATORS, evaluate_directory, score_image, parse_spec_file,
parse_gm_spec_file, parse_gm_fields, cv2, opencv-contrib-python,
opencv-python-headless, streamlit extra, Python 3.14, onnxruntime,
transformers, hand-crop, deskew, PSM, security pattern, brushed metal,
hitch hardware, false positive, degenerate quad, confidence gate,
f150_good_pic, curly brace, glyph confusion, no-candidate contour.

---

## Executive Summary (what we did and the results)

This session built and evaluated **BoundOCR**
(`src/experiments/BoundOCR/`), an isolated, TDD-built experiment testing
whether local/free image cropping + OCR can extract vehicle data-plate
fields (GVWR, GAWR, etc.) from poor-quality phone photos of truck door
jambs — as a free alternative to the existing, already-working paid
Claude-vision pipeline (`hdttools.truck_tag`). Four localization options
were identified up front (barcode anchor, contour/quad detection,
brightness thresholding, local ML text-detector); the session pursued a
**barcode → contour** pipeline first, per the user's initial choice.

**Barcode localization (pyzbar) was ruled out empirically**: 0 of 10 real
Ford F-150 photos decoded, even after cropping, contrast, upscaling, and
symbology restriction — confirmed not a library bug (pyzbar decodes its
own bundled test images fine). The pipeline was redesigned as
**contour-quad only** (Canny edge detection → `cv2.findContours` →
`approxPolyDP`, unanchored).

Built via strict TDD (Red tests first, confirmed failing, then minimum
Green implementation): `common/ground_truth.py`, `common/confidence.py`
(Tesseract word-confidence + per-field format gating), `common/
geometry.py` (quad ordering, padding, perspective warp), `pipelines/
contour_quad/contour_locate.py` and `pipeline.py`. Reused
`hdttools.ocr_common`/`hdttools.truck_tag_ocr._parse_fields` rather than
duplicating Tesseract setup or field regexes.

**Real result: 0/10 Ford photos fully correct**, even after fixing a
genuine bug (naive bounding-box crop on a rotated quad, replaced with
real perspective correction — which did produce one confirmed
improvement, plus one newly-discovered regression from a degenerate
`order_quad_points` case). A targeted diagnostic — hand-cropping the
clearest Ford photo as tightly and straight as possible and testing
every Tesseract `--psm` mode, raw/grayscale/binarized preprocessing, and
a sweep of deskew angles — proved the bottleneck is **Tesseract's OCR
quality on this label's dense print + diagonal security-pattern
background**, not localization.

A trade study followed: **EasyOCR** (PyTorch-based) gave a dramatic,
confirmed improvement on the same hand-crop (correctly read GVWR/GAWR
values Tesseract garbled) but needs a decent crop first and is much
slower. **PaddleOCR was blocked** — `paddlepaddle` has no Python 3.14
wheels on this project; a claimed paddlepaddle-free workaround (from an
external screenshot) was partially true but didn't actually work, and
was removed after testing (which briefly broke `cv2` via an
`opencv-contrib-python` conflict and dropped the `streamlit` extra — both
fixed and verified). The existing **Claude-vision pipeline scored 4/4 on
both the best and worst Ford photos tested**, including one rotated 90°,
with zero cropping/pipeline work — the clear quality ceiling, at real
per-call API cost.

A **second real vehicle (GM truck)** was added to BoundOCR with its own
field schema (`RGAWR`/`GCWR`/`CURB WEIGHT`/`MAX PAYLOAD`/TWR fields, no
barcode, no security-pattern background). Its hand-crop OCR result was
**8/10 fields correct** — confirming label design/material varies hugely
in OCR-friendliness — but the automated pipeline still scored 0/10
because `locate_label` picked the wrong region entirely (trailer-hitch
hardware instead of the label): a second real, documented localization
false positive.

**Update, 2026-08-27**: the user retook a Ford photo
(`f150_good_pic/20260827_123744.jpg`) with real care — sharp, well-lit,
straight-on, label filling most of the frame. All three engines were
re-run against it. **`locate_label` still failed** (zero contour
candidates cleared the 2%-area threshold at all — a new failure mode,
not the earlier wrong-region false positives). **EasyOCR still crashed
on the raw image** with the same `cv2.resize` bug. A hand-crop bypassing
localization showed real, partial progress: Tesseract got the
manufacturer right (still missed GVWR/GAWR), and **EasyOCR got both
GAWR values exactly right** for the first time on this label — but both
engines independently misread the same `(` as `{` before the GVWR value,
which the field parser's regex doesn't tolerate. **Claude vision scored
100% on every field.** This confirms the original diagnosis rather than
overturning it: a much better photo narrows the gap for local engines
but does not close it, on either localization or recognition.

---

## Next Steps Action Plan (~500 words)

1. **DONE, 2026-08-27**: the user retook a careful Ford photo
   (`f150_good_pic/20260827_123744.jpg`) and it was run through all three
   engines (see the Executive Summary update and the new Full Narrative
   section below for detail). Result: local engines are closer but still
   not there — `locate_label` still finds no usable box on this image
   (new failure mode: zero candidates, not a wrong-region pick), EasyOCR
   still can't take a raw full-resolution image directly, and on a
   hand-crop both local engines are blocked by small, specific glyph
   misreads (a `(`→`{` swap breaking GVWR parsing on both engines; a
   stray space breaking Tesseract's manufacturer match). Claude vision
   scored 100%. This was one photo, not a full 10-image regression set —
   if more retaken photos arrive, extend
   `src/experiments/BoundOCR/tests/test_evaluate_f150_regression.py`
   against them the same way, following the existing `vehicle.json`
   convention.

2. **Confirmed by the 2026-08-27 result above**: the Ford label's
   printing/background (not photo quality) is the real ceiling for local
   engines. Next real options, in likely priority order:
   - Wire **EasyOCR** in as a genuine second BoundOCR pipeline option
     (`pipelines/easyocr_pipeline/` or similar, mirroring `contour_quad`'s
     shape). Needs: (a) adapting field extraction since EasyOCR returns
     individual word/phrase detections with bounding boxes, not flowing
     paragraph text like Tesseract — the existing regex-based
     `_parse_fields`/`parse_gm_fields` approach needs a concatenation or
     spatial-grouping strategy first; (b) always feeding it a crop, never
     the raw full image (confirmed crash: an internal `cv2.resize`
     assertion failure on an extreme-aspect-ratio proposed region); (c)
     accounting for real per-image latency (~6s CPU, ~50s one-time model
     load) if this ever needs to run at scale.
   - Accept Tesseract's ceiling for this specific label style and route
     it to the existing Claude-vision path (already perfect on both
     tested extremes) rather than continuing to chase local-only
     accuracy — a real, legitimate outcome for this experiment, not a
     failure of it.

3. **Fix `locate_label`'s reliability** — now backed by three real,
   documented failure cases, two different failure modes: wrong-region
   false positives (Ford's `20260824_141600.jpg` top-corner artifact;
   GM's trailer-hitch-hardware pick) and outright no-candidate misses
   (`f150_good_pic/20260827_123744.jpg`, where no contour cleared the
   2%-area threshold at all despite a clean, well-lit, close shot).
   Options: stricter area/position plausibility filtering, swapping
   `approxPolyDP`'s corner-hunting for `cv2.minAreaRect` as the primary
   shape estimate, or loosening the Canny/area thresholds to recover
   candidates on cleaner photos without reintroducing false positives on
   cluttered ones (discussed but not yet attempted). This matters
   regardless of which OCR engine wins, since a wrong or missing crop
   defeats any OCR engine equally.

4. **Revisit deferred items** already tracked in
   `ClaudePlans/2026-08-26-boundocr-greenstage-design.md`'s "Deferred
   items" table: `contour_locate`'s non-4-corner fallback branch still
   has no dedicated test; per-field (vs. whole-crop) confidence
   alignment is still a flagged, deferred refinement.

5. **Consider the manual drag-box UI** (Phase 2 of the original
   high-level plan, `ClaudePlans/2026-08-26-boundocr-phase1-high-level-plan.md`)
   sooner rather than later, given automated localization's now
   twice-confirmed real flakiness — `pipeline.extract_from_box` already
   exists as the exact seam this UI needs, unchanged since Phase 1.

6. **Dependency housekeeping**: `pyzbar`, `opencv-python-headless`,
   `easyocr` (+ `torch`/`torchvision`/etc.) remain installed and used;
   `paddleocr`/`paddlex`/`transformers`/`onnxruntime` were cleanly
   removed after the failed PaddleOCR attempt — confirmed via
   `git diff pyproject.toml` and a full test-suite pass.

---

## Full Narrative

### Context and starting options

The task began as pure research (no code): given poor-quality phone
photos of truck data plates defeating the existing Tesseract-based OCR
path, what are viable no-cost, local options to locate the label
boundary before OCR? Four options were identified and compared with
pros/cons (see the very first research pass, not separately filed):

- **Option A** — brightness/color thresholding + largest-bright-blob
  bounding box.
- **Option B** — edge/contour quadrilateral detection ("document
  scanner" style): Canny → `cv2.findContours` → `approxPolyDP`.
- **Option C** — barcode-anchored localization (`pyzbar`/`zbar`), using
  the plate's Code128-style barcode as a robust anchor, then expanding.
- **Option D** — a local pretrained scene-text detector (EAST/CRAFT/
  DBNet-style), explicitly deprioritized ("Option D is out, unless we
  can't find another solution").

The user also asked about a manual drag-to-adjust bounding-box UI as a
complement/fallback — assessed as low implementation difficulty (a day
or so via `streamlit-cropper`/`streamlit-drawable-canvas` or
`react-image-crop`), valuable because it doubles as a free ground-truth
annotation tool.

### Directory/project setup

All new code lives under `src/experiments/BoundOCR/`, explicitly
isolated: no existing file modified, only imported from
(`hdttools.ocr_common`, `hdttools.truck_tag_ocr._parse_fields`). Tests
live under `src/experiments/BoundOCR/tests/` (not the top-level
`tests/`), run via `uv run pytest src/experiments/BoundOCR/tests -v`,
which a bare `uv run pytest -q` (existing full-suite command) does not
pick up. New dependencies (`pyzbar`, `opencv-python-headless`) were
installed at the project level via `uv add` after explicit per-package
confirmation, following a refined install policy the user set mid-session:
ask before installing new toolchains even via `uv add`; new toolchains
default to the G: drive; existing tool configs (`uv`'s own cache/python/
tool dirs) stay on their current C: defaults unless asked; any single
C:-drive write over ~10MB needs fresh confirmation each time (this policy
itself is now saved to auto-memory, `feedback_system_installs.md`).

### Phase 1 — high-level plan (barcode → contour)

The approved Phase 1 plan (`ClaudePlans/2026-08-26-boundocr-phase1-high-level-plan.md`)
specified a **C → B pipeline**: barcode-anchored localization (Option C)
refined by contour/quad detection (Option B), crop, Tesseract OCR (reusing
`preprocess_image`/`ocr_text`), field extraction via
`hdttools.truck_tag_ocr._parse_fields` (reused, not reimplemented — its
field names already matched `F-150Spec.txt`'s ground truth exactly), and
a confidence gate (`pytesseract.image_to_data` word confidences +
per-field format validators) to blank low-confidence fields rather than
guess.

### The barcode dead end (Option C ruled out)

Before writing the planned Red-stage tests for barcode locate, an
empirical spike tested `pyzbar.decode()` against all 10 real F-150
photos, at full resolution and after grayscale/autocontrast preprocessing:
**0 of 10 decoded**. A manually-cropped tight region containing just the
visible barcode also failed, across raw/grayscale/autocontrast/binarized/
2x-upscaled variants, and restricted to Code128/Code39 symbologies
explicitly. To rule out an environment bug, `pyzbar` was tested against
its own bundled test fixtures (`code128.png`, `qrcode.png`,
`qrcode_rotated.png`) — all decoded correctly, confirming the library
itself works and the real photos' barcodes are what defeat it (likely
JPEG compression + the label's diagonal security-pattern background +
handheld blur/skew, though the exact cause wasn't isolated further since
the practical conclusion — abandon Option C for this dataset — didn't
require it).

Given this, the user chose to **drop barcode-anchoring from this
experiment entirely** rather than invest further, keeping `pyzbar`
installed (parked) for a possible future separate pipeline on a different
vehicle. The plan was revised to **contour/quad detection alone
(`contour_quad`)**, unanchored.

A follow-up spike (before committing to the revised Red-stage plan) ran
raw Canny+contour+`approxPolyDP` against 3 real images unanchored,
finding a **mixed but non-trivial signal**: on `20260824_141530.jpg` the
2nd-largest contour was a clean 4-corner match at ~15% of frame area,
plausibly the real label; on `20260824_141600.jpg` the largest contour
was a false positive (a top-left frame artifact, not the label). This
was accepted as a real, bounded risk rather than a dead end, matching
the plan's `pytest.mark.xfail(strict=True, reason=...)` philosophy for
per-image limitations (never a silent skip, never an invented pass-rate
threshold).

### Red stage (contour_quad)

5 test files were written first and confirmed to fail with clean
`ModuleNotFoundError`s (not import typos or wrong fixture paths):
`tests/common/test_ground_truth.py`, `test_confidence.py`,
`tests/pipelines/contour_quad/test_contour_locate.py` (3 cases —
clean synthetic rectangle, a synthetic case mirroring the real
7-corner-vs-4-corner spike finding, and a no-plausible-candidate case),
`test_pipeline.py` (shape-only, real F-150 image), and
`tests/test_evaluate_f150_regression.py` (parametrized over all 10 real
images, no `xfail`s added in advance).

### Green stage (contour_quad) — first real result

Implementation followed the Red tests exactly: `locate_label` sorts
contour candidates by `(0 if corners==4 else 1, corners, -area)` — an
exact-4-corner match always outranks any other candidate regardless of
area, directly encoding the lesson from the spike. `pipeline.py`'s
`detect_and_extract`/`extract_from_box` wired `locate_label` → crop →
`preprocess_image` → `ocr_text` → `_parse_fields` → `gate_fields`.

**Real regression result: 0/10 fully correct.** One partial win
(`141537.jpg` got `front_gawr_lb` right); `141545.jpg` got no box at all.
Per-image diagnosis of the actual crops/OCR text (not assumed) found two
concrete, fixable issues: (1) `extract_from_box` did a naive axis-aligned
bounding-box crop even when the located quad was visibly rotated —
`141530.jpg`'s box was a rotated parallelogram, and its OCR output was
pure noise as a direct result; (2) the quad was cropped tight with no
margin, clipping needed rows out of frame (`141537.jpg`'s GVWR line
missing entirely from its OCR text).

### Perspective-correction + padding fix

The user chose these two specific, bounded fixes ("let's do #1 and #2 as
low hanging fruit") over broader options (Hough-based deskew, `minAreaRect`,
OCR character-confusion regex tolerance). Built via TDD:
`common/geometry.py`'s `order_quad_points` (standard sum/diff corner-sort
trick), `pad_quad` (centroid-radial expansion), `warp_to_quad`
(`cv2.getPerspectiveTransform`/`warpPerspective`, output size from the
quad's own real side lengths). 3 tests, including one synthetic
rotated-rectangle-with-asymmetric-marker case specifically designed to
catch a flip/mirror bug, all passed on the first real run.

**Real before/after, reported honestly:**
- `141530.jpg`: 0 correct fields → **`front_gawr_lb`, `rear_gawr_lb`
  correct** — the fix's confirmed, targeted win.
- `141557.jpg`: previously read `vin`/`vehicle_type` correctly (though
  unscored) → **empty OCR text, a new regression**. Root cause: its
  quad `[(3703,329),(1686,371),(1453,1669),(1423,591)]` is not a
  well-behaved rotated rectangle, and `order_quad_points`'s corner-sum
  heuristic degenerated on it, assigning the **same point to both
  top-right and bottom-right** — a singular perspective transform,
  unusable output.
- No change on the other 7 images. **Still 0/10 fully correct overall.**

Given one real win and one new real regression with no net improvement,
the user decided to **stop pursuing contour_quad further** ("not much
upside to continuing down this path") rather than fix the degenerate-quad
case.

### The OCR-quality diagnostic

Before choosing a next direction, a bounded diagnostic separated
"localization is the bottleneck" from "OCR itself is the bottleneck":
`20260824_141530.jpg` (the clearest existing photo, already visually
confirmed legible) was hand-cropped as tightly and straight as
realistically achievable. Result: **still near-total garbage** from
Tesseract, across every `--psm` mode tested (3/4/6/11/12), raw/
grayscale/binarized preprocessing, and a sweep of deskew angles
(-6/-3/0/+3/+6 degrees — +3° recovered the most alphanumeric characters,
227 vs. 99 at 0°, but still far from clean/parseable text). **Conclusion:
OCR quality, not cropping precision, is the dominant bottleneck** for
this label style — better localization alone cannot fix it.

### OCR-engine trade study

Given the above, the user asked for a trade study of local OCR
alternatives. Candidates compared: **PaddleOCR** (PP-OCRv4/v5, Apache
2.0, strong real-world reputation), **EasyOCR** (CRAFT+CRNN, PyTorch,
MIT), **docTR** (Mindee, Apache 2.0, modular). PaddleOCR was recommended
first based on reputation, pending empirical verification.

**PaddleOCR install failed**: `paddlepaddle` has no wheels for Python
3.14 (`uv add paddlepaddle` — "No solution found... paddlepaddle have no
wheels with a matching Python version tag"). Confirmed clean failure via
`git diff pyproject.toml` (no partial state left).

**EasyOCR installed successfully** (torch 2.13.0 has cp314 wheels). Model
cache redirected to `G:\easyocr-models` per the install policy. Hit and
fixed a real Windows-console Unicode bug in EasyOCR's own download
progress bar (`UnicodeEncodeError` on a `█` block character under the
default cp1252 console encoding) via `PYTHONIOENCODING=utf-8` and
`verbose=False`; a corrupted partial `temp.zip` from the crashed first
attempt was deleted before retrying.

**Real result, apples-to-apples on the same hand-crop**: EasyOCR
correctly read `GVWR: 3221 (7100 LB)`, `FRONT GAWR: 1599 KG (3525 LB)`,
`REAR GAWR: 1724 KG 3800 LB)`, plus reasonable VIN/TYPE — a dramatic
improvement over Tesseract's garbage on the identical input. Caveats,
reported honestly: results come as individual word/phrase detections
with bounding boxes (not flowing text, so the existing `_parse_fields`-
style regex approach needs adapting); ~50s one-time model load + ~6s/
image on CPU; small character slips remain (`"CO"` → `"C0"`, a `"5"` → `"S"`
in the VIN); **crashes on the raw, full 4032x1816 image**
(`cv2.error: ... !ssize.empty() ... in function 'cv::resize'`, an
internal bug when its own detector proposes an extreme-aspect-ratio
region) — it still needs a reasonable crop as input, confirming it
replaces the *recognition* stage, not the whole pipeline.

### Claude-vision ceiling check

To establish a real accuracy ceiling (not assumed), the existing,
already-working Claude-vision pipeline (`hdttools.truck_tag._SYSTEM_PROMPT`/
`_SCHEMA`, `vision_client.extract_via_claude`) was run against the
visually-confirmed best (`141530.jpg`, clear/near-straight) and worst
(`141606.jpg`, rotated 90° but fully legible) Ford photos, real API calls
(ANTHROPIC_API_KEY present in the environment). **Result: 4/4 scored
fields correct on both images**, with zero cropping/preprocessing
pipeline at all. This sharpened the tradeoff: free/local methods
(Tesseract, even EasyOCR) require real engineering and still have real,
unresolved accuracy limits on this label style; the paid path already
works perfectly, at real per-image cost and an API-key/network
dependency.

### PaddleOCR-without-PaddlePaddle investigation

The user shared an external screenshot (an AI-summary-tool answer)
claiming PaddleOCR could run without `paddlepaddle` via a
`PaddleOCR(engine="transformers")` parameter. This was verified rather
than trusted at face value:
- **Partially true**: `paddleocr`'s PyPI metadata (`paddleocr==3.7.0`)
  depends on `paddlex[ocr-core]`, not `paddlepaddle` directly; `paddlex`'s
  (`==3.7.2`) `ocr-core`/`ocr` extras declare no `paddlepaddle` dependency
  either — both installed cleanly on Python 3.14, `pip`/`uv` metadata
  confirmed via direct PyPI JSON queries, not assumed from the
  screenshot.
- **The specific fix was wrong**: `PaddleOCR.__init__`'s actual signature
  (inspected directly, `inspect.signature`) has no `engine` parameter at
  all. Instantiating it reproduced the *exact* real error the screenshot
  referenced — `RuntimeError: Engine 'paddle_static' is unavailable
  because dependency 'paddlepaddle' is not installed` — confirming the
  underlying problem was real even though the shown fix wasn't.
- Found the real alternate-engine mechanism by reading the installed
  package source directly:
  `paddlex/inference/models/engines/onnxruntime.py` exists (not a
  "transformers" engine). Installed `onnxruntime` (has Python 3.14
  wheels, 13.7MB). But the default detection model
  (`PP-OCRv6_medium_det`)'s own config (`inference.yml`) only declares
  `paddle_infer`/`tensorrt` backends, not `onnxruntime` — so installing
  the runtime alone didn't unlock it for this model; making it work
  would need hunting for an ONNX-packaged model variant or reaching into
  internal APIs, judged not worth the uncertain payoff given EasyOCR and
  Claude vision were already confirmed working alternatives.
- **PaddleOCR/paddlex/transformers/onnxruntime were removed**
  (`uv remove paddleocr transformers onnxruntime`) after this
  investigation, at the user's direction.

### Cleanup incident: cv2/streamlit regression, found and fixed

The `uv remove` resync **broke two things**, found and fixed
immediately rather than left for later:
1. `cv2.cvtColor` went missing (`AttributeError: module 'cv2' has no
   attribute 'cvtColor'`) — caused by `paddleocr`'s dependency chain
   having installed `opencv-contrib-python==4.10.0.84` alongside the
   existing `opencv-python-headless`, a well-known OpenCV packaging
   conflict (both provide the same `cv2` namespace); removing one left a
   corrupted hybrid install. Fixed via
   `uv pip install --reinstall opencv-python-headless` (also restored
   `numpy` from a downgraded `2.3.5` back to `2.5.2`).
2. `tests/test_streamlit_app.py` broke at collection
   (`ModuleNotFoundError: No module named 'streamlit'`) — the `uv
   remove` resync only installs the base `dependencies` list, dropping
   the `streamlit` optional-dependencies group that had been present in
   the venv. Fixed via `uv sync --extra streamlit`.

Both fixes were verified: `uv run pytest -q` (existing suite) back to
**554 passed, 3 xfailed**; `uv run pytest src/experiments/BoundOCR/tests`
back to its expected state (10/10 non-regression tests passing, 10
expected Ford regression failures unchanged).

### GM truck — second real vehicle

A new label (`ExampleDocs/scans/truck/gm_truck/GMTruck_FB.jpg` +
`GMTruck-Spec.txt`) was added by the user: a GM "Trailering Information"
label — a genuinely different schema (`RGAWR` instead of split front/
rear GAWR, plus `GCWR`, `CURB WEIGHT`, `MAX PAYLOAD`, and an SAE J2807
section with `CONVENTIONAL TWR`/`GOOSENECK TWR`/two `MAX TONGUE WEIGHT`
values), no barcode, no diagonal security-pattern background (plain
brushed-metal plate).

The provided `GMTruck-Spec.txt` had a real bug — a leftover
`"MFD. BY FORD MOTOR CO"` line copy-pasted from the Ford fixture — fixed
before use as ground truth. Directory placement needed no change:
`ExampleDocs/scans/truck/gm_truck/` already matches
`scripts/vehicle_discovery.py`'s `<truck|trailer|scale>/<vehicle_slug>/`
bucket convention.

Wired in via TDD, reusing the schema-agnostic parts
(`locate_label`/`geometry`/confidence mechanism) and adding only what's
genuinely GM-specific: `common/gm_truck_fields.py::parse_gm_fields`
(regex parser, including a positional resolution for the two
identically-labeled `MAX TONGUE WEIGHT` values, mirroring how
`truck_tag_ocr._tire_specs` already resolves front/rear tire specs
positionally), `common/ground_truth.py::parse_gm_spec_file`,
`FIELD_VALIDATORS` entries for the new numeric fields, an optional
`field_parser` parameter added to `pipeline.detect_and_extract`/
`extract_from_box` (default = Ford's `_parse_fields`, fully
backward-compatible — the existing Ford `test_pipeline.py` needed no
changes), and `common/evaluation.py::evaluate_directory` was finally
built for real (previously deferred pending a second real caller, which
this was) with its own new test.

**Real result**: the automated regression test failed, **0/10 (all 10
fields) scored correct** — `locate_label` picked the wrong region
entirely, a box covering `[(0,0),(1206,0),(1206,466),(0,466)]` (the
trailer-hitch/ball-mount hardware at the top of the 1206x1201 frame),
not the label below it. Diagnosed by hand-cropping the real label
region and re-running the identical OCR + `parse_gm_fields`: **8 of 10
scored fields exact** (VIN, GVWR, GCWR, RGAWR, curb weight, max payload,
conventional TWR, its tongue weight) — only the two `gooseneck` TWR
fields failed, from a real, localized OCR misread
(`"7539 Bete fon Fee"` instead of `"7539 KG / 16620 LBS"`, likely a real
dirt/rust smudge visible over that part of the label in the photo).

This is the opposite failure mode from Ford: **this label's plain
surface is confirmed dramatically more OCR-friendly** (8/10 vs. Ford's
0/10, same OCR engine, no changes), and the sole real blocker here is
`locate_label`'s region selection — now documented with two concrete
real false-positive cases (Ford's `141600.jpg` top-corner pick, GM's
hitch-hardware pick).

No `xfail` was added to either regression test for any of this — every
real result was reported as-is, per the standing "pause and discuss real
results, don't force a pass" discipline established early in this
session and now saved to auto-memory.

### New Ford photo — f150_good_pic (2026-08-27)

The user retook a single Ford F-150 photo with real care
(`ExampleDocs/scans/truck/f150_good_pic/20260827_123744.jpg`, 4032x1816):
sharp, well-lit, straight-on, the label filling most of the frame — a
deliberate attempt to separate "the original 10-photo batch was just a
hard/atypical set" from "this label's printing is fundamentally hard for
local OCR regardless of photo quality." Ground truth matched the existing
`F-150Spec.txt` exactly (same VIN/label, just a much better shot), so no
new spec fixture was needed. All three previously-explored engines were
re-run against it as an ad-hoc diagnostic spike (scratch scripts, not
added to the permanent `pytest` suite — a bounded, one-off check, not a
new regression fixture yet).

**1. contour_quad pipeline (`locate_label` + Tesseract), full automated
run**: failed completely — `detect_and_extract` returned `label_found:
False`, `box: None`. Direct inspection of `locate_label`'s internals
(Canny edges → `cv2.findContours`, no dilation-then-threshold change)
showed **zero contours cleared the `_MIN_AREA_FRACTION = 0.02` area
threshold at all** (largest raw contour: ~64,654 px² against a required
~146,442 px² minimum on this image's 7,322,112 px² frame) — a **new
failure mode**, distinct from the earlier wrong-region false positives
on Ford's `141600.jpg` and GM's hitch-hardware pick. The label's edge
against the truck's dark paint apparently still doesn't trace as one
clean closed contour even on a much cleaner, closer photo.

**2. EasyOCR directly on the raw 4032x1816 image**: crashed again with
the identical `cv2.error: ... !ssize.empty() ... in function
'cv::resize'` seen in the original trade study — confirms this is a
structural EasyOCR limitation (an internal detector proposing an
extreme-aspect-ratio region on a large, uncropped frame), independent of
how good the underlying photo is. EasyOCR still cannot be pointed at a
raw phone photo; it always needs a crop from somewhere else first.

**3. Hand-crop test** (a generous manual crop around the visible label,
bypassing `locate_label` entirely, to isolate whether the better photo
helps the OCR engines themselves — same methodology as the original
OCR-quality diagnostic):
- **Tesseract** (`ocr_common.preprocess_image` + `ocr_text` +
  `truck_tag_ocr._parse_fields`): manufacturer correct
  (`"FORD MOTOR CO."`), VIN/tire fields visible in the raw text, but
  **GVWR/GAWR all failed to parse**. Root cause, confirmed by reading
  the raw OCR text directly: Tesseract rendered the label's
  `GVWR: 3221 KG (7100 LB)` as `"GVWR: 3221 KG {7100 LB) -"` — a literal
  curly brace in place of the opening parenthesis. `truck_tag_ocr._kg_lb`'s
  regex (`rf"{label_pattern}\W{{0,4}}([\d,]+)\s*KG\s*\(?\s*([\d,]+)\s*[L1I][B8]"`)
  only tolerates a real `(` or nothing before the value — a `{` blocks
  the match outright, so `gvwr_kg`/`gvwr_lb` both came back `None`
  despite the correct digits sitting right there in the text.
- **EasyOCR** on the identical hand-crop: **`front_gawr_lb` and
  `rear_gawr_lb` both came back exactly correct** (3525/3800) for the
  first time on this label — its rendering of those two lines happened
  to have clean or absent parentheses. VIN was read perfectly
  (`1FTFW3L50TFB54677`). But **manufacturer failed**
  (`_parse_fields`'s `r"(?:MFD\.?\s*BY|...)"` pattern requires `MFD`
  immediately followed by an optional `.` with no space before it;
  EasyOCR's text read `"MFD . BY FORD MOTOR Co_"` — a stray space before
  the period broke the match) and **GVWR failed on the same
  curly-brace-for-parenthesis substitution as Tesseract**
  (`"3221 KG { 7100 LB)"`) — an odd coincidence that both engines
  independently misread that one glyph the same way, suggesting a real
  print/rendering artifact on the physical label itself at that specific
  spot rather than two unrelated engine quirks.
- **Claude vision** (real API call, confirmed with the user first given
  the per-call cost): **100% correct on every scored field** — manufacturer,
  VIN, date, GVWR, both GAWR values, both full tire specs, in one call,
  with zero cropping/preprocessing pipeline.

**Conclusion**: this result confirms rather than overturns the earlier
diagnosis. A much better photo measurably helps — EasyOCR crossed a real
threshold it hadn't before (both GAWR values exactly right) — but it
neither fixes automated localization (still fails, now for a different
reason) nor fully closes the recognition gap (both local engines are
each one small, specific glyph confusion away from a clean result: a
curly brace, a stray space). Claude vision remains the only path tested
that is unaffected by either problem.

### End-of-session state

- `uv run pytest -q` (existing production suite): **554 passed, 3
  xfailed**, unaffected throughout.
- `uv run pytest src/experiments/BoundOCR/tests -q`: **14 passed, 11
  failed** (10 expected Ford regression failures + 1 new, diagnosed GM
  regression failure) — an honest, current snapshot, not a target to
  hide.
- Dependencies installed and kept: `pyzbar`, `opencv-python-headless`,
  `easyocr` (+ `torch`/`torchvision`/`scipy`/etc.). Removed:
  `paddleocr`, `paddlex`, `transformers`, `onnxruntime`.
- **2026-08-27**: one retaken Ford photo (`f150_good_pic/20260827_123744.jpg`)
  tested photo quality as a confound directly. Result: photo quality is
  a real but partial factor — it improved EasyOCR's recognition (both
  GAWR values now exact) but did not fix automated localization
  (`locate_label` still fails, a new zero-candidate failure mode) or
  fully close the recognition gap on either local engine (both still
  blocked by small, specific glyph misreads). Claude vision scored 100%.
  This was a one-off diagnostic spike (ad-hoc scratch scripts), not yet
  folded into the permanent `pytest` regression suite.
