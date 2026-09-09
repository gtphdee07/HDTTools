# Research + spike: camera-preview bounding-box overlay for tag framing

## Context

Users photographing a compliance tag/data plate often frame the shot too
wide or off-focus, which is a large part of why the OCR pipeline
struggles on real photos (see `NEXT_STEPS.md` items #11/#17). Rather than
fix framing after the fact (auto-crop, which item #17's BoundOCR
experiment found unreliable), this task investigates fixing it *before*
capture: overlay a bounding box on the live camera view showing the user
where to position/focus the tag.

Explored today: capture is currently a **system camera intent**, not a
custom preview — `ChooserScreen.kt` (`android/app/src/main/java/com/rigcheck/app/ui/screens/ChooserScreen.kt`,
lines 56-76) launches `ActivityResultContracts.TakePicture()` against a
`Uri` from `ScanPhotoStorage.kt`'s `createScanPhotoUri`; the stock camera
app owns the entire UI, no `CAMERA` permission is needed today. No
CameraX, MLKit, or Accompanist-permissions dependency exists anywhere in
`android/gradle/libs.versions.toml`/`app/build.gradle.kts`, and no
overlay/`Canvas`/bounding-box pattern exists anywhere in the Compose
codebase. A framing-guide overlay therefore requires a genuinely new
custom camera preview — this is real, non-trivial scope, which is why
this is a **research + spike task for a sub-agent**, not a build-it-now
plan. The result should be a working feasibility spike plus a written
recommendation, not a production feature merged into the real scan flow.

Downstream, whatever the spike captures only needs to produce the same
kind of `Uri`/file `ChooserScreen`'s `onPhotoScanned(uri)` already
receives — from there it's unchanged: `RigCheckNavHost.kt` (line 72) →
`RigCheckViewModel.performScan(...)` (`ui/RigCheckViewModel.kt`, line
123) → `PhotoEncoding.kt`'s `encodePhotoForScan` → `ScanApiClient.scan(...)`.
`ReferenceImageCard.kt`'s `SunsetOrange` accent + `RoundedCornerShape(14.dp)`
is this app's existing visual language and should inform the overlay's
styling.

## Goal

Prove (or disprove) that a live camera-preview bounding-box overlay is
feasible in this app, with a real on-device spike backing the answer —
not a written guess. Produce a concrete recommendation for whether/how
to build it for real.

## Sub-agent brief (hand this to the sub-agent verbatim)

**What to do** (<50 words): Research + spike a live camera-preview screen
with a bounding-box overlay guiding users to frame the compliance tag.
Investigate feasibility (permission flow, overlay alignment, preview
performance), build a minimal isolated proof-of-concept, and report
findings/recommendation — don't wire it into production navigation yet.

**What framework to use** (<50 words): Use CameraX
(`androidx.camera.core`/`camera2`/`lifecycle`/`view`) for the live
preview + capture, wrapped in Compose via `AndroidView(PreviewView)`.
Draw the overlay with Compose's `Canvas`/`drawRect`, not a custom View.
No CameraX exists in this app yet — it's a new dependency.

**What the quality goal is** (<50 words): Overlay must stay correctly
positioned across device sizes/orientations and camera aspect ratios,
match the app's existing visual style (`SunsetOrange` accent, rounded
corners), add no visible preview lag, and the captured photo must work
unchanged through the existing `PhotoEncoding`/scan pipeline.

## Steps

1. Add CameraX dependencies (`camera-core`, `camera-camera2`,
   `camera-lifecycle`, `camera-view`) to `libs.versions.toml`/
   `app/build.gradle.kts`, and add the `CAMERA` runtime permission to
   `AndroidManifest.xml`.
2. Build an **isolated** spike screen (new package, e.g.
   `ui/experiments/cameraoverlay/`, not referenced from
   `RigCheckNavHost.kt` or `ChooserScreen.kt`) containing:
   - A `PreviewView`-backed CameraX preview (permission request →
     `ProcessCameraProvider` → `Preview` use case bound to it).
   - A `Canvas` overlay drawing a fixed guide rectangle sized/positioned
     to approximate a compliance tag's real aspect ratio, styled with
     the app's existing accent/corner-radius conventions.
   - A capture button using CameraX's `ImageCapture` use case, saving to
     a `Uri`/file shaped the same way `ScanPhotoStorage.kt`'s
     `createScanPhotoUri` already produces.
3. Run the spike for real on an emulator or device (see
   `DEV_ENVIRONMENT.md` for the AVD to use): grant the permission,
   confirm the preview renders, confirm the overlay stays aligned across
   at least two orientations/aspect ratios, capture a photo, and confirm
   the resulting file is a valid JPEG.
4. Feed the captured file through `encodePhotoForScan` (a scratch
   test/script is fine) to confirm the spike's output is drop-in
   compatible with the existing pipeline — verify this for real, don't
   assume it from the code shape alone.
5. Write a short report: what worked, any real friction points
   (permission UX, preview lag, alignment issues across devices), and a
   concrete recommendation — replace `ChooserScreen`'s flow entirely,
   add it as an alternative "Guided Scan" option, or abandon if a real
   blocker surfaced. Do not update `NEXT_STEPS.md` or wire the spike into
   production — leave that for a follow-up decision once the report is
   reviewed.

## Definition of Done

- A real, on-device working CameraX preview + overlay spike exists in an
  isolated location, untouched production navigation/screens.
- The spike's captured photo is verified (not assumed) to work through
  `encodePhotoForScan` unchanged.
- A written report covering real permission-flow behavior, overlay
  alignment across at least two aspect ratios/orientations, any observed
  preview lag, and a clear go/no-go recommendation.

## Verification

- Run the spike on an emulator/device (`./gradlew installDebug` or an
  Android Studio run) and visually confirm the overlay renders and
  stays aligned as the device rotates or the preview aspect ratio
  changes.
- Manually confirm the captured file is a valid JPEG and that
  `encodePhotoForScan` accepts it without changes.
- No automated test suite is required for this spike (consistent with
  how BoundOCR's own early feasibility spikes were treated, per
  `ClaudePlans/2026-08-26-boundocr-report-session-summary.md`) — if the
  recommendation is to proceed to a real feature, note that the
  production version would need Minor/Major coverage per
  `android/TESTING.md`'s existing model.
