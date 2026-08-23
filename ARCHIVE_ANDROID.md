# Archive: Android app history

Detailed narrative for Android app work, moved out of `NEXT_STEPS.md`
2026-08-23 to keep that file's current-status section cheap to read.
Current status/roadmap lives in `NEXT_STEPS.md` — this file is history,
not a place to look for "what's next."

**Entry-tag convention** (for `Grep`-based lookup instead of reading this
whole file): entries lead with `✅ **Real bug`, `**Decided`, `**Design
correction`, or similar bold tags — grep for those to filter by type.

See also `ARCHIVE_TESTING.md` for the Kotlin golden-vector port work
(`Breakdown.kt` Rounds 1-2, 2026-08-21) — that work is Android-specific in
effect but told as part of one continuous cross-platform testing-strategy
narrative, so it lives there instead of being split mid-story.

---

## 🤖 Android app: Phases 0-4 done, paid scan feature working end-to-end

Full roadmap (6 phases) was planned 2026-08-17 — see git history / ask for
the plan if needed; not duplicated here. This section tracks execution
status only. Decided: build happens on this Windows machine (the earlier
"Android compilation happens elsewhere" note referred to a *different*
machine, not this one). `applicationId` = `com.rigcheck.app`. RevenueCat
SDK choice: native `purchases-android`, not `purchases-kmp`.

**Phase 0 (dev environment) — done, verified via CLI, 2026-08-17:**
- Android Studio (Quail 3 | 2026.1.3) installed to `G:\Android\AndroidStudio`
  (checksum-verified download, silent-install needs admin elevation this
  automated session couldn't grant, so the user ran the installer/wizard
  directly — same pattern as GUI dashboard steps elsewhere in this project).
  SDK installed to `G:\Android\Sdk` via its Setup Wizard.
- **No standalone JDK installed** — Android Studio bundles a JetBrains
  Runtime at `G:\Android\AndroidStudio\jbr`; set as `JAVA_HOME` (User env
  var) so `gradlew`/`sdkmanager`/`avdmanager` work from a bare terminal too.
- `GRADLE_USER_HOME=G:\GradleUserHome` set (User env var) — Gradle's
  dependency cache, same category of fix as the earlier npm-cache move.
- **Session gotcha, will recur:** newly-set User env vars aren't visible to
  an already-running shell (same class of issue as the `ANTHROPIC_API_KEY`
  propagation gotcha) — every `gradlew`/`sdkmanager`/`avdmanager`/`emulator`
  call in a shell opened *before* a var was set needs it passed inline
  (`JAVA_HOME=... GRADLE_USER_HOME=... command`) until the shell restarts.
- Confirmed via CLI: `./gradlew assembleDebug` and `./gradlew test` both
  succeed; Gradle cache correctly lands on `G:\GradleUserHome`, not C:.

**Phase 1 (project scaffolding) — done, verified via CLI, 2026-08-17:**
- Project created at `android/` (inside this repo) via Android Studio's New
  Project wizard — Empty Activity template, Compose, Kotlin DSL.
  `applicationId=com.rigcheck.app`, `minSdk=26`, `targetSdk=37`.
- A save-location warning about the space in
  `G:\Claude Experiment\...` was dismissed — that warning is a legacy
  caution for NDK/native-toolchain builds; this project has no native code,
  and the build succeeded with the space in the path.
- Baseline deps added: Navigation-Compose (2.9.8), `lifecycle-viewmodel-compose`
  (2.11.0), `kotlinx-serialization-json` (1.11.0) + the matching Kotlin
  serialization Gradle plugin — versions checked directly against Google's/
  Maven Central's metadata (not guessed), filtered to the latest genuinely
  stable release (the metadata's own `<latest>`/`<release>` tags include
  alpha/rc builds, so those had to be excluded explicitly). Build confirmed
  green with all of them in.

**Phase 2 (core business logic port) — done, 2026-08-17, all tests green:**
- Ported `compute_breakdown`/`verdict_for` to
  `android/app/src/main/java/com/rigcheck/app/domain/Breakdown.kt` +
  `VerdictInfo.kt`, with `TruckTag`/`TrailerTag`/`ScaleTicket` domain models
  under `domain/model/` (deliberately narrower than the full Python
  dataclasses — only fields `compute_breakdown` or manual entry actually
  use; VIN/tire-spec/scale-metadata fields are scan-only and don't exist in
  the Kotlin domain model at all).
- Fixed the Python-truthiness parity trap identified in planning before it
  could bite: `if standalone_weight:` and `if axle_count_raw else 2` both
  treat an explicit `0` as "not provided" in the original — ported
  explicitly (`!= null && != 0`), not via a naive `?:`, which would have
  silently diverged on a `0` input.
