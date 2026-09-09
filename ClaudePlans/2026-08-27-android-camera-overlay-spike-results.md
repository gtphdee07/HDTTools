# Results: camera-preview bounding-box overlay spike (paused 2026-08-29)

Keywords for grep: camera overlay, CameraX, PreviewView, ImageCapture,
CameraOverlaySpikeActivity, CameraOverlaySpikeScreen, Guided Scan,
EXIF orientation, normalizeExifOrientation, encodePhotoForScan,
landscape rotation, physical device, awaitViewAttached, paused, resume,
test phone.

Companion report to `ClaudePlans/2026-08-27-android-camera-overlay-spike.md`
(the approved plan). All verification below was done for real on the
`medium_phone` emulator (`G:\Android\EmulatorHome\avd\medium_phone.avd`,
API level with `androidx.camera` 1.6.2) — no physical device was available
in this environment; see the Open Risk section for why that matters.

---

## Status: Paused (2026-08-29)

**Not abandoned — paused for a concrete, external reason: no physical
Android test device is currently available**, and the single most
important open question from this spike (finding #3 below: does
landscape capture come out genuinely rotated at the pixel level, or is
it an emulator-only artifact of the AVD's virtual scene camera?)
**cannot be answered on an emulator** — it requires a real device.
Continuing to invest further here without that answer risks building on
top of an unconfirmed assumption either way.

**Everything below this line was already true as of 2026-08-27** and
remains a real, complete, isolated spike — nothing was undone or
invalidated by pausing. When a physical device becomes available, the
concrete next action is exactly step 1 of the Recommendation section
below: confirm finding #3, then proceed or fall back per that section's
own logic. No re-derivation of the permission-flow, EXIF-bug, or overlay-
alignment findings should be needed — they're already established here.

## What was built

Isolated, production-untouched spike under
`android/app/src/main/java/com/rigcheck/app/ui/experiments/cameraoverlay/`:

- `CameraOverlaySpikeActivity.kt` — standalone `ComponentActivity`, launched
  directly via
  `adb shell am start -n com.rigcheck.app/.ui.experiments.cameraoverlay.CameraOverlaySpikeActivity`.
  Registered in `AndroidManifest.xml` as its own `<activity>` entry, not
  reachable from `MainActivity`/`RigCheckNavHost`.
- `CameraOverlaySpikeScreen.kt` — permission request → CameraX
  `ProcessCameraProvider`/`Preview`/`ImageCapture` bound to a
  `PreviewView` (via `AndroidView`), a Compose `Canvas` overlay drawing a
  rounded guide rectangle (`SunsetOrange`, 14dp corners, aspect ratio
  1600:721 taken from the app's own `ref_truck_tag.jpg`), a Capture
  button, and a "Verify via encodePhotoForScan" button that runs the real
  production `encodePhotoForScan` against the captured file for an
  honest drop-in-compatibility check.
- Added dependencies (`camera-core`/`camera2`/`lifecycle`/`view` 1.6.2,
  `androidx.exifinterface` 1.4.1) to `libs.versions.toml`/
  `app/build.gradle.kts`, and `CAMERA` permission +
  `android.hardware.camera.any` (`required="false"`) to
  `AndroidManifest.xml`. `ChooserScreen.kt` and `RigCheckNavHost.kt` were
  not touched. Existing unit suite (`./gradlew test`) still passes.

## What worked

- **Permission flow**: first launch fires the standard system dialog
  ("Allow RigCheck to take pictures and record video?", While using the
  app / Only this time / Don't allow) immediately — no custom rationale
  screen shown first in this implementation (the composable never gets a
  chance since it requests permission unconditionally in
  `LaunchedEffect(Unit)`). Granting "While using the app" is instant and
  the preview binds right after.
- **Portrait preview + overlay alignment**: confirmed visually — the
  `SunsetOrange` rounded guide rectangle stays centered and correctly
  proportioned against the live `PreviewView` feed, matching the app's
  existing visual language (`ReferenceImageCard.kt`'s accent/corner
  convention). Screenshots taken via `adb exec-out screencap`.
- **Landscape overlay alignment**: the overlay itself (Compose `Canvas`,
  drawn in the same `Box` as the `PreviewView`) stayed correctly aligned
  to the screen bounds in landscape too — this part of the quality goal
  is solid because the overlay is computed as a fraction of the actual
  Compose layout size on every draw, not from any fixed/cached
  dimension.
- **Capture → valid JPEG**: `ImageCapture` writes directly through
  `createScanPhotoUri`'s `FileProvider` `Uri` (reused unchanged from
  `ScanPhotoStorage.kt`). Pulled captured files off-device and confirmed
  with Pillow (`Image.verify()`) that they're valid JPEGs; on-screen
  debug text also decodes+reports dimensions/byte count/mime type
  in-app without needing adb.
- **No visible preview lag**: CameraX's `Preview` use case rendered
  smoothly on the emulator's virtual scene camera; no stutter observed
  during interaction.

## Real friction found (and what was done about each)

1. **CameraX/Compose interop timing bug (fixed).** Binding `Preview`
   before the `PreviewView` is attached to a window leaves its target
   rotation resolved from a stale/absent `Display`, independent of
   whether the hosting Activity was freshly recreated by a rotation.
   Fixed by suspending until `View.isAttachedToWindow` before calling
   `Preview.Builder().build()`/reading `previewView.display.rotation`
   (see `awaitViewAttached` in `CameraOverlaySpikeScreen.kt`). Confirmed
   via logcat (`Camera bound successfully (targetRotation=1)`) that the
   correct rotation is now picked up immediately after a real rotation.

2. **Real EXIF-orientation incompatibility with `encodePhotoForScan`
   (found, and fixed inside the spike only).** CameraX's `ImageCapture`
   saves the sensor-native pixel buffer and signals the needed rotation
   only via the JPEG's EXIF `Orientation` tag (portrait capture → tag
   `6`, i.e. "rotate 90° to display upright"). The existing production
   `PhotoEncoding.kt::encodePhotoForScan` decodes with plain
   `BitmapFactory.decodeStream`, which **does not consult EXIF at all**.
   Verified concretely, not just reasoned about: captured a portrait
   photo (raw file confirmed via Pillow: `1280x960`, `orientation_tag=6`),
   ran it through the real `encodePhotoForScan` via the spike's "Verify"
   button, decoded the resulting base64 back to a file, and it came out
   **visibly sideways** — the ceiling/bookshelf scene that was upright in
   the live preview rendered rotated 90° after the real pipeline. Fixed
   by adding a one-file `normalizeExifOrientation()` step in the spike
   (bakes the EXIF rotation into the pixels immediately after capture,
   the same way a stock camera app's output is typically already
   pre-rotated) — re-ran the same test after the fix and the decoded
   output was correctly upright. **This is the single most important
   finding of this spike**: any production version of a custom CameraX
   capture screen must either bake in this normalization at capture time
   (as the spike now does) or make `encodePhotoForScan` EXIF-aware
   (`androidx.exifinterface` was added as a dependency specifically for
   this). It was not possible to check here whether the *existing*
   system-camera-intent flow already has the same latent issue on some
   devices — that flow wasn't touched or tested per the spike's
   boundaries, but it's worth a quick check before assuming it's spike-only.

3. **Landscape capture appears genuinely rotated at the pixel level on
   this emulator (open risk, not fixed, needs physical-device
   verification).** After rotating to landscape with the timing fix from
   (1) in place (`targetRotation=1` correctly picked up per logcat), the
   live preview content itself rendered sideways relative to the UI
   chrome (overlay + buttons stayed correctly landscape-oriented; only
   the camera feed inside them was rotated). This is **not** the same
   bug as (1) — pulling the raw captured landscape JPEG off-device and
   viewing it directly confirmed the saved pixels are actually sideways
   (`EXIF orientation_tag=1`, i.e. the file claims no rotation is needed,
   but the image content plainly is rotated). Since EXIF says "normal"
   there's nothing for `normalizeExifOrientation()` (or any EXIF-aware
   decoder) to correct — the sensor buffer itself came out wrong. Given
   that the *same* code path correctly rotates/tags a portrait capture,
   this looks like a limitation of the AVD's virtual scene camera backend
   not properly rendering its frames for a landscape target rotation,
   rather than an app-level bug — but this could not be confirmed against
   a real device in this environment (none was available), so it remains
   an open risk. **A physical-device test in landscape is a hard
   prerequisite before shipping any production version of this screen.**

