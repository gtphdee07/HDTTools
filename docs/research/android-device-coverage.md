# Android device coverage: which phones to test, how far to go, and what it costs

Research only, done 2026-10-27. Nothing was installed, run, deployed or called (no emulator, Gradle, adb, git change, GitHub issue or paid API call), and no repo file other than this one was changed. Web pages were read with a fetch tool that returns a summary of each page, so quotes are as the tool returned them; where a page was empty to the tool (Samsung Remote Test Lab FAQ, rendered by JavaScript) or only partly read (the AOSP device-definition files, 387,000 characters of base64), that is said in the row. Every claim is marked **Confirmed** (the cited page states it), **Indirect** (computed or inferred from cited data, arithmetic shown) or **UNCONFIRMED** (no primary source found). The Read column is the date I read the page. Claims about this repo cite the file read: `android/app/build.gradle.kts`, `android/TESTING.md`, `android/gradle/libs.versions.toml`, `android/app/src/main/AndroidManifest.xml`, `docs/BETA_PLAN.md`, `docs/research/artemis-android-testing.md`.

Plain-language key: **dp** is Android's size unit that does not depend on how sharp the screen is (dp = pixels / (density / 160)). A phone's layout depends on its width in dp, height in dp, the room taken by system bars, the text size the user picked and the Android version, far more than on its brand.

## Recommendation (short)

1. **The break point is about 4 emulator configurations plus 1 to 2 real Samsung phones.** Four well-chosen "corner" emulator configurations cover 8 of the 12 hidden-button risk classes listed in Q5; six to eight cover 11 of 12; the 12th (Samsung's own software) can only come from a real Samsung phone. Past about 8 emulator configurations the extra runs repeat risk classes already covered (Q5, my reasoning, not a measured population).
2. **Android is about 46% of US phones, and Samsung is about 61% to 65% of that.** Two Galaxy A-series models alone were about 35% of US Android shipments in Q2 2026 (Q1). Per-model US installed base is not public anywhere I could reach.
3. **Cheapest first.** Do the size, font-size and navigation-mode variations on the one emulator you already have (no new boot, no AI cost), then add three or four extra emulator profiles, then use your Galaxy S21+ (SM-G996U, already named in `android/TESTING.md`) as the real Samsung. Do not build a plan on Firebase Test Lab: **it is deprecated and shuts down 2027-09-30** (Q3).
4. **Cost of the Tier 1 set (4 configurations):** about 26 minutes for the full instrumented suite (4 x 6.5 min, measured basis) or about 10 minutes for a short smoke run (assumed). Artemis with the Flash profile adds about $0.3 and 100 s per scenario in the middle case (assumed token counts, real prices); the Pro profile is about 3x the money and 6x the time, so it does not belong in a matrix (Q6).
5. **Keep the deterministic tests as the gate.** "Is this button visible and not under a bar, at width W, height H, font scale F" is a Compose test, not an AI task. `PaywallScreenTest` already does a version of it (font scale 2.0 inside a 360 dp tall box).

## Q1. What the US phone population looks like

### Android versus iOS, and vendors

| Fact | Source | Status | Read |
|---|---|---|---|
| US mobile OS share, September 2026: iOS 53.59%, Android 46.39% | https://gs.statcounter.com/os-market-share/mobile/united-states-of-america | Confirmed (web-traffic measurement, not units sold or in use) | 2026-10-27 |
| US vendor share, September 2026: Apple 53.58%, Samsung 28.11%, Motorola 3.49%, Google 3.16%, Xiaomi 5.89%, Unknown 2.1% | https://gs.statcounter.com/vendor-market-share/mobile/united-states-of-america | Confirmed as the page's figures. **Weak:** Xiaomi at 5.89% contradicts Counterpoint (below); StatCounter reads browser identifiers, so a mislabel is possible. | 2026-10-27 |
| US smartphone shipments, Q2 2026: Apple 54%, Samsung 30%, Motorola 11%, Google 3%, Others 3% (Q2 2025: 54 / 27 / 12 / 2 / 5). Published 2026-08-31. These are **shipments (new phones sold into the market)**, not phones in use. | https://www.counterpointresearch.com/insights/us-smartphone-market-share/ | Confirmed | 2026-10-27 |
| Counterpoint names the Galaxy A17 5G as Samsung's driver in Q2 2026 and notes "Pixel brand remains aggressive in postpaid" and "Prepaid demand remained weak" for Motorola | same page | Confirmed | 2026-10-27 |

Android coverage of the US: Android is 46.39% (StatCounter) or 100 - 54 = 46% (Counterpoint shipments, Indirect). **Android testing covers about 46% of US phones; the other 54% are iPhones, which this app does not target.** The two firms use different methods and agree to within half a point.

Samsung's share of US Android (Indirect, arithmetic):

| Basis | Samsung / Android | Samsung + Motorola + Google / Android |
|---|---|---|
| StatCounter Sept 2026 | 28.11 / 46.39 = **60.6%** | (28.11 + 3.49 + 3.16) / 46.39 = **74.9%** (the rest is Xiaomi and unknown) |
| Counterpoint Q2 2026 shipments | 30 / 46 = **65%** (or 30 / 47 = 63.8% if "Others 3%" is counted and Apple is 54%; the rounded shares sum to 101) | (30 + 11 + 3) / 46 = **96%** |

So: **Samsung is roughly 60% to 65% of US Android. A real Samsung sample is the highest-value single addition to emulator testing.**

### Best-selling Android models and how old they are

| Fact | Source | Status | Read |
|---|---|---|---|
| Counterpoint "Best-Selling Smartphones in USA in Q2 2026": iPhone 17 (14%), iPhone 17 Pro Max (13%), iPhone 17 Pro (10%), **Galaxy A17 5G (9%)**, **Galaxy A16 5G (7%)** | https://www.counterpointresearch.com/insight/top-5-smartphone-model-share-8-countries/ | Confirmed | 2026-10-27 |
| Share of US Android shipments held by those two Galaxy A models: (9 + 7) / 46 = **about 35%** | computed from the two rows above | Indirect | 2026-10-27 |
| Galaxy A17 5G display: 6.7 inch, 1080 x 2340 (FHD+) Super AMOLED, 90 Hz max | https://www.samsung.com/uk/smartphones/galaxy-a/galaxy-a17-5g-black-128gb-sm-a176bzkaeub/ (and other Samsung country pages, via search) | Confirmed (UK page; US page returned 404 to the tool) | 2026-10-27 |
| Galaxy A16 5G display | not fetched | **UNCONFIRMED** (likely the same panel class; check before buying) | |
| In March 2025 the Galaxy S25 Ultra was the 4th best-selling phone in the US (8%) | Counterpoint monthly list (via search result; not opened) | Confirmed only as a search-result excerpt | 2026-10-27 |
| North America 2025: "Samsung's Galaxy A16 5G is the only Android model in the NAM top five" | https://counterpointresearch.com/en/insights/Apple-Samsung-Dominate-2025-List-of-Highest-shipping-Models-Across-Regions | Confirmed (region is North America, not US alone; ranking is in an image the tool could not read) | 2026-10-27 |

Replacement cycle (how old phones in use are):

| Fact | Source | Status | Read |
|---|---|---|---|
| Replacement cycles extending to **4 years** (global), expected to continue through 2026 and 2027; free summary has no US figure | https://counterpointresearch.com/en/reports/memory-crisis-pushes-global-smartphone%20replacement-cycles-toward-4-years (published 2026-08-13) | Confirmed (global; US figure paywalled) | 2026-10-27 |
| Omdia: average lifetime **4.2 years** before replacement (3.6 in 2020), worldwide | https://www.theregister.com/2026/04/30/phone_buyers_opt_to_wait/ (an article quoting Omdia, not Omdia's own page) | Confirmed as quoted; secondary | 2026-10-27 |
| CIRP (Oct 2023): 43% of Android owners kept their previous phone 2 years or more, 21% three years or more (iPhone: 61% and 29%). Sample size and country not stated on the page. | https://cirpapple.substack.com/p/iphone-owners-keep-phones-longer | Confirmed (old; geography not stated) | 2026-10-27 |

Plain reading: **the Android phones in US pockets in late 2026 are typically 2 to 4 years old**, so phones from about 2022 to 2025 (Galaxy S22 to S25, A13 to A17, Pixel 6 to 10) matter most; I found no primary US-only cycle length for Android.

### Android version (API level)

| Fact | Source | Status | Read |
|---|---|---|---|
| US Android versions, September 2026, mobile only: Android 16 46.85%, 13 11.04%, 15 10.74%, 14 9.37%, 12 6.51%, 17 5.73% (sum 90.24%; the page shows no other versions) | https://gs.statcounter.com/android-version-market-share/mobile/united-states-of-america | Confirmed. The mobile-and-tablet view of the same month shows Android 11 at 5.81% and does not list 17. | 2026-10-27 |
| Share of US phones below the app's minSdk 26 (Android 8.0) | not shown | **UNCONFIRMED.** Indirect upper bound: everything not listed is 100 - 90.24 = 9.76%, and that includes Android 11 and 10 and every older version, so the true share below 26 is smaller. | 2026-10-27 |
| Google's own distribution (active Play devices, 7 days, **global, not US**), as of 2025-12-01: 16 7.5%, 15 19.3%, 14 17.2%, 13 13.9%, 12 11.4%, 11 13.7%, 10 7.8%, 9 4.5%, 8.1 2.3%, 8.0 0.8%, 7.1 0.4%, 7.0 0.4%, 6 0.4%, 5.1 0.3%, 5.0 0.1%. Below API 26: 0.4 + 0.4 + 0.4 + 0.3 + 0.1 = **1.6%** (Indirect). API 26 and 27 together 0.8 + 2.3 = 3.1%. | https://9to5google.com/?p=702977 (a news report of Google's update, published 2026-01-30). Google's own page https://developer.android.com/about/dashboards no longer carries a version table (it shows only Vulkan and OpenGL ES, "active devices on Google Play ... 7-day period ending November 24, 2025"). The table lives in Android Studio's new-project dialog, which I cannot open. | Figures are secondary; the owner can read the primary in Android Studio ("Help me choose" under minimum SDK). | 2026-10-27 |