- String formatting deliberately split from the domain layer (unlike the
  Python/TS originals, which bake comma-formatted strings directly into
  their output): `domain/NumberFormatting.kt` holds the one canonical
  `formatWholeNumber()` (needed by both the domain layer itself, since note
  text like "1,660 lb tongue weight" embeds a formatted number as business
  text, and by `ui/format/NumberFormatting.kt`'s display helpers
  `formatLb()`/`badgeLabel()`). `barColor`/`bandBg` (CSS var strings in the
  originals) don't port at all — deferred to whenever the UI screens map
  `Tone` to actual Compose colors.
- **Caught and fixed one real bug during testing, not just porting**: the
  first draft of the tongue-weight note used a local `roundToInt().toString()`
  instead of the shared comma-formatter, which would have produced `"1660 lb
  tongue weight"` instead of the spec's `"1,660 lb tongue weight"` — the
  ported test caught this immediately (comma-formatted assertion failed),
  fixed by routing through the one shared `formatWholeNumber()`.
- **Test port**: `BreakdownTest.kt` — the same 5 scenarios from
  `tests/test_breakdown.py` (default axle count, custom axle count,
  standalone-weight omitted/provided, clamp-at-0) *plus* 2 new cases the
  Python suite doesn't cover (`axle_count = 0`, `standalone_weight_lb =
  0.0`) verifying the truthiness-parity fix above. Plus `VerdictTest.kt`
  (2 cases — `verdict_for` also has no existing Python test) and
  `NumberFormattingTest.kt` (3 cases). **13/13 tests pass**, confirmed via
  `./gradlew test` and the generated JUnit XML reports (`tests="7"` /
  `"2"` / `"3"` / `"1"` across the 4 test classes, 0 failures/errors) — not
  just a green Gradle exit code, the actual per-class counts were checked.
  `./gradlew assembleDebug` also still succeeds.

**Emulator setup — AVD created, boot blocked on a real hardware issue:**
- `cmdline-tools` (sdkmanager/avdmanager) weren't part of Studio's default
  SDK install — downloaded separately (checksum-verified) and extracted to
  `G:\Android\Sdk\cmdline-tools\latest`.
- System image `system-images;android-37.0;google_apis_playstore;x86_64`
  (2.8 GB) installed manually via `sdkmanager`, matching `targetSdk=37` and
  including Play Store (useful later for Phase 4/6 billing tests).
- **`avdmanager create avd` (the older, deprecated tool) is broken for this
  system image** — fails with "Could not load devices from ...devices.xml"
  because this particular image ships with no `devices.xml`. Worked around
  by using the newer `android` CLI instead (also in `cmdline-tools/latest/bin`,
  the tool `sdkmanager`'s own deprecation warning points to):
  `android --sdk="G:\Android\Sdk" emulator create <profile>` (profile names:
  `android emulator create --list-profiles`). This tool auto-picked its own
  system image (API 36, not the API 37 one installed above) rather than
  reusing it — harmless (G: has ample space) but means both API 36 and 37
  images now sit on disk unused-except-one.
- **Real mistake caught and fixed:** the `android` CLI **defaults to its own
  SDK at `C:\Users\Angela\AppData\Local\Android\Sdk`** if `--sdk` isn't
  passed explicitly — first attempt did exactly this and silently downloaded
  ~3.4 GB (platform-tools, emulator binary, the API 36 system image) to the
  space-constrained C: drive. Caught via `android info` showing the wrong
  `sdk:` path, deleted (`Remove-Item` on the whole stray folder, 3.4 GB
  reclaimed), and redone with `--sdk` explicit. **Always pass `--sdk=` (or
  `ANDROID_SDK_ROOT`) explicitly with this tool — it does not reliably pick
  up the SDK from Android Studio's own configured location.**
- AVD instance data (`~/.android`, normally lands on C: — flagged in the
  original plan as "stubborn, revisit if C: usage climbs") was proactively
  relocated *before* first boot, since first boot can add several GB via
  userdata/snapshot images: `ANDROID_AVD_HOME=G:\Android\EmulatorHome\avd`
  and `ANDROID_EMULATOR_HOME=G:\Android\EmulatorHome` (both User env vars).
  Note the emulator binary's actual runtime search order (confirmed via
  `emulator.exe -help-all` and by directly hitting the error) is
  `$ANDROID_AVD_HOME` → `$ANDROID_SDK_HOME\avd` → `$HOME\.android\avd` —
  `ANDROID_EMULATOR_HOME` alone was *not* sufficient to relocate the `avd/`
  subfolder despite the help text implying it would be; both vars are now
  set for safety.
- ✅ **Emulator fully working — done 2026-08-18.** Booting needed *two*
  separate fixes, not one — worth remembering both if this ever needs
  reproducing on another machine:
  1. **BIOS/UEFI firmware virtualization** (Intel VT-x/AMD-V) was off —
     `systeminfo`'s `Virtualization Enabled In Firmware: No` caught this;
     fixed by the user rebooting into firmware setup and enabling it (no
     software/Windows-feature toggle can do this, hardware-level only).
  2. **Windows Hypervisor Platform**, a separate *Windows* feature from the
     BIOS setting — still showed `InstallState: 2` (disabled) even after
     the BIOS fix (checked via `Get-CimInstance -ClassName
     Win32_OptionalFeature -Filter "Name='HypervisorPlatform'"`, since the
     more obvious `Get-WindowsOptionalFeature` cmdlet itself requires
     elevation even to *read* status). Needs admin elevation to enable
     (`dism.exe /online /enable-feature /featurename:HypervisorPlatform
     /all`, or the "Turn Windows features on or off" GUI) — same
     elevation wall as the Android Studio installer, so the user ran it
     directly, then rebooted again.
  - With both fixed, `emulator -avd medium_phone` boots cleanly — log
    confirms `WHPX on Windows 10.0.26200 detected. Windows Hypervisor
    Platform accelerator is operational`. Full pipeline verified: `adb
    devices` sees it, `gradlew installDebug` installs the real app,
    `adb shell am start` launches it, confirmed via a real screenshot
    (`adb exec-out screencap`) showing the stock "Hello Android!" screen
    rendering correctly with the Play Store icon present in the status bar.

**Phase 3 (manual-entry UI) — done, verified end-to-end on-device,
2026-08-18.** Real screens built from the 2026-08-17 mockups (reconciled
into `ANDROID_DESIGN_BRIEF.md`), not stubs:

- **Theme**: `ui/theme/Color.kt`/`Theme.kt`/`Type.kt` replaced entirely —
  were 100% stock Android Studio purple/pink template before this phase.
  Real brand palette from `web/src/design-system/tokens.css`, light-only
  `lightColorScheme`, `dynamicColor` off (so Material You can't override
  the fixed brand colors). Quicksand + Karla wired via the Compose
  **Downloadable Fonts API** (fetched at runtime from Google Fonts, not
  bundled `.ttf` files) — needed `res/values/font_certs.xml`, which
  **must be copied verbatim from Google's own sample**, not
  hand-transcribed: a first attempt at reproducing it from memory got the
  certificate bytes wrong and used the wrong XML array type
  (`<array>` vs `<string-array>`), caught only by fetching the real file
  from `android/user-interface-samples` and diffing before it shipped.
- **Reference images**: the 3 mockup photos (`android/design/extracted/.../
  reference-images/`) resized via a one-off `uv run python` + Pillow
  script (repo's existing Python dependency, no new tooling) from
  ~3.6 MB combined down to ~0.63 MB, capped at 1600px long edge, and
  copied into `res/drawable/` as `ref_truck_tag.jpg`/`ref_trailer_tag.jpg`/
  `ref_scale_ticket.jpg`. **Real bug caught by on-device testing**: the
  first resize pass called `ImageOps.exif_transpose()`, which rotated the
  truck-tag photo sideways — the design export's pixel data was already
  correctly rotated (confirmed by direct visual inspection), but the file
  carries a *stale* EXIF orientation tag left over from the original phone
  capture that no longer matches the pixels. Fixed by dropping the
  `exif_transpose()` call entirely.
- **Domain model change**: `TruckTag`/`TrailerTag`'s `manufacturer` field
  renamed to `description`, plus a new `name` field added to both —
  matches the reconciled brief's mockup-driven field list. Safe rename:
  `manufacturer` was never read by `compute_breakdown`, no test fixture
  set it.
- **Domain layer change, decided this session**: `Breakdown.kt`'s
  `"Tow Vehicle Total (GVWR)"` and `"Combined Rig Weight"` rows now get
  dynamic, number-specific note text (e.g. "Steer (5,640) + drive (9,080)
  = 14,720 lb, which is 720 lb over this truck's 14,000 lb GVWR.")
  instead of a fixed generic sentence — matches the mockup, but is a
  **deliberate Android-only enhancement**, not ported back to
  `breakdown.py`/`calc.ts`. Two new JUnit cases added
  (`BreakdownTest.kt`) asserting the exact generated text.
- **Data layer**: `data/RecentRigsRepository.kt` — Preferences DataStore
  (new dependency, `androidx.datastore:datastore-preferences` 1.2.1),
  one serialized JSON blob via `kotlinx.serialization`, porting
  `web/src/recentRigs.ts`'s exact algorithm (case-insensitive dedupe by
  nickname, prepend, slice to 5) — verified against the real file this
  session, not from memory.
- **Navigation**: `ui/navigation/RigCheckNavHost.kt` — Navigation-Compose
  with type-safe `@Serializable` route objects (natural fit given
  `kotlinx-serialization-json` was already a dependency). One
  nav-graph-scoped `RigCheckViewModel` (`AndroidViewModel`, no DI
  framework needed) holds in-progress truck/trailer/scale state and an
  in-memory-only `disclaimerAcknowledged` flag — never persisted, shown
  once per process per the brief.
- **Reference-image zoom, decided this session**: tap-and-hold (not the
  alternative persistent-lower-third-crop option) — press and drag on the
  truck/trailer tag photos to zoom into that exact spot, matching the
  mockup's hover-to-zoom intent adapted for touch. Highlight-ring color
  (`#f0942f`) pulled directly from the mockup's own JS, not guessed.
  Scale-ticket screen uses a simpler static numbered-legend instead (no
  interaction) — exact badge x/y positions weren't extractable from the
  design source, so the legend row carries the number-to-field mapping.
