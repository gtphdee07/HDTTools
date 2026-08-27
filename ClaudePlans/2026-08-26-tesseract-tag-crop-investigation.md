# Investigate and decide: fixing Tesseract's un-cropped-tag failure

## Context

`NEXT_STEPS.md` item #11 (closed 2026-08-24) found that Tesseract OCR
fails to extract *any* of the three weight fields from a realistic,
un-cropped phone photo of a compliance tag (tag as one region within a
wider dashboard/door-jamb shot) — regardless of lighting/angle quality.
Claude vision doesn't share this limitation. The fix itself was never
built; it's tracked as a living gap under `NEXT_STEPS.md`'s "🧪 Tests
still outstanding" section, currently phrased as "needs either an
auto-crop/tag-isolation preprocessing step in `ocr_common.py`, or
documented in-app guidance."

This document is a **handoff brief for a fresh session** to investigate
and decide the approach, then plan the implementation — not a build-it-now
plan. The current session accumulated a lot of unrelated context (an
Android test-pool build-out, a documentation sweep); this decision
deserves its own clean investigation rather than continuing to load
context here. Give this file's content to a fresh Claude Code session
in this repo (`HDTTools`) as its starting prompt.

## Already-confirmed facts (don't re-derive these)

- **Root cause is framing, not lighting**: item #11's finding was that
  10 real photos of the same tag (1 clean shot + 9 at varying angle/
  shadow/glare) all fail the same way when un-cropped — "regardless of
  lighting/angle quality." The problem is that the tag is a small region
  within a much wider shot, not image quality.
- **Current preprocessing does no cropping at all.**
  [ocr_common.py](src/hdttools/ocr_common.py)'s `preprocess_image()`
  (line 47) only does grayscale conversion, `ImageOps.autocontrast`, and
  an upscale if width < 1600px. No OpenCV/`cv2` dependency exists
  anywhere in [pyproject.toml](pyproject.toml) — only `pytesseract`.
  `ocr_text()` (line 57) calls `pytesseract.image_to_string(image,
  config="--psm 6")`.
- **The regression fixtures already exist and are real**: the 10 F-150
  photos live at `ExampleDocs/scans/truck/f150_blue_goose_uncropped/`
  with a `vehicle.json` (`pool: "fail"`, `expected_none_fields:
  ["manufacturer", "gvwr_lb", "front_gawr_lb", "rear_gawr_lb"]`),
  auto-discovered by `scripts/vehicle_discovery.py` and exercised by
  `tests/test_fail_pool_regression.py`. **Any fix that makes some of
  these photos start succeeding must update this test's expectations,
  not just add new tests** — `NEXT_STEPS.md` already flags this.
  Android has its own duplicate fixture at
  `android/app/src/androidTest/assets/scans/truck/f150_blue_goose_framing_gap/`
  with the same `expected_none_fields` shape (see
  `android/app/src/androidTest/java/com/rigcheck/app/testsupport/ScanFixturePool.kt`).
- **No crop UI exists on either platform today** (confirmed via grep,
  2026-08-26) — this would be new work on both, not an extension of an
  existing component.
- **Web's upload entry point**: [UploadStep.tsx](web/src/wizard/UploadStep.tsx)
  — plain `<input type="file">` (line 39), `onFileSelected(file: File)`
  callback, plus an existing "I don't have this image" skip button
  (line 75) that already lets the flow proceed with blank fields. Any
  crop step would sit between file selection and the existing
  extract/upload call.
- **Android's capture path**: `RigCheckViewModel.kt` and
  `PhotoEncoding.kt` (`data/PhotoEncoding.kt`) own the real resize/
  compress pipeline (1600px long edge, JPEG quality 85) that runs before
  a photo is sent to the Worker. A crop step would need to run before
  this encoding step, on the original captured bitmap.