**Takeaway:** about 90% of US Android phones are on Android 12 to 17 (API 31 to 37) and the globally rarest group is API 26 to 28. Testing API 26 is a minSdk safety net, not a population need.

### What is not public for the US

- **Per-model installed base** (how many Galaxy S23s are in US pockets). None of Counterpoint, IDC, Canalys/Omdia, CIRP or StatCounter publishes this free; Counterpoint's channel and sell-through reports are paywalled (I could not open them). Counterpoint's top-5 lists are **sales in a quarter**, not phones in use.
- **Per-model screen size in dp.** Manufacturers publish pixels and pixels-per-inch, not the density the phone actually runs at, and users can change it (Q2). dp for a real model is Indirect until read off the phone with `adb shell wm size` and `wm density`.
- **Your own users' models:** Google's dashboard page points to "Reach and devices in the Google Play Console" for granular data (Confirmed, https://developer.android.com/about/dashboards, read 2026-10-27). That exists only once the app is on Play (Release stage). Until then, ask each tester for model and Android version.

## Q2. What actually makes a button disappear

Brand matters less than this list. "Emulator?" says whether the Android Emulator can reproduce it.

| Cause | What happens | Primary source | Status | Emulator? |
|---|---|---|---|---|
| **Window width / height in dp** | Google: compact width (under 600 dp) is "99.96% of phones in portrait"; compact height (under 480 dp) is "99.78% of phones in landscape"; medium height (480 to 899 dp) is "97.59% of phones in portrait"; expanded height (900 dp and up) is "94.25% of tablets in portrait". Width usually matters more than height. | https://developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes (read 2026-10-27) | Confirmed | Yes (any profile or `wm size`) |
| **Density and "Display size" setting** | Users can change display size, which changes dp width. The Android 16 compatibility definition: the system "MUST NOT scale the display larger than 1.5 times" the native density or "produce an effective minimum screen dimension smaller than 320dp", and not below 0.85x; suggested steps Small 0.85x, Default 1x, Large 1.15x, Larger 1.3x, Largest 1.45x. So **the narrowest phone window you can ever get is 320 dp**. | https://source.android.com/docs/compatibility/16/android-16-cdd, section 7.1.1.3 | Confirmed | Yes (`wm density`, UNCONFIRMED command, see Q3) |
| **Font size up to 200%** | Android 14 and later support font scale up to 200% with a non-linear curve. Google: test with the maximum font size, and never size spacing in sp. | https://developer.android.com/about/versions/14/features#non-linear-font-scaling | Confirmed | Yes (Settings, or a `font_scale` setting; the command is UNCONFIRMED) |
| **Edge-to-edge and system bars** | Android 15 enforced edge-to-edge for apps targeting API 35; targeting 36 removes the opt-out. "If your app is not already edge-to-edge, portions of your app may be hidden and you must handle insets." The app targets 37. Android 17 adds no edge-to-edge change on its behavior-changes page. | https://developer.android.com/develop/ui/compose/layouts/insets ; https://developer.android.com/about/versions/16/behavior-changes-16 ; https://developer.android.com/about/versions/17/behavior-changes-17 | Confirmed | Yes |
| **3-button versus gesture navigation** | Under enforcement "the system status bar and gesture navigation bars are transparent, but the three-button navigation bar is translucent". The repo saw this bug live: in gesture mode the Paywall passed, in 3-button mode "Restore purchase ends at 2400px, under the navigation bar that starts at 2274px" (`android/TESTING.md`, #186). The ticket's own phone, an SM-G996U, uses 3-button navigation. | https://developer.android.com/develop/ui/compose/system/system-bars ; `android/TESTING.md` | Confirmed | Yes (`cmd overlay enable ...navbar.threebutton`, the repo's own recipe) |
| **Display cutouts** | By default apps draw into the cutout area; "Don't obscure list items with the display cutout or the system bars." Developer options has "Simulate a display with a cutout" on Android 9 and up. | https://developer.android.com/develop/ui/views/layout/edge-to-edge ; https://developer.android.com/develop/ui/views/layout/display-cutout | Confirmed | Yes (simulated shapes only) |
| **Keyboard (IME) insets** | The `ime` inset is the space the soft keyboard takes; `safeDrawing` includes it. The app uses `adjustResize` and one `safeDrawingPadding()` at the root (`RigCheckApp.kt`, `AndroidManifest.xml`). | https://developer.android.com/develop/ui/compose/layouts/insets | Confirmed | Yes, but the emulator's Gboard is not Samsung Keyboard |
| **Old Android (API 29 and lower)** | Google: "on devices that run Android 10 (API level 29 and earlier), insets aren't dispatched to siblings after calling WindowInsetsCompat.CONSUMED, which can cause unintended visual overlap." | https://developer.android.com/develop/ui/views/layout/edge-to-edge | Confirmed | Yes (needs an API 26 to 29 system image) |
| **Foldables and large screens** | For apps targeting 36 or higher, orientation, resizability and aspect-ratio restrictions are ignored on displays with smallest width of 600 dp or more, and the opt-out is gone at target 37. The app sets no orientation lock (manifest read), so it will fill any tablet or unfolded window. Samsung lists Z Fold2 main screen 1768 x 2208 at 480 dpi. | https://developer.android.com/about/versions/16/behavior-changes-16 ; https://developer.android.com/about/versions/17/behavior-changes-17 ; https://developer.samsung.com/galaxy-z/testing.html | Confirmed | Yes (foldable AVD profiles; fold posture needs Espresso Device) |
| **Split-screen / multi-window** | Window size can change while running (rotation, multi-window, folding). Samsung: "up to 3 split screen view and 5 pop-up view open simultaneously." Samsung also asks whether the app supports "multi-window and resizable activity properly". | https://developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes ; https://developer.samsung.com/one-ui/largescreen-and-foldable/intro.html | Confirmed | Yes (split-screen); Samsung pop-up view is One UI only |
| **OEM skin (Samsung One UI)** | Samsung's software layer: its keyboard, its navigation settings, its system font, its pop-up view and Edge panel. Samsung publishes "emulator skins" for Galaxy Z (device frame, resolution, density) but nothing I read says they contain One UI software. | https://developer.samsung.com/galaxy-emulator-skin/galaxy-z.html | Skin pages Confirmed; "emulator images are Google builds, not One UI" is **Indirect** (no page states it) | **No** |

Google also warns that edge-to-edge and similar system UI "will still require device tests" when using a JVM simulator such as Robolectric (https://developer.android.com/training/testing/local-tests/robolectric, read 2026-10-27, Confirmed).

### Real dp sizes (computed from published pixels and density)

dp = px / (dpi / 160). Sources: AOSP device definitions `devices.xml` and `nexus.xml` (https://android.googlesource.com/platform/tools/base/+/refs/heads/mirror-goog-studio-main/sdklib/src/main/resources/com/android/sdklib/devices/devices.xml and `nexus.xml`, read 2026-10-27 as base64 decoded by the fetch tool: **verify in Android Studio's Device Manager before relying on one number**), Samsung and Motorola spec pages.

| Device | Pixels, density | Width x height in dp | Status |
|---|---|---|---|
| Android Studio **Small Phone** | 720 x 1280, 320 dpi (xhdpi) | 360 x 640 | Indirect (definition Confirmed) |
| Android Studio **Medium Phone** (your emulator) | 1080 x 2400, 420 dpi | 411 x 914 | Indirect |
| Pixel 3a / 4 / 5 | 1080 x 2220 / 2280 / 2340, 440 dpi | 393 x 807 / 829 / 851 | Indirect |
| Pixel 6 / 7 / 8 | 1080 x 2400, 420 dpi | 411 x 914 | Indirect |
| Pixel 7 Pro | 1440 x 3120, 560 dpi | 411 x 891 | Indirect |
| Pixel 9 / 10 | 1080 x 2424, 420 dpi | 411 x 923 | Indirect |
| Pixel 8 Pro, 9 Pro XL, 10 Pro XL | 1344 x 2992, "xxhdpi" (480) | 448 x 997 | Indirect (bucket read as 480 dpi) |
| Pixel Fold (unfolded) | 2208 x 1840, 420 dpi | 841 x 701 | Indirect |
| Pixel 9 Pro Fold / 10 Pro Fold (unfolded) | 2076 x 2152, 390 dpi | 852 x 883 | Indirect |
| Pixel Tablet | 2560 x 1600, "xhdpi" (320) | 1280 x 800 | Indirect |
| Studio "7.6 inch Fold-in with outer display" (main) | 1768 x 2208, 420 dpi | 674 x 841 | Indirect |
| Samsung Z Fold2 main (Samsung's own table) | 1768 x 2208, 480 dpi | **589 x 736** (under 600, so still "compact" width) | Indirect |
| Samsung Z Flip (Samsung's own table) | 1080 x 2636, 480 dpi | 360 x 879 | Indirect |
| Samsung Z Fold6 main | 1856 x 2160, about 374 ppi, density not published | 707 x 823 at 420 dpi, 825 x 960 at 360 dpi (**600 dp or more at either**) | Indirect |
| Galaxy A17 5G (and probably A16 5G) | 1080 x 2340, 6.7 inch = 385 ppi; density not published | 411 x 891 at 420 dpi, or 360 x 780 at 480 dpi | Indirect, density **UNCONFIRMED** |
| Galaxy S21+ (SM-G996U, the owner's phone) | 1080 x 2400, 6.7 inch (393 ppi, computed); density not published | 411 x 914 at 420 dpi, or 360 x 800 at 480 dpi | Indirect, density **UNCONFIRMED** |
| Moto g 2025 | 720 x 1604, 263 ppi (Motorola US support page: "HD+ (1604 x 720) 263ppi") | 360 x 802 at 320 dpi, or 411 x 917 at 280 dpi | Indirect, density **UNCONFIRMED** |
| Hard floor (CDD) | any phone | width can never go below **320 dp** | Confirmed |

Spec sources: https://www.samsung.com/uk/smartphones/galaxy-a/galaxy-a17-5g-black-128gb-sm-a176bzkaeub/ ; https://developer.samsung.com/galaxy-emulator-skin/galaxy-z.html ; https://developer.samsung.com/galaxy-z/testing.html ; https://en-us.support.motorola.com/app/answers/detail/a_id/184288/~/specifications---moto-g---2025 (all read 2026-10-27; Moto page via search excerpt). No Samsung profile ships in Android Studio's `devices.xml` (every device there has manufacturer "Generic") or the Pixel/Nexus file (Indirect: I saw the definitions through a base64 decode; the tool reported no Samsung entry).

**Observation about the existing emulator:** the Medium Phone is 914 dp tall. Google says 97.59% of portrait phones have a window height between 480 and 899 dp, i.e. your emulator is taller than the bucket nearly all phones are in. Whether Google's measurement counts the system bars is not stated (**UNCONFIRMED**), so treat "the emulator is taller than a typical phone" as likely, not proven. A shorter profile (about 780 to 850 dp) is a closer match to a typical Galaxy A-series window.

## Q3. How to expand testing, cheapest first

| Option | What it varies | Cost in time and money | Reboot? | Reproduces real insets? | Source and status |
|---|---|---|---|---|---|
| **(0) In-test overrides** inside the instrumented tests you already have: `DeviceConfigurationOverride` (forced size, font scale, theme) and the pattern already in `PaywallScreenTest` (`Density(..., fontScale = 2f)` in a 360 dp box) | width, height, font scale | Seconds per case, no boot, no money | No | **No** (a forced size does not change the real bars; `SystemBarsTest` covers those) | https://developer.android.com/training/testing/different-screens/tools (read 2026-10-27): Confirmed |
| **(1) Same AVD, different settings**: `wm size`, `wm density`, `font_scale`, the navigation overlay | size, density (= "Display size" setting), font, nav mode | Seconds, no money | No | Yes, mostly (the system recomputes bars) | Nav overlay Confirmed by the repo's own recipe (`android/TESTING.md`). Google's `adb` page documents `am display-size` and `am display-density` (override size and density), **not** `wm size`, `wm density` or `settings put system font_scale`: those three are **UNCONFIRMED** here, widely used, to be tried once. Font size via Settings is Confirmed (Android 14 page). |
| **(1b) Espresso Device**: `onDevice().setDisplaySize(widthSizeClass, heightSizeClass)`, `setTabletopMode()` | window size class, fold posture, at run time | Seconds, no boot | No | Yes | Alpha; needs AGP 8.3+, emulator 33.1.10+, an AVD at API 24+ (Confirmed, tools page above). The repo is on AGP 9.3.1 (`libs.versions.toml`). Moves between size classes, not arbitrary dp. |
| **(2) More AVD profiles** in Android Studio (clone a hardware profile; set resolution and screen size) | everything physical | Disk on G:; about 1 min boot each (repo), one at a time | Yes | Yes | Confirmed (https://developer.android.com/studio/run/managing-avds): preloaded profiles cannot be edited, clone them; the Device Manager density field is **not** documented there. |
| **(3) Gradle Managed Devices (GMD)** | AVD per profile + API, created and torn down by Gradle; groups; shards | Automates (2). Group members run "in parallel" per the page, which the repo's one-emulator rule forbids; run one device per Gradle call. Sharding "can cause timeout errors" when devices cannot be provisioned. | Yes (automated) | Yes | https://developer.android.com/studio/test/gradle-managed-devices (Confirmed). As read: API 27+; image sources `aosp`, `google`, `aosp-atd` (ATD "API 30 only" and "Screenshot tests that depend on hardware rendering aren't supported"), `google-atd`. The page gives no speed numbers. The repo's suite needs the Google Play image and the software GPU (`swangle_indirect`); GMD documents `swiftshader_indirect`; whether it maps is **UNCONFIRMED**. |
| **(4) JVM screenshot tests** (no emulator) | many sizes/fonts/themes per run | Seconds each (**UNCONFIRMED**: no primary timing); one-time setup; adds Robolectric or layoutlib to the build | n/a | **No** (Google: system UI such as edge-to-edge still needs device tests) | See table below |
| **(5) Real-device cloud** | real hardware, Samsung skins | See pricing below | n/a | Yes, real | See below |
| **(6) Owner's own phone(s)** | one real sample each | Free | n/a | Yes, real | The S21+ is already in use as a test phone (`android/TESTING.md`) |

### JVM screenshot tools

| Tool | Device configs | Maturity (as read) | Source |
|---|---|---|---|
| **Compose Preview Screenshot Testing** (Google) | `@Preview` parameters such as `uiMode`, `fontScale`, multi-previews; the page documents no `device` parameter | The standalone `com.android.compose.screenshot` plugin "is no longer maintained"; Google recommends AGP test suites with **AGP 9.5 or higher**; the repo is on AGP 9.3.1. Host-side, "can be memory-intensive" (heap 4g setting). Confirmed. | https://developer.android.com/studio/preview/compose-screenshot-testing (2026-10-27) |
| **Paparazzi** (Cash App) | `PIXEL_5` shown; other `DeviceConfig`s are in its docs (not read) | 2.0.0-alpha05.1 in the README; Apache-2.0; "render your application screens without a physical device or emulator". Says nothing about system bars. | https://github.com/cashapp/paparazzi (2026-10-27): Confirmed |
| **Roborazzi** | `@Config(qualifiers = RobolectricDeviceQualifiers.Pixel5)`, night, locale, screen sizes such as `MediumTablet`; needs `@GraphicsMode(NATIVE)`; has an accessibility-check module | Apache-2.0; about 1.1k stars; latest release not read | https://github.com/takahirom/roborazzi (2026-10-27): Confirmed (page partly read) |
| **Compose accessibility checks** | `enableAccessibilityChecks()` from Compose 1.8.0; flags missing labels, contrast, "small touch target size", traversal order | A check, not a layout matrix; no touch-target number on the page | https://developer.android.com/develop/ui/compose/accessibility/testing: Confirmed |
| Google's view of Robolectric | Runs Compose UI tests on the JVM; "Use Robolectric to take screenshots when the pixel accuracy is not critical"; system UI such as edge-to-edge "will still require device tests" | | https://developer.android.com/training/testing/local-tests/robolectric: Confirmed |

For this project JVM screenshots check "does the layout wrap or clip at this width and font", but not the real-bars bug that #186 was. They are a Beta-stage option, not an Alpha need (Q7). The repo has no Robolectric dependency today (`build.gradle.kts` read).

### Real-device clouds

| Service | Facts | Source | Status |
|---|---|---|---|
| **Firebase Test Lab (FTL)** | Spark plan free daily quota: virtual devices 10 tests/day, up to 60 min/day; physical devices 5 tests/day, up to 30 min/day. Blaze: **$1 per virtual device-hour, $5 per physical device-hour**, billed per minute rounded up. **"Firebase Test Lab is deprecated and will be fully shut down on September 30, 2027."** Replacement: Developer Device Platform on Google Cloud. | https://firebase.google.com/pricing ; https://firebase.google.com/docs/test-lab/migrate-faq (2026-10-27) | Confirmed |
| **Developer Device Platform (DDP)**, Google Cloud, Preview | Matches FTL rates "until April 30, 2027"; after that "pay-per-use and per-device slot subscription options", price not published; **requires billing enabled; the pages mention no free quota**; Preview supports Android Instrumentation and iOS XCTest, **Robo test not mentioned**. | https://firebase.google.com/docs/test-lab/migrate-faq ; https://docs.cloud.google.com/developer-device-platform/device-run/migrate ; https://docs.cloud.google.com/developer-device-platform/pricing (rates not on the page) | Confirmed; price after 2027-04-30 **UNCONFIRMED** |
| DDP device catalog | Physical Samsung: S20 FE to S26 families (Android 33 to 36), A03s to A56 (Android 29 to 36, includes A16 and A05s), Z Fold3/4/5/6/8, Z TriFold; physical Pixel: 3 (Android 28), 5 (30), 6 to 11, Pixel Fold, 9 and 10 Pro Fold, Pixel Tablet; **virtual** devices are generic only: Medium Phone (Android 26 to 36), Small Phone (26 to 35), Medium Tablet. | https://docs.cloud.google.com/developer-device-platform/device-catalog (2026-10-27) | Confirmed (a Galaxy A17 is not in the list I saw) |
| FTL device page | Lists only deprecated devices (Galaxy Tab S3, Galaxy Z Fold2 planned removal 2026-02-13); live list via `gcloud firebase test android models list` | https://firebase.google.com/docs/test-lab/android/available-testing-devices | Confirmed |
| **Samsung Remote Test Lab** | Real Samsung devices through a browser web client; "Sign up - it's free!" for membership; featured devices Galaxy Z Fold8, Z Flip8, S26 Ultra, Tab S11. Per Samsung's FAQ (search excerpt; the FAQ page itself was empty to the tool): **20 free credits a day, 1 credit = 15 minutes, minimum reservation 30 min (2 credits), maximum 10 hours a day (40 credits)**; unused time is returned. Whether it takes an automated test run or only a person driving the phone: **UNCONFIRMED**. | https://developer.samsung.com/remote-test-lab ; https://developer.samsung.com/remotetestlab/docs/2/faq | Landing page Confirmed; credit limits **Indirect** (search excerpt) |
| **AWS Device Farm** | **$0.17 per device minute** after a one-time 1,000-minute trial; unmetered slot **$250 per slot per month**, per device family (Android or iOS) and usage type. Samsung models in its catalog: not checked. | https://aws.amazon.com/device-farm/pricing/ | Confirmed |
| **BrowserStack** | App Live and App Automate prices are not on the pricing page ("contact sales"); only web products are priced (e.g. Automate Desktop & Mobile $175/month, 1 parallel). | https://www.browserstack.com/pricing | No primary app-testing price: **UNCONFIRMED** |

## Q4. Which configurations to test

Axes behind the sets: width dp x height dp x system-bar insets/cutout x font scale x navigation mode x API level x skin (Q2). Names use profiles that ship in Android Studio or in Google's cloud catalog.

### Tier 1: 4 corner configurations (emulator only)

| # | Profile (dp) | API | Font | Nav | Why it is in | Stands in for |
|---|---|---|---|---|---|---|
| 1 | Medium Phone 411 x 914 (today's) | 36 | 1.0 | gesture | Baseline; API 36 is past edge-to-edge enforcement (35) and in the 16-and-up predictive-back era | Pixel 6/7/8/10 (Pixel new), Galaxy S21+ pixels (old Samsung, its real density unknown) |
| 2 | **Small Phone 360 x 640**; also try `Display size` to the 320 dp floor | 36 | **2.0** | **3-button** | Smallest and shortest window, biggest text, tallest bottom bar: the #186 bug class, all at once | Budget Moto g / Galaxy A at 360 dp wide (shorter than any real one, deliberately harsh) |
| 3 | **Pixel 9 Pro XL 448 x 997** (or Pixel 8 Pro) | 37 (newest) | 1.0 | gesture | Tallest and widest common phone; newest API | Samsung high-end (S25/S26 Ultra class; its density is unpublished) and Pixel new Pro |
| 4 | Medium Phone-class, **Pixel 3a-like 393 x 807** if a profile is added | **26** (minSdk) | 1.15 | 3-button | Oldest supported Android, old inset behaviour (API 29 and lower), older-phone proportions | Pixel old (3a/4/5: Pixel 3 is API 28 and Pixel 5 API 30 in the cloud catalog), old Samsung |

### Tier 2: add 4 more (8 total)

| # | Config | Why |
|---|---|---|
| 5 | Pixel Fold unfolded 841 x 701 (or Studio "7.6 inch Fold-in" 674 x 841), API 35 | Width of 600 dp or more: size-class switch; Android 16+ ignores orientation locks here |
| 6 | Config 1 rotated to landscape, then split-screen (height under 480 dp) | Compact height: where bottom buttons drop under the bars |
| 7 | Config 2 or 1 with a simulated cutout (top-center, corner, double) | Cutout push on the first row |
| 8 | A "Galaxy A-class" custom profile 1080 x 2340 at 420 and at 480 dpi (411 x 891 and 360 x 780), API 34 | The commonest US Android size class (A16/A17) at both plausible densities, until the real density is read off a phone |

### Tier 3: 12 or more (add 4+)

| # | Config | Why |
|---|---|---|
| 9 | Display size at Largest (1.45x) and Smallest (0.85x) on config 1 | Density extremes the CDD allows |
| 10 | Mid API (31 to 33), 3-button, font 1.3 | Mid-life phones (Android 12 to 14 are about 27% of US Android on StatCounter: 6.51 + 11.04 + 9.37 = 26.9 of 90.24 listed) |
| 11 | Pixel Tablet 1280 x 800 | Ignored orientation lock; very wide |
| 12 | **Real Samsung One UI**: owner's Galaxy S21+; then a Galaxy A17-class phone (or Samsung Remote Test Lab / DDP catalog A-series, S-series, Z Fold) | The only way to see Samsung Keyboard, One UI navigation, fonts, pop-up view |
| 13+ | Real Pixel old (cloud Pixel 5, Android 30) and a Motorola | Brand-specific skins; Motorola is not in the DDP catalog list I saw (UNCONFIRMED for other clouds) |

Mapping to the owner's categories: **high-end Samsung** = config 3 on the emulator for size, a real S-series via Samsung Remote Test Lab or DDP for the skin. **Old Samsung** = the owner's S21+ (real) plus config 1. **Pixel** = configs 1 and 3. **Old Pixel** = config 4 (and a cloud Pixel 3 or 5 if wanted). **Motorola / budget** = config 2 and config 8 (the Moto g's density is not published, so its dp is a range).

## Q5. The break point: coverage versus number of configurations

**What I can and cannot support.** Google's size-class percentages (Q2) say 99.96% of phones have a compact width and 97.59% of portrait phones a medium height, so size classes are too coarse to tell phones apart: nearly every phone lands in the same box. The useful measure of layout risk is therefore the **distinct buckets of (width dp x height dp x insets/cutout x font scale x nav mode x API x skin)** that each reproduce a *different failure*, not brand share. No source publishes the share of US phones per bucket, so the table counts **risk classes**, which is my own classification, not a measured population. The one population number I can give is vendor: Samsung is about 61% to 65% of US Android (Q1).

Twelve risk classes: R1 nominal phone (about 411 x 900); R2 narrow (360 dp or less); R3 short (about 650 dp or less); R4 tall or wide (448 dp wide or 950 dp tall and up); R5 large font (2.0); R6 3-button bar; R7 old API (26 to 29, old inset dispatch); R8 newest APIs (35 and up, enforced edge-to-edge); R9 600 dp or wider (foldable, tablet); R10 cutouts; R11 landscape or split-screen (height under 480 dp); R12 OEM skin (needs real hardware).

| Configurations | What it adds | Risk classes covered (of 12) | What it still misses |
|---|---|---|---|
| 1 (Medium Phone) | R1, R8 | **2** | Everything that is not the nominal phone, including the bug #186 found |
| 2 (+ Small Phone, font 2.0, 3-button) | R2, R3, R5, R6 | **6** | Tall/wide, old API, folding, cutout, landscape, skin |
| 4 (Tier 1) | R4, R7 | **8** | Large widths, landscape, cutouts, skin |
| 6 | R9, R11 | **10** | Cutouts, skin |
| 8 (Tier 2) | R10 (config 7, a simulated cutout); config 8 re-checks the commonest Samsung A-class size and adds no new class | **11** | Skin only (needs real hardware) |
| 12 (Tier 3 incl. 1 to 2 real Samsungs) | R12 (S21+ and an A-class) | **12** | Combinations of the above; brand-specific quirks of other makers |
| 20 | Combinations only | **12** | Nothing new by class; it re-runs earlier classes in different mixes |

**Where the curve flattens (the break point): at about 4 configurations the curve is steepest (2 to 8 classes); between 6 and 8 it finishes the emulator-reproducible classes (11 of 12); 12 adds only the real-Samsung class; 20 adds none.** The reasoning behind that flattening is an assumption: a button that fits at the smallest window with the largest font and the tallest bar will usually fit in every larger window (the "monotonic" argument). It fails at breakpoints (a layout switching at 600 dp), at odd cutout positions and where a vendor changes the system, which is why R9 to R12 get their own configurations. Until a bug shows otherwise, treat the argument as sound for scrolling single-column screens like this app's, and **UNCONFIRMED** as a general rule.

Vendor coverage that a real device adds (Indirect, Q1): one Samsung phone stands for 61% to 65% of US Android by vendor; a Galaxy A17-class device (1080 x 2340) stands for the screen class of the two best-selling Android phones, about 35% of US Android shipments in Q2 2026.

## Q6. Cost model with the owner's real numbers

### (a) Simulation time, one emulator at a time

Measured in this repo (`android/TESTING.md`): the instrumented suite is 148 tests; on the software GPU it took **252 to 262 s** by `am instrument` (4 warm-reuse runs), **275 to 308 s** with a fresh boot per run (5 runs), and **5 min 10 s to 5 min 50 s** through Gradle, `BUILD SUCCESSFUL in 5m 35s` including APK build and install (2026-10-21, `medium_phone`, API 36). The restart before each run "costs about a minute" (repo; no stopwatch figure). Warm reuse of one boot is not allowed for full suites (host GPU: 3 of 4 warm runs failed; software GPU: reuse passed but the rule stays). Google: a snapshot boot can be "up to 10 times faster" than a cold boot, and "Snapshots are not reliable when software rendering is enabled" (https://developer.android.com/studio/run/emulator-snapshots, 2026-10-27), which is why the repo cold-boots.

| Configurations | (i) Full instrumented suite (1 min boot + 5.5 min each; measured basis) | (ii) "Does every button show" smoke (1 min boot + 1.5 min each; the 1.5 min is an **assumption**, no smoke class has been timed) |
|---|---|---|
| 1 | 6.5 min | 2.5 min |
| 4 | 26 min | 10 min |
| 8 | 52 min | 20 min |
| 12 | 78 min | 30 min |

Changing size, density, font or navigation on a booted emulator takes seconds and needs no boot, so a smoke run over several settings on one boot costs less than the table's one-boot-per-configuration worst case. Each different AVD or API image still needs its own boot, and creating AVDs writes outside the repo (the default AVD folder is under the user profile on C:, which is nearly full; check where `medium_phone` lives and ask before creating more).

### (b) AI time and money with Artemis

Facts: Artemis Flash is about 3 to 5 s a step and Pro about 15 to 40 s a step; its default model is `gemini-3.8-flash`; its config gives the **planner, operator and checker the same default model** (Pro differs by running three roles with `thinking_level` high or medium and a checker with up to 20 iterations) (https://raw.githubusercontent.com/google/artemis/main/config/artemis.jsonc, read 2026-10-27, Confirmed; the config has no cost or token-limit field and a `context_budget_tokens` of 80,000). Price, standard paid tier, per 1 million tokens (https://ai.google.dev/gemini-api/docs/pricing, read 2026-10-27, Confirmed): **`gemini-3.8-flash` input $0.75 and output $3.75 through December 31, 2026, then $1.50 and $7.50 from January 1, 2027**; `gemini-3.1-pro-preview` input $2.00 and output $12.00 (prompts up to 200k tokens). Image input: "Larger images are tiled into 768x768 pixel tiles, each costing 258 tokens" (https://ai.google.dev/gemini-api/docs/image-understanding, Confirmed for the older scheme; Gemini 3 uses a `media_resolution` setting whose token counts the page does not list).

**Tokens per step: UNCONFIRMED.** Artemis publishes no per-step figure (its own `token_meter.py` is not in the config). My labelled assumptions: a screenshot plus UI element list plus history.

| Assumption | Flash profile (1 model call per step) | Pro profile (3 calls per step) |
|---|---|---|
| Low | 6,000 in / 300 out | 18,000 in / 1,500 out |
| Middle | 12,000 in / 700 out | 36,000 in / 3,000 out |
| High | 25,000 in / 1,500 out | 75,000 in / 6,000 out |

Formula: cost per step = (input tokens x $0.75 + output tokens x $3.75) / 1,000,000 (double both prices from 2027-01-01). Per run = steps x cost per step. Wall time per run = steps x seconds per step. Steps per scenario: **15 (low), 25 (middle), 40 (high), assumed**. Seconds per step: Flash 3 / 4 / 5; Pro 15 / 25 / 40.

| Per scenario | Time | Cost (to 2026-12-31) |
|---|---|---|
| Flash, low | 45 s | $0.084 |
| Flash, **middle** | 100 s | **$0.29** |
| Flash, high | 200 s | $0.98 |
| Pro, low | 225 s | $0.29 |
| Pro, **middle** | 625 s (10 min) | **$0.96** |
| Pro, high | 1,600 s (27 min) | $3.15 |

Middle case, configurations x scenarios, added to one boot (1 min) per configuration. Cost is shown to 2026-12-31 and, in brackets, from 2027-01-01.

| Configurations x scenarios | Flash time | Flash cost | Pro time | Pro cost |
|---|---|---|---|---|
| 1 x 5 | 8 + 1 = 9 min | $1.45 ($2.91) | 52 + 1 = 53 min | $4.78 ($9.56) |
| 1 x 10 | 17 + 1 = 18 min | $2.91 ($5.81) | 104 + 1 = 105 min | $9.56 ($19.13) |
| 4 x 5 | 33 + 4 = 37 min | $5.81 ($11.63) | 208 + 4 = 212 min (3.5 h) | $19.13 ($38.25) |
| 4 x 10 | 67 + 4 = 71 min | $11.63 ($23.25) | 417 + 4 = 421 min (7 h) | $38.25 ($76.50) |
| 8 x 5 | 67 + 8 = 75 min | $11.63 ($23.25) | 417 + 8 = 425 min (7 h) | $38.25 ($76.50) |
| 8 x 10 | 133 + 8 = 141 min | $23.25 ($46.50) | 833 + 8 = 841 min (14 h) | $76.50 ($153) |
| 12 x 5 | 100 + 12 = 112 min | $17.44 ($34.88) | 625 + 12 = 637 min (10.6 h) | $57.38 ($114.75) |
| 12 x 10 | 200 + 12 = 212 min | $34.88 ($69.75) | 1,250 + 12 = 1,262 min (21 h) | $114.75 ($229.50) |

Low-to-high range for the cells that matter (all-low to all-high): Tier 1 with 5 Flash scenarios (4 x 5 runs of 15 to 40 steps) is **$1.69 to $19.50** and 19 to 71 min plus boots; with Pro **$5.74 to $63.00** and 79 to 537 min plus boots. If Pro were pointed at `gemini-3.1-pro-preview` instead of the default model, the middle-case step would cost $0.054 (low) to $0.222 (high), about 3 to 10 times more again (Indirect; Artemis can be configured for another provider per its `.env.example`, see `docs/research/artemis-android-testing.md`).

**Reading it:** Flash across Tier 1 is affordable and fast enough for a pre-release pass (about 37 min, $6 in the middle case). Pro across a matrix is not: Tier 1 x 5 scenarios is about 3.5 hours. Artemis Flash also has no pre-execution safety net (that file), so keep it on read-only "look at this screen" scenarios.

### (c) The cheaper alternatives, priced the same way

Assumption (**UNCONFIRMED**): one full instrumented suite on a cloud device takes about 10 minutes billed (install, 148 tests, report); this repo's local figure is 5.5 min, no cloud timing exists.

| Configurations x 10 min | FTL / DDP virtual ($1/h) | FTL / DDP physical ($5/h) | AWS Device Farm ($0.17/min) | Samsung Remote Test Lab |
|---|---|---|---|---|
| 1 | $0.17 | $0.83 | $1.70 | free (20 credits = 300 min a day) |
| 4 | $0.67 | $3.33 | $6.80 | free, but see below |
| 8 | $1.33 | $6.67 | $13.60 | |
| 12 | $2.00 | $10.00 | $20.40 | |

FTL's free Spark quota (60 virtual min or 30 physical min a day) would cover 3 physical device runs of 10 min, but FTL shuts down 2027-09-30 and the DDP that replaces it needs billing and shows no free quota. Samsung Remote Test Lab: 20 credits a day at 15 minutes each is 300 minutes, but it is a browser session on a real Samsung phone; an automated suite run is not documented (**UNCONFIRMED**). It suits a human walking screens on a Fold or an S-series, free of charge.

Other costs: the owner's old phone is free; one new Galaxy A-class phone is a one-time purchase (price not researched); JVM screenshot tools cost setup time only (no primary figure).

## Q7. Phased recommendation

| Stage | Do | Cost | Where it belongs |
|---|---|---|---|
| **Alpha** (5 testers) | (1) Add "phone model and Android version" to the tester guide's feedback email; costs nothing. (2) On the owner's S21+: read `adb shell wm size`, `wm density`, `getprop ro.build.version.sdk` once and record the real dp. (3) Extend existing Compose tests with a small table of (width, height, font scale) cases that assert every primary button is displayed and inside the safe area (the `PaywallScreenTest` pattern; `DeviceConfigurationOverride`). (4) Run the existing `SystemBarsTest`-style check on Tier 1's four emulator settings by changing size, font and nav on the one AVD, before each APK. (5) Optional: one Artemis Flash scenario, "walk every screen and report any button cut off or hidden", on each Tier 1 setting. | About 10 min of emulator time per APK (assumed smoke), $0.3 to $1 per Artemis scenario (middle case), near zero otherwise | (2)-(4) deterministic; (5) exploration, never a gate |
| **Beta** (under 20) | Tier 2 (8 configurations) as a smoke run on the emulator; one real Galaxy A-series phone (or Samsung Remote Test Lab credits for an A-series, S-series and Fold session) because Samsung is 61% to 65% of US Android; use the models Alpha feedback reported to add the commonest one not yet seen; optionally try Roborazzi or the AGP screenshot route for font/size matrices. Do not build on FTL. | About 20 min emulator smoke (assumed); free Samsung credits; optional ~$10 of cloud minutes | Deterministic Compose tests for presence/reachability; JVM screenshots for wrap/clip; a person on Samsung hardware for One UI |
| **Release** | Tier 3 (12) per release candidate: emulator Tier 1 and 2, real-device cloud pass over Samsung A, S and Fold plus a Pixel and a Motorola if the catalog has them (DDP or AWS Device Farm; about $10 to $20 per pass at the stated rates, 10-minute assumption), and then use Play Console "Reach and devices" to replace this guess with the app's real top models. | About $10 to $20 per release candidate for cloud, 78 min emulator for full suites (or 30 min smoke) | Real devices catch what emulators cannot |

**Ask the owner:**
1. Is the S21+ available as the standing "old Samsung" test phone, and may I read its `wm size` and `wm density` (read-only)?
2. Budget for one Galaxy A17-class phone for Beta (yes or no), and a monthly cap for the Gemini key if Artemis is used (the middle case suggests $10 to $20 per pre-release matrix).
3. Permission to create 3 or 4 extra AVDs (Small Phone, Pixel 9 Pro XL, an API 26 image, Pixel Fold) and where they should live, since the default folder is on C:.
4. Whether to wait for the Alpha feedback to see which models actually appear before building Tier 2.

## Risks and open items

- **Per-model dp for Samsung and Motorola phones is not published.** Use the real phone or a range; do not hard-code a profile as "the A17".
- **The `wm size`, `wm density` and `font_scale` commands are not on a page I read.** Try them once on the emulator; the navigation overlay command is already proven in this repo.
- **Cold-boot flakiness and one emulator at a time** (repo) mean the "Full suite" column is a minimum; every extra AVD multiplies exposure to the aborts described in `android/TESTING.md`.
- **Firebase Test Lab ends 2027-09-30; DDP is Preview, billed, Samsung/Pixel physical only, instrumentation tests only.** Anything built on either may need to move again.
- **Artemis token use is a guess.** Measure the first ten runs before trusting the cost table; its project is young (`docs/research/artemis-android-testing.md`).
- **StatCounter's vendor split has Xiaomi at 5.89% in the US, which Counterpoint's shipment data does not support.** The Samsung share could be higher than 61% on StatCounter's own numbers if that vendor tag is a mislabel.
- **My risk-class counts are classification, not measurement.**

## What I could not find

- US installed base by phone model, from any free primary source.
- Google's current Android version table on a web page (only in Android Studio); the global numbers above came through a news report of Google's update.
- A US-only phone replacement cycle for Android (CIRP 2023 gives a split without a stated country; Counterpoint and Omdia give global figures).
- Counterpoint's top US Android models beyond the Q2 2026 top 5, and its installed-base data (paywalled).
- Per-step token use or cost for Artemis; cloud timing for this app's suite.
- Developer Device Platform prices after 2027-04-30; BrowserStack app-testing prices; AWS Device Farm's Samsung catalog.
- Samsung Remote Test Lab's rules for automated runs and its current credit limits from the FAQ itself (the page was empty to the fetch tool).
- Samsung's published density for Galaxy S21+, A16, A17, Z Fold6 and S25; Motorola's for the Moto g; the Galaxy A16 5G display page.
- A primary statement that Android Emulator images do not contain Samsung One UI (inferred only).
- Whether Google's window-height percentages include the system bars.