- **"Scan Photo" is now fully live on all three chooser screens** — see
  the Phase 4 section below.
- **Full on-device verification, real data, both branches of the
  tongue-weight fallback exercised**: installed the real (non-stub) app
  on the now-fully-working emulator, manually drove the entire flow via
  `adb shell input tap`/`text` (with `uiautomator dump` for exact element
  bounds — screen-relative tap coordinates broke once the keyboard
  reflowed the layout, a test-methodology gotcha, not an app bug) using
  the real `ExampleDocs/`-equivalent CAT Scale ticket numbers. Confirmed
  via real screenshots at every step: Rig Picker (gradient header, empty
  state, working nickname field) → Chooser (disabled Scan card, active
  Manual card) → Truck Tag Entry (corrected reference image, all fields
  bind correctly) → Trailer Tag Entry → Scale Ticket Entry (numbered
  legend + real ticket image) → Disclaimer (exact finalized text) →
  **Results**, which rendered the full real breakdown correctly: mixed
  pass/fail rows, correct colors/borders/percentages, and the new dynamic
  note text tap-to-expanded exactly as designed. `./gradlew test
  assembleDebug` both still pass after all of the above.

**Phase 4 (optional paid scan feature) — done, verified on-device,
2026-08-18:** connected to the RevenueCat test customer `smoke-test-user`
(the same one used for the 2026-08-17 server-side Worker smoke test),
using the RevenueCat **public** Test Store SDK key pasted directly into
chat (public keys are explicitly exempt from the "never type secrets in
chat" rule — unlike `REVENUECAT_SECRET_KEY`/`ANTHROPIC_API_KEY`, which
stayed out of chat/commands as always).
- **RevenueCat SDK wiring**: `RigCheckApplication.kt` configures
  `Purchases` with a hardcoded `appUserID("smoke-test-user")` —
  deliberately a testing-only shortcut, commented in code as needing to
  change to the SDK's default per-install anonymous ID before any real
  release. `data/RevenueCatManager.kt` wraps the SDK's callback APIs as
  suspend functions (balance, offerings, purchase via the current
  non-deprecated `PurchaseParams.Builder`/`purchase()` path, restore).