- **This project's default posture is human-in-the-loop over automation**:
  every platform already requires mandatory manual review of OCR results
  before use (no confidence-based bypass anywhere), and this project has
  a documented preference for real/manual verification over trusting an
  automated heuristic to be right (see the "duplicate, not inherit"
  decision behind Android's own Claude-vision test pool, `NEXT_STEPS.md`
  item #13). Weigh this when comparing automated-crop vs. manual-crop
  options below — it's not a neutral tiebreaker, it's this project's
  track record.

## Candidate approaches (not yet decided — investigate, then decide)

1. **In-app guidance only.** UI copy/validation telling users to
   photograph just the tag tightly, no new image-processing or crop UI.
   Cheapest. Does not help the 10 existing fail-pool photos (already
   taken) and is unenforceable — a user can still submit a wide shot.

2. **Tesseract-self-referential auto-crop (spike first).** Use
   `pytesseract.image_to_data()`'s word-level bounding boxes to find the
   densest text cluster on the *uncropped* image, crop to that region
   with padding, then re-run OCR. No new dependency. **Real feasibility
   risk, untested**: if Tesseract already returns near-garbage on the
   wide shot (which is exactly the failure mode), the same weak pass may
   also fail to produce usable bounding boxes to crop to — this could be
   circular and simply not work. Spike this against the real 10
   fail-pool photos before committing to it as the design.

3. **OpenCV-based tag detection.** Contour/edge detection to find the
   tag's rectangular boundary independent of text recognition, then
   crop. More likely to be robust than option 2, but adds a new
   dependency (`opencv-python` or similar) to `pyproject.toml` and more
   implementation/test surface. Only clearly worth it if option 2's
   spike fails.

4. **Manual crop-box UI on Web + Android.** User drags a bounding box
   over the photo (before/instead of any auto-detection) to indicate the
   tag region; the app crops to exactly that box before OCR runs.
   Deterministic — no detection heuristic to get wrong. Fixes the
   problem going forward on both platforms; does not retroactively fix
   the 10 existing fail-pool photos unless someone replays them through
   the new tool once. Cost is real UI/UX work on *two* platforms (a
   drag-rectangle-over-image component in React; a Compose gesture-based
   crop overlay in Kotlin) rather than one shared Python function — a
   different kind of effort than options 2/3, and a different shape of
   fix than what `NEXT_STEPS.md` currently describes (UI feature, not a
   backend algorithm). Most consistent with this project's
   human-in-the-loop track record (see above).

## What the fresh session should actually do

1. Read `NEXT_STEPS.md`'s roadmap item #11 reference and "🧪 Tests still
   outstanding" section, and `ARCHIVE_WEB_STREAMLIT.md`'s full item #11
   narrative, for the complete original finding.
2. Run the option-2 spike for real: take one or more of the real
   uncropped photos in `f150_blue_goose_uncropped/`, call
   `pytesseract.image_to_data()` on the un-preprocessed image, and check
   whether a usable bounding box for the tag's text cluster comes back.
   Report the real result — don't assume either way.
3. Based on the spike's real outcome plus the tradeoffs above, propose a
   recommendation to the user (via `AskUserQuestion` if genuinely
   ambiguous, per this project's standing convention) among: guidance
   only, Tesseract-self-referential crop (if the spike worked), OpenCV
   detection, manual crop-box UI, or some combination (e.g., manual
   crop-box now + guidance copy, deferring OpenCV).
4. Once a direction is chosen, write a real implementation plan
   following `TDD_METHODOLOGY.md` (failing test first) and `TESTING.md`'s
   Minor/Major/Interface categorization — including how
   `tests/test_fail_pool_regression.py` and Android's
   `ScanFixturePoolTest`/`f150_blue_goose_framing_gap` fixture need to
   change if any of the 10 fail-pool photos are expected to start
   passing.
5. Update `NEXT_STEPS.md`'s "Tests still outstanding" entry and item #11
   cross-references once a real decision is made, per this project's
   documented archive/sweep conventions in `Claude.md`.

## Definition of Done (for this investigation phase)

- A real spike result exists for option 2 (not assumed).
- A specific approach (or combination) is chosen and confirmed with the
  user, not left open.
- A concrete TDD implementation plan exists for the chosen approach,
  naming exact files to change on each affected platform (Python, and
  Web and/or Android if a crop-UI option is chosen).

## Verification

- The option-2 spike is verified by actually running it against real
  fixture photos and reading the real `image_to_data()` output, not by
  reasoning about it in the abstract.
- Once an approach is implemented (a later session's work, not this
  one), verify via `uv run pytest tests/test_fail_pool_regression.py -v`
  (Python) and/or `.\test-weekly.ps1` (Android, if a crop UI ships
  there) showing the expected, real before/after change in which
  fail-pool photos pass or still correctly fail.