## Definition-of-done check

- Real, on-device CameraX preview + overlay spike exists in an isolated
  location; `ChooserScreen.kt`/`RigCheckNavHost.kt` untouched. ✅
- Spike's captured photo verified (not assumed) against
  `encodePhotoForScan` — and this verification is exactly what surfaced
  finding #2 above, which would have been missed by code-reading alone. ✅
- Overlay alignment checked across portrait and landscape; one real
  camera-content rotation problem found and left open pending
  physical-device confirmation (finding #3). ⚠️ partial — overlay itself
  is solid, camera content in landscape is not confirmed clean.

## Recommendation

**Conditional go** — proceed toward a real "Guided Scan" feature (as an
*additional* option alongside the existing system-camera-intent flow in
`ChooserScreen`, not a wholesale replacement), but only after:

1. Confirming finding #3 (landscape rotation) on a real physical device.
   If a physical device shows the same sideways-landscape-capture
   behavior, that is a hard blocker requiring real investigation
   (possibly `ImageCapture` output rotation handling, or falling back to
   locking the guided-scan screen to portrait-only, which is a reasonable
   product constraint for photographing a data plate anyway).
2. Deciding where the EXIF-normalization fix from finding #2 belongs
   long-term: baked into the new capture screen (as the spike now does)
   versus making `encodePhotoForScan` itself EXIF-aware so *both* capture
   paths benefit and stay in sync. The latter is probably the more
   robust choice if the system-camera-intent path turns out to share the
   same latent risk.
3. Scoping this as an addition, not a replacement, at least initially —
   the system-camera-intent flow is simpler, has zero permission
   friction, and already works; a guided-scan option can be A/B'd
   against it on real OCR accuracy before considering a full cutover.

If neither risk above is confirmed acceptable, abandoning custom preview
work and instead improving in-app guidance text/example overlays shown
*before* handing off to the system camera intent (no new permission, no
CameraX dependency) is the fallback worth considering.

## If this proceeds: testing note

Per `android/TESTING.md`'s Minor/Major/External model, a production
version of this screen would need at least: a Minor (unit/Robolectric-
style, if feasible) test for the overlay geometry math
(`GUIDE_ASPECT_RATIO`/`GUIDE_FRACTION` sizing logic, currently untested
since this is a spike per plan boundaries), and a Major (instrumented)
test exercising the permission-denied path, the capture path, and ideally
an EXIF-orientation regression test asserting the captured file decodes
upright through `encodePhotoForScan` — directly guarding against finding
#2 recurring.