- **Scan pipeline**: `ActivityResultContracts.TakePicture()` +
  `FileProvider` (no `CAMERA` permission needed) →
  `data/PhotoEncoding.kt` (downscale ≤1600px long edge, JPEG q85, base64)
  → `data/ScanApiClient.kt` (OkHttp POST to the deployed `scan-proxy`
  Worker) → `data/ScanFieldMapping.kt` (merges extracted fields onto the
  current module's state, never clobbering a value the user already
  typed) → lands on the *same* Phase 3 entry screen for review, exactly
  as planned (no new form UI needed).
- **New `RigCheckRoute.Paywall` + `PaywallScreen.kt`**: custom Compose
  layout (not RevenueCat's prebuilt UI), real Test Store offerings/prices
  via `StoreProduct.price.formatted` (never hardcoded), "Restore
  purchase" link. Reachable by tapping Scan Photo at 0 credits, or by
  tapping the new credit-balance chip directly ("get more scans"
  affordance).
- **Real bug caught and fixed during on-device verification**: the
  RevenueCat SDK caches virtual-currency balance client-side and has no
  way to know the Worker just deducted a credit server-side via a direct
  REST call (not through the SDK's own purchase flow) — so the credit
  chip kept showing the pre-scan balance after a real scan. Fixed by
  calling the SDK's `invalidateVirtualCurrenciesCache()` before every
  balance fetch in `RevenueCatManager.getScanCreditBalance()`, so launch
  and post-scan/post-purchase refreshes always hit the network. This is
  the same "don't trust memory, verify against the real decompiled jar"
  discipline as the Phase 4 planning stage (`javap -p` on
  `purchases-10.17.0.aar`'s `classes.jar` found the method).
- **Full on-device verification, `./gradlew assembleDebug` clean**,
  driven via `adb shell input`/`uiautomator dump` (same technique as
  Phase 3): credit chip showed the real `smoke-test-user` balance (99) on
  launch; tapping Scan Photo launched the real system camera app via
  `FileProvider` with no crash; capturing and confirming a photo drove
  the full pipeline (encode → upload → real Worker call → real Claude
  call → parsed response → merged onto `TruckTag` → navigated to the
  review screen) — fields came back blank/`<UNKNOWN>` as expected since
  the AVD's back camera is a generic virtual scene, not a real label, but
  the pipeline itself is proven; balance correctly decremented 99 → 98,
  confirmed durable across an app reinstall (not just an optimistic local
  update); Paywall rendered two real Test Store products ($99.99
  Lifetime, $0.99 Consumable) with working "Restore purchase"; a real
  Test Store purchase completed end-to-end (RevenueCat's own "Test Store
  Purchase" confirmation dialog → "Purchase complete!" toast → balance
  correctly incremented 98 → 108, the consumable pack's configured
  credit grant).

All 6 planned phases are now done. Remaining Android work is polish/tests
only — see `NEXT_STEPS.md`'s roadmap section.

**Two real bugs found during the user's own hands-on emulator testing,
both fixed and re-verified on-device, 2026-08-18:**
- **Recent-rig selection skipped the Chooser entirely.** Picking an
  existing rig from `RigPickerScreen` navigated straight to
  `RigCheckRoute.ScaleTicketEntry`, bypassing `Chooser(EntryModule.SCALE)`
  — so returning users had no Scan Photo option at all, only the fresh
  "start a new rig" path did. Fixed in `RigCheckNavHost.kt`:
  `onSelectRecentRig` now navigates to `Chooser(EntryModule.SCALE)`
  instead. Re-verified: selecting an existing rig now lands on the
  Chooser with Scan Photo available.
- **Scan Photo only offered "take a new photo," never "use one you
  already have."** The user correctly pointed out that in practice the
  photo is usually already taken before opening the app — certainly true
  for a CAT Scale ticket, which is a printed receipt handed over well
  before anyone opens RigCheck. `ChooserScreen.kt` now shows a small
  dialog on tapping Scan Photo ("Take Photo" / "Choose from Gallery"),
  the latter via `ActivityResultContracts.PickVisualMedia()` (the modern
  Android Photo Picker — no storage permission needed on any API level).
  The credit-balance chip also got a `onClick` (opens the Paywall
  directly, a "get more scans" affordance) to support testing this
  without spending real Test Store credits repeatedly.
  **AVD-testing-only gotcha hit and fixed while verifying this**: photos
  pushed onto the emulator via `adb push` land in MediaStore with
  `is_pending=1` (a flag meaning "still being written"), which hides them
  from every gallery/picker app including the new one — not an app bug,
  a test-environment quirk. Fix: `adb shell content update --uri
  content://media/external/images/media/<id> --bind is_pending:i:0` per
  file. Even after that, the Photo Picker's own separate sync can lag
  behind a raw `adb push`; `adb shell am force-stop
  com.google.android.providers.media.module` forces it to resync on next
  launch. Re-verified end-to-end with a real, legible photo this time
  (`ExampleDocs/CatScale-Ticket.jpg` via "Choose from Gallery," not the
  AVD's virtual-scene camera): Claude correctly extracted every field —
  scale location "LOVES COUNTRY STORES," steer 5640, drive 9080, trailer
  19680 lb, all matching the real ticket exactly — and the credit balance
  decremented correctly (108 → 107).

## 📱 Android distribution: sideloading confirmed viable, Play Console decision parked

Raised 2026-08-18 after Phase 4 was committed/pushed — the user wants to
field-test the app on their own phone for a while before deciding
anything about a real Play Store release. **Not blocking further work,
no action taken yet** — this section exists so the decision context
survives a machine switch.

**Sideloading needs no Google Play Console account at all** — confirmed
this is a fully separate concern from Play Store distribution:
- **Recommended path**: enable Developer Options (Settings → About Phone
  → tap Build Number 7×) and USB Debugging on the phone, plug it into
  this PC, authorize the one-time "Allow USB debugging?" prompt, then
  `adb install` the existing debug APK exactly like every emulator
  install this session — no rebuild needed beyond what already exists.
- **Cable-free alternative**: transfer the APK to the phone any way
  (email, Drive, USB file copy) and tap to install; Android prompts for a
  one-time "install unknown apps" permission on whichever app opened the
  file. Fully standalone afterward either way — the cable/PC is only
  needed at install time, not for ongoing use.
- **Caveat specific to field-testing the paid scan feature**: the app is
  currently wired to RevenueCat's **Test Store** with the hardcoded
  `smoke-test-user` identity (see the Phase 4 section above) — so scans/
  purchases on a sideloaded phone build won't involve real money and will
  share the same credit balance this session's testing has been using
  (107 as of the last check), not a fresh account. Convenient for free
  field testing, but not representative of a real customer's experience,
  and this hardcoded identity must change before any real release
  (already flagged in code as testing-phase-only). Manual entry (the
  free, offline path) has no such caveat.

**Play Console registration — decision explicitly parked by the user,
"need to think about it for a while":**
- **Personal vs. Organization account** is the open question. Personal
  is simpler (no D-U-N-S/business-entity verification) and was my
  recommendation for a solo/experimental project like RigCheck;
  Organization is only needed to publish under a registered business
  name. Neither choice is reversible without creating a new account, so
  there's no harm in taking time here.
- Known facts for whenever this decision resumes: one-time $25 USD
  registration fee; Google now requires **identity verification**
  (government-ID upload, possibly a live selfie-match step) for *all*
  new developer accounts, personal or organization, which can take
  anywhere from a few days to ~2 weeks to clear; after approval, Google
  requires new personal accounts to run a **closed test with 20+ testers
  for 14 continuous days** before allowing a production release.
- None of this blocks sideloaded field testing, which needs no Play
  Console account at all — the two tracks (personal field testing vs.
  eventual Play Store release) are fully independent until the user
  decides to actually publish.

## From "🧪 Tests still outstanding" — Android-specific done items

- ✅ **`compute_breakdown`/`verdict_for` Kotlin port — done 2026-08-17.**
  `BreakdownTest.kt` (9 cases: the 5 from `tests/test_breakdown.py` plus 2
  zero-value edge cases it doesn't cover plus 2 for the new dynamic
  Android-only row notes), `VerdictTest.kt` (2 cases),
  `NumberFormattingTest.kt` (3 cases) — 13/13 passing, see Phase 2 above
  for detail.
- ✅ **Phase 3/4 manual on-device verification (navigation, disclaimer
  gating, results rendering, RevenueCat/scan/purchase flow) — done
  2026-08-18**, real walkthroughs against the RevenueCat Test Store and
  the live `smoke-test-user` customer (see the Phase 3/4 sections above).
  Converted into a committed, repeatable `androidx.compose.ui.test` suite
  2026-08-19 — see below.
- ✅ **`RevenueCatManager` unit test — done 2026-08-19.**
  `RevenueCatManagerTest.kt` (4 JUnit4 + MockK cases) specifically covers
  the balance-cache-invalidation bug found and fixed 2026-08-18: asserts
  `getScanCreditBalance()` calls `invalidateVirtualCurrenciesCache()`
  before reading the balance (not after), plus the balance-present,
  balance-absent, and `appUserId`-passthrough cases. New test
  dependencies: `io.mockk:mockk` 1.14.3, `kotlinx-coroutines-test` 1.10.2
  (added to the version catalog; versions verified against Maven Central
  at write time, not assumed from memory).
  **Two genuine deadlocks hit and fixed while writing this — both
  confirmed via `jstack` thread dumps, not guessed:**
  1. **`Purchases.sharedInstance` needs `mockkObject(Purchases.Companion)`,
     not `mockkStatic(Purchases::class)`.** The latter compiles and runs
     without error but silently doesn't intercept the call — `sharedInstance`
     is `Purchases.Companion.getSharedInstance()` under the hood, not a
     true `@JvmStatic` method, so the *real* getter ran every time and threw
     (`Purchases.configure()` is never called in a plain JVM unit test).
  2. **MockK's `coEvery`/`coVerifyOrder` on a suspend function deadlock
     if called from inside any coroutine builder** (`runBlocking`,
     `runTest`, doesn't matter which) — `coEvery` internally bridges into
     suspend land via its *own* `runBlocking` to record the call
     signature, and nesting that inside another coroutine on the same
     thread means both park waiting on each other. This happened twice
     (once nested in `runTest`, once nested in plain `runBlocking`) before
     the actual fix: **mock the real callback-based
     `getVirtualCurrencies(GetVirtualCurrenciesCallback)` member method
     instead of the `awaitGetVirtualCurrencies()` suspend extension
     function built on top of it** — a plain `every {...} answers {...}`
     invoking the callback synchronously, no `coEvery`/`mockkStatic` on
     the extension file needed at all. `RevenueCatManager`'s real
     (unmocked) suspend wrapper still runs and bridges the callback into a
     suspend result exactly as it does in production.
  `./gradlew test`/`assembleDebug` both clean after.
- ✅ **Compose UI test suite (daily-equivalent tier) — done 2026-08-19.**
  Full writeup in `android/TESTING.md`; summary here. 30 instrumented
  tests across 10 files (`ResultsScreenTest`, `BreakdownRowTest`,
  `DisclaimerScreenTest`, `RigPickerScreenTest`,
  `TruckTagEntryScreenTest`, `TrailerTagEntryScreenTest`,
  `ScaleTicketEntryScreenTest`, `ChooserScreenTest`,
  `CreditBalanceChipTest`, `PaywallScreenTest`) plus navigation-flow
  coverage in `RigCheckNavHostTest.kt` — `./gradlew
  connectedDebugAndroidTest`, 30/30 passing.
  - **New `CustomTestRunner.kt`** substitutes a plain `Application` for
    `RigCheckApplication` during instrumented tests, so
    `Purchases.configure()` never runs — confirmed via `adb logcat`
    showing zero `[Purchases]` SDK log lines across a full run. This
    keeps the whole suite offline and hermetic (no real network, doesn't
    touch `smoke-test-user`'s balance), needing zero production-code
    changes since `RigCheckViewModel`/`PaywallScreen`'s RevenueCat calls
    were already wrapped in `runCatching`.
  - **Real regression test added** for the recent-rig routing bug found
    2026-08-18 (`RigCheckNavHostTest.recentRigSelectionRoutesThrough...`):
    does a full checkout, goes back to `RigPicker`, selects the
    just-created recent rig, and asserts it lands on
    `Chooser(EntryModule.SCALE)` rather than skipping straight to the
    entry form — would fail if that bug reappeared.
  - **Real gotcha hit and fixed**: entry screens (`TruckTagEntryScreen`
    etc.) live inside a `verticalScroll` `Column`, and their Next/Check
    Weights buttons sit below the fold — `performClick()` doesn't
    auto-scroll a node into view before clicking, unlike Espresso.
    Fixed by chaining `.performScrollTo().performClick()`; first showed
    up as 5 failures (a "not displayed" assertion, and several button
    clicks silently not registering) across the entry-screen and
    NavHost-flow tests.
  - **Minor production change**: added `testTag` modifiers to one
    representative field per entry screen (`truck_description`,
    `trailer_description`, `scale_location`) so tests can target a
    specific `TextField` reliably — `LabeledTextField`'s existing
    `modifier` parameter already threaded through to the real field, so
    this needed no changes to the shared component itself.
- ✅ **Weekly-equivalent tier — built and verified for real, 2026-08-23**
  (roadmap item #4, Part A). `PaywallScreenWeeklyTest.kt` (3 cases, see
  `android/TESTING.md` for what each covers) passes end-to-end against
  the real RevenueCat Test Store and the real deployed Worker
  (`.\test-weekly.ps1` → `OK (3 tests)`), incrementing/decrementing
  `weekly-test-user`'s real balance both ways.

  **Real bug found while diagnosing an unrelated user report, found via
  live device driving, not guessed.** Before starting this work, the
  user reported the app "skipping" the Trailer step after a truck scan.
  Rather than guess, drove the actual installed APK live via
  `uiautomator dump` + `adb shell input tap` (screenshotting each step)
  — a full manual-entry walkthrough (Truck → Trailer → Scale) proved the
  navigation code itself was correct; the real culprit was almost
  certainly the AVD's fake virtual-scene camera returning garbage OCR
  data (a known, already-documented limitation, not a new bug). This
  hands-on-driving technique — `uiautomator dump` for exact element
  bounds/resource-ids, `adb shell input tap`/`screencap` to drive and
  observe — turned out to be exactly what this tier's own tests needed
  too, since it's what surfaces a native (non-Compose) dialog's real
  structure.

  **Three mechanisms tried for "one test APK, two Application classes,
  chosen at run time" before one actually worked — each rejected only
  after hands-on proof, not assumption:**
  1. A second, separately-named `AndroidJUnitRunner` subclass
     (`WeeklyTestRunner`) with its own `<instrumentation>` manifest
     entry. **Doesn't work** — AGP's manifest merger treats
     `<instrumentation>` as a singleton merge point regardless of
     `android:name`; the second entry's attributes (confirmed via the
     merged manifest in `build/intermediates/`) silently fold into the
     *existing* `CustomTestRunner` entry instead of registering as an
     invocable component. `am instrument ... WeeklyTestRunner` then
     fails outright: `INSTRUMENTATION_FAILED`.
  2. Reusing `CustomTestRunner`, branching on `-e weekly true` read via
     `InstrumentationRegistry.getArguments()` inside `newApplication()`.
     **Doesn't work** — crashed the *Daily* tier too (this runner is
     shared): `IllegalStateException: No instrumentation arguments
     registered!`. `AndroidJUnitRunner` hadn't registered the static
     registry yet when `newApplication()` fired.
  3. Same branch, but capturing the `Bundle` from `onCreate(Bundle)`'s
     own parameter into an instance field first (Android's own docs say
     `onCreate` runs "before any application code is loaded", i.e.
     before `newApplication()`). **Also doesn't work**, and this one is
     worth remembering precisely: timestamped `Log.i` calls proved
     `newApplication()` actually fires *before* `onCreate()` in this
     AGP/androidx.test version — the documented order is reversed in
     practice.
  4. **What actually worked**: a device-side marker file
     (`/data/local/tmp/rigcheck_weekly_mode`), touched by
     `test-weekly.ps1` via `adb shell` *before* `am instrument` runs,
     checked with plain synchronous `java.io.File.exists()` in
     `newApplication()` — no lifecycle-ordering dependency at all, since
     it doesn't go through the Instrumentation object's own state.
     Removed again after the run so a later `./gradlew
     connectedDebugAndroidTest` is unaffected regardless.

  **A second real gap, found only because the Daily tier was rerun as a
  regression check after each attempt (per this project's TDD/no-silent-
  regression discipline) rather than trusting the Weekly-tier change was
  isolated:** simply adding `PaywallScreenWeeklyTest.kt` to the shared
  `androidTest` source set meant `./gradlew connectedDebugAndroidTest`
  picked it up too — JUnit discovers every `@Test` class in the source
  set regardless of which tier "owns" it. Since the Daily tier never
  sets the weekly marker, this test would have silently tried real
  network as an unconfigured `Purchases` instance. Fixed with
  `testInstrumentationRunnerArguments["notClass"]` in
  `app/build.gradle.kts` (Gradle-invocation-only, doesn't affect
  `test-weekly.ps1`'s raw `adb shell am instrument` call at all — the
  two invocation paths are fully independent).

  **A real threading bug in the purchase test itself**: calling
  `RevenueCatManager.purchasePackage(...)` from the instrumentation
  thread (the default for `runBlocking`/`async` here) never triggered
  RevenueCat's Test Store confirmation dialog at all — not slow, just
  never happened, confirmed by widening the wait to 25s with no change.
  A real manual button tap (which always runs on the main thread) opens
  it instantly. Fixed by wrapping the call in
  `async(Dispatchers.Main) { ... }`.

  **The dialog itself was screenshotted and confirmed hands-on before
  encoding it into the test**, reusing the already-installed app (same
  RevenueCat Test Store dialog regardless of app-user-id, so no need to
  build the Weekly APK first just to see it): a standard native
  `AlertDialog` with `android:id/button1`/`button2`/`button3`
  ("TEST VALID PURCHASE" / "TEST FAILED PURCHASE" / "CANCEL"), title
  "Test Store Purchase", body text stating outright "This is a test
  purchase and should only be used during development" — confirms the
  plan's second hands-on-check item (no real charge) directly from the
  SDK's own UI, not RevenueCat's docs. Triggering it also proved the
  first hands-on-check item: yes, a real purchase needs exactly one UI
  interaction beyond the app's own Buy button (this dialog), consistent
  with what Phase 3/4's manual verification already found. New
  `androidx.test.uiautomator:uiautomator` dependency drives it (`By.res`/
  `UiDevice.wait`/`Until.findObject`), since it's outside the Compose
  semantics tree `composeRule` can see.

  **One more real, unrelated bug caught by the compiler, not guessed**:
  `rendersRealOfferingsFromTestStore() = runBlocking { ... }`'s body
  ended in `assertIsDisplayed()`, which returns a chainable
  `SemanticsNodeInteraction`, not `Unit` — JUnit rejects any `@Test`
  method whose inferred return type isn't void. Fixed by switching to a
  block body (`{ runBlocking { ... } }`) so the method's return type is
  unambiguous regardless of the last expression inside.

  Part B (Unit/Daily JaCoCo coverage tooling) not started — see
  `NEXT_STEPS.md`'s roadmap item #4.
