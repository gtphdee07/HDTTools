# Test audit: Android (`android/`)

Audited 2026-10-04 by the test-audit-android agent against `docs/test-audit/rules.md`. Facts marked (measured) come from commands run in this audit; everything else is read from files. No device, emulator, live or paid test was run, and nothing was deployed.

## 1. Summary

1. Worst gap: Android's only enforced coverage number (71.00% baseline in `scripts/coverage_gate.py`) comes from the device-only Major suite, so a session-end JVM run has no coverage verdict. JVM-only coverage is 6.92% (measured), and `ScanApiClient`, `RecentRigsRepository`, `RigCheckViewModel`, `ScanFieldMapping` and `PhotoEncoding` have 0% JVM coverage.
2. A JVM-only session-end run works today with one command (`./gradlew test`, 38 tests, 21 s warm, measured), but nothing wraps it and nothing runs static checks with it. `detekt` could not run offline here (its tool dependencies are not in the Gradle cache), and it enables only two rules.
3. Android's third-party surfaces are thin in the freshness system: only `revenuecat-rest` lists `android` (via the Worker file). The RevenueCat Android SDK (#39) and Google Play Billing (#40) surfaces are not in the manifest, no Android test carries a surface tag, and `external_freshness.py` has an npm fetcher only (no Maven).
4. The Android release step (`android/test-weekly.ps1`) runs `wrangler deploy` of the Worker, then paid scans, and does not call `external_freshness.py`. ADR-0008's Android gate is not built. Its recorded result uses the legacy `android/weekly` key, which the gate ignores.
5. The golden-vector port is fully run (14 of 14 cases, none skipped) but the fixture lacks GCWR cases (#47 not started); Disclaimer gate, Rig and scan each have an offline test, History does not exist on Android.

## 2. Inventory

Android's test layout maps onto `TESTING.md` categories as follows. The repo's Android names are Minor (JVM) / Major (instrumented, offline) / External (instrumented, real RevenueCat and Worker). Counts are `@Test` annotations (grep) except the JVM numbers, which are JUnit XML from the measured run (`android/app/build/test-results/testDebugUnitTest/`).

| Group | Category | Files / tests | Command | Needs |
|---|---|---|---|---|
| JVM unit ("Minor") | 1 function, 3 module (the breakdown port is one module) | 7 files, 38 tests: `BreakdownTest` 17, `VerdictTest` 6, `GuideRectMathTest` 5, `RevenueCatManagerTest` 4, `NumberFormattingTest` 3, `BreakdownGoldenVectorTest` 2, `ExampleUnitTest` 1 (placeholder) | `cd android; ./gradlew test` (measured: BUILD SUCCESSFUL, 38/38 pass, 0 skipped) | JDK 21 toolchain and Gradle cache. No network (ran with `--offline`), no device, no secrets |
| Instrumented offline ("Major") | 2 interaction, 3 module (Compose screens with fake params, NavHost flow) | 14 files, 60 tests besides the External class (count includes 7 in `ScanFixturePoolTest`, 2 in `CameraOverlaySpikeExifTest`, 1 placeholder `ExampleInstrumentedTest`). Screens: Results 8, Paywall 7, Truck entry 6, Chooser 5, RigPicker 4, ScaleTicket 2, TrailerTag 2, Disclaimer 1. Components: CreditBalanceChip 5, BreakdownRow 3, ReferenceImageCard 3. Navigation: `RigCheckNavHostTest` 4 | `cd android; ./gradlew connectedDebugAndroidTest` (not run) | A booted device or emulator; the task depends on `wakeEmulatorForInstrumentedTests`, which needs `adb` from the SDK. No network. `Purchases.configure()` never runs (`CustomTestRunner`) |
| External | 5 external | `PaywallScreenWeeklyTest` 6 tests (real offerings, real Test Store purchase, real scan, duplicate-scan idempotency, two scan-fixture pool tests) | `cd android; .\test-weekly.ps1` (not run) | Device or emulator, network, the Worker (the script runs `npm run typecheck` then `npm run deploy` first), and the `weekly-test-user` RevenueCat customer. Costs two real Claude calls (about $0.02) per `android/TESTING.md` |
| Fixture contract | 4 inter-module (cross-platform) | `BreakdownGoldenVectorTest` reading `test-vectors/breakdown_cases.json` (14 cases) | part of `./gradlew test` | none |

Notes:
- Category 4 for the Worker boundary is not an Android test: `android/TESTING.md` says the Worker's own External suite runs first, then the Android External suite. There is no offline test of the Android to Worker request/response contract (`ScanApiClient.kt` has no JVM test).
- Runtime (measured): `./gradlew test --offline` 20.9 s with 24 of 25 tasks up to date, so this is a warm figure; a cold compile was not measured. JUnit total time for the 38 tests was about 4.2 s, 3.95 s of it in `RevenueCatManagerTest` (mockk start-up). Instrumented and External runtimes were not measured (device needed); `android/TESTING.md` records earlier counts (Minor 38, Major 57 at 2026-09-09), so the Major count has since grown by 3 or the earlier figure excluded the placeholder or pool tests (not verified).
- Placeholder tests: `ExampleUnitTest.kt` and `ExampleInstrumentedTest.kt` are Android Studio templates, counted above, with no value as coverage.
- `ScanFixturePoolTest` (7 tests, under `androidTest`) tests pure Kotlin test-support code and needs no device logic; it runs on the device only because of where it lives.

## 3. Code coverage

JVM coverage (measured, `./gradlew testDebugUnitTest createDebugUnitTestCoverageReport --offline`, report at `android/app/build/reports/coverage/test/debug/index.html`):

- App-wide instruction coverage: 16,087 of 17,283 instructions missed, so 6.92% covered. Excluding `ui.experiments.cameraoverlay` (the gate's exclusion list), 7.08%, computed with `scripts/coverage_lib.py parse_android_report`.
- Per-file line from the report (percent covered): `domain/Breakdown.kt` 99, `BreakdownItem.kt` 100, `Tone.kt` 100, `NumberFormatting.kt` 100 (both copies), `VerdictInfo.kt` 97, `ScaleTicket.kt` 95, `TruckTag.kt` 92, `TrailerTag.kt` 88, `RevenueCatManager.kt` 15, `CameraOverlaySpikeScreen.kt` 5. Everything else is 0%.
- 0% under the JVM suite and of consequence: `data/ScanApiClient.kt` (the paid scan call, request building and error mapping), `data/ScanFieldMapping.kt` (how scan JSON becomes tags; the root `TESTING.md` line 81 says the field names are contract-tested elsewhere), `data/RecentRigsRepository.kt` (saved Rigs persistence), `data/PhotoEncoding.kt`, `data/ScanPhotoStorage.kt`, `domain/model/RecentRig.kt`, `ui/RigCheckViewModel.kt` (credit balance, scan, purchase and save flows), and all of `ui/screens`, `ui/components`, `ui/navigation` (expected: Compose, covered by the device suite).
- `RevenueCatManager.kt` at 15% JVM: only `getScanCreditBalance()` and `appUserId` are tested offline (4 tests). `getOfferings`, `purchasePackage`, `restorePurchases` and the three callback objects have no JVM test.

Device-suite numbers are recorded in `android/TESTING.md` and could not be reproduced here (no `.ec` file and no device): Major 73.50% (gate baseline 71.00%), Major plus External merged 78.38% (informational), per `android/TESTING.md` at 2026-09-09. The release gate (`scripts/coverage_gate.py`: `ANDROID_REPORT` is the `androidTest/debug/connected` report; `get_android_result` runs `connectedDebugAndroidTest` if that report is missing) never reads the JVM report. The gate is also a hard floor against a baseline, which rule 9 says the owner has not yet decided; rule 9 asks for gaps with no verdict.

To get JVM-only coverage offline (done here): `./gradlew testDebugUnitTest createDebugUnitTestCoverageReport` then `scripts/coverage_lib.py` for the number. The `.exec` file is at `android/app/build/outputs/unit_test_code_coverage/debugUnitTest/testDebugUnitTest.exec`. Merged Major plus External uses `jacocoMergedCoverageReport` (`android/app/build.gradle.kts`) and needs the two `.ec` files from device runs.

## 4. Feature coverage

Requirements come from `android/CONTEXT.md`, `CONTEXT-MAP.md`, issues #15 and #47, and `android/TESTING.md`.

| Feature / requirement | Verifying test | Offline? |
|---|---|---|
| Breakdown math port (Rig, Breakdown, Item, Tone, Verdict) against the shared fixture | `BreakdownGoldenVectorTest` (all 14 `breakdown_cases.json` cases run; the "report skipped" test prints "14/14 ... Skipped:" with an empty list, measured) plus `BreakdownTest` (17) and `VerdictTest` (6) | yes, JVM |
| Disclaimer gate (blocking, once per app session, never persisted) | `DisclaimerScreenTest` (copy renders, acknowledge fires callback); `RigCheckNavHostTest.newRigHappyPathShowsDisclaimerThenResults` and `recentRigSelectionRoutesThroughTheChooserAndSkipsTheDisclaimerSecondTime` (second pass skips it). Nothing tests "re-appears on every app launch" (the session flag lives in `RigCheckViewModel.disclaimerAcknowledged`; no ViewModel JVM test) | device only |
| Rig: save and pick a recent Rig | `RigPickerScreenTest` (4: card tap, create disabled until nickname, create fires, chip tap), `RigCheckNavHostTest` recent-rig route. Persistence itself (`RecentRigsRepository`, DataStore) has none | UI device only; persistence none |
| History | not an Android feature (`grep -i history android/app/src/main` finds nothing); #15 plans synced Garage/History for Android and Web, no tests yet | n/a |
| Scan (paid Claude vision, 3 documents) | End to end only in External: `realScanDecrementsBalance`, `realDuplicateScanWithSameClientRequestIdSpendsOnce`, fixture-pool tests (`PaywallScreenWeeklyTest`). UI states: `ChooserScreenTest.scanErrorShowsDialog...`, `TruckTagEntryScreenTest.standaloneScanErrorShows...`, `...scanStandaloneTicketButtonOpensTheSourceChoiceDialog` (fake callbacks). `ScanApiClient`, `ScanFieldMapping`, `PhotoEncoding`: no offline test | partly device; core logic none offline |
| Paywall, credit balance, restore | `PaywallScreenTest` (7), `CreditBalanceChipTest` (5), `ChooserScreenTest` zero-credit route, `RigCheckNavHostTest` paywall routes, `RevenueCatManagerTest.invalidates...before reading the balance` (JVM, the 2026-08-18 cache bug). Offer list, purchase and spinner: External only | mixed |
| Results screen (verdicts, estimated-figures notice, nickname, start another) | `ResultsScreenTest` (8), `BreakdownRowTest` (3) | device only |
| Entry screens (truck, trailer, scale ticket), pin-weight slider | `TruckTagEntryScreenTest` (6), `TrailerTagEntryScreenTest` (2), `ScaleTicketEntryScreenTest` (2); each tests one representative field only | device only |
| Number formatting | `NumberFormattingTest` (3) | JVM |
| Optional truck GCWR field and updated breakdown (#47, open) | none; `grep -i gcwr` in `android/app/src/main` finds nothing | n/a, not built |
| Camera overlay spike (item #18, isolated) | `GuideRectMathTest` (5, JVM), `CameraOverlaySpikeExifTest` (2, device) | mixed |

## 5. Interface coverage

Our interfaces:

- Golden-vector fixture `test-vectors/breakdown_cases.json`: covered by `BreakdownGoldenVectorTest` (Kotlin side). Two other fixtures in `test-vectors/`, `breakdown_response_shape_contract.json` and `pin_weight_pct_contract.json`, are referenced only by Python and Web tests (found by grep); Android reads neither. The first is about the API response shape that Android does not consume; `pin_weight_pct_contract.json` has no Kotlin consumer (the golden vectors do include `adjustable_pin_weight_pct` cases).
- Public surface per module: `domain` (`computeBreakdown`, `verdictFor`) is covered; `data` (`RevenueCatManager` partly, `ScanApiClient`, `RecentRigsRepository`, `ScanFieldMapping`, `PhotoEncoding` none offline); the Worker request/response contract as seen from the Android side (`ScanApiClient.scan(...)`) has only the External test.
- Cross-platform "Disclaimer" and "Rig" contracts are intentionally independent per `CONTEXT-MAP.md`, so no shared test is expected.

Their interfaces:

| Third-party | Where Android calls it | Test | Watched in `scripts/external_manifest/surfaces/`? |
|---|---|---|---|
| RevenueCat Android SDK (`com.revenuecat.purchases:purchases` 10.17.0) | `RevenueCatManager.kt`, `RigCheckApplication.kt`, `PaywallScreen.kt` | JVM mock of one function (`RevenueCatManagerTest`); real calls in `PaywallScreenWeeklyTest` | no surface (#39 open). Not in any `registry_packages` |
| Google Play Billing (via RevenueCat; `com.android.billingclient:billing`, not directly pinned) | through `purchasePackage` | the Test Store purchase in `realPurchaseIncrementsBalance` goes through RevenueCat's Test Store, not Play Billing, so it does not cover this surface | no surface (#40 open) |
| RevenueCat REST (balance spend/refund, done by the Worker) | not called by Android directly | Worker-side tests; `realScanDecrementsBalance` sees it indirectly | yes, `revenuecat-rest.json`: platforms `scan-proxy`, `android`; boundary file `workers/scan-proxy/src/revenuecat.ts`; no registry packages; last pass recorded 2026-10-04 at commit 51dc229 |
| Our deployed Worker (`ScanApiClient.kt` `SCAN_ENDPOINT`) | `ScanApiClient.kt` via OkHttp 5.5.0 | External scan tests | no surface for the deployed Worker yet (ADR-0008 lists it; manifest does not) |
| Anthropic (reached only through the Worker) | none from Android | via Worker External suite | no surface file yet |
| AndroidX / Compose / CameraX / DataStore / OkHttp / kotlinx-serialization | many | JVM and instrumented suites | not watched; ADR-0008 does not call for them |

`android/test-weekly.ps1` records the result with `record_external_result.py android weekly`, the legacy key (`external_status.json` shows `android.weekly` at 2026-09-09). The gate ignores it, so Android has no per-surface pass of its own; `revenuecat-rest` was passed on 2026-10-04 by another path.

## 6. Spec check

- #47 (optional GCWR): the shared fixture and Kotlin port do not know GCWR. Kotlin still always emits a Combined Rig Weight row from GVWR plus GVWR, and `BreakdownTest.kt:123` (`combined rig weight note spells out the arithmetic`) pins the old "GVWR + GVWR" note that #47 says to remove. Expected lag, since #47 depends on a core ticket; when the fixture changes, `SUPPORTED_CAPABILITIES` in `BreakdownGoldenVectorTest.kt` silently skips any case that needs an unknown capability (the loop `continue`s; only the second test prints the skip list and its `assumeTrue("informational only", true)` can never fail). A new GCWR case could therefore be skipped without any red result. Suggest making unsupported cases visible (JUnit `assumeTrue` per case, or fail on an allow-list of skips).
- ADR-0008 / #35: surface tags ("annotation for Android") do not exist; no Android test class has one. The Android "release step" gate is not implemented in `test-weekly.ps1` (no call to `external_freshness.py`; the Worker deploy happens before tests, so a failed test run leaves a freshly deployed Worker). `test-weekly.ps1` and `build.gradle.kts` also use the retired "Daily" and "Weekly" names in comments, noted in `android/TESTING.md` as unrenamed.
- ADR-0008 says missing secrets or devices must fail the run: `test-weekly.ps1` throws when `adb` is missing, matching the intent. No skip flag exists on Android.
- #39: the test depth "no real purchase" conflicts with the current External suite, which does make a real Test Store purchase (free). The current suite exceeds the spec in that respect, and lacks the "unknown user" and "offline" error-contract tests it asks for.
- #15: the Disclaimer, Rig and scan tests match `CONTEXT.md`. Nothing tests the planned account/sync features, which do not exist on Android yet.
- `android/TESTING.md` counts lag the code (Major 57 at 2026-09-09 versus 60 offline instrumented tests counted here, and External "3 tests" in one paragraph versus 6 now). Documentation only.
- Possible overreach by tests: `PaywallScreenWeeklyTest` hosts the scan-fixture pool tests (`scanPassPoolRandomPickMatchesGoldenFields`, `scanFailPoolRandomPickReturnsNullForMissingFields`), which make real paid calls; they belong to the Worker/Anthropic surface rather than the RevenueCat SDK, so they count against a future RevenueCat SDK surface's paid-call maximum.

## 7. Rule fit

1. Scope ladder. File: possible with a Gradle filter (`./gradlew testDebugUnitTest --tests 'com.rigcheck.app.domain.BreakdownTest'`; standard Gradle, not run here; for instrumented, `-Pandroid.testInstrumentationRunnerArguments.class=<fqcn>`). Context: `./gradlew test` (JVM), `./gradlew connectedDebugAndroidTest` (device). Application level: Android is one module, so context and application coincide for Android, but there is no command that spans Android, Worker, Web and Python. No wrapper script exposes the file level.
2. Per issue. The issue's targeted test can run first via the filter above. A Minor suite can be run alone (`./gradlew test`). A Major suite can be run alone but only with a device. The "dependency changed" Major trigger cannot be detected automatically (no planner, rule 8). Inter-module interface tests: the golden-vector test is the only cross-module test; running it alone needs `--tests ...BreakdownGoldenVectorTest`.
3. Session end. JVM-only run is possible today with one command, `./gradlew test` (measured, 21 s warm). Blockers: detekt is not part of it and failed offline here (missing cached artifacts for its tool classpath; resolving them needs the network); there is no JVM coverage gate; `coverage_gate.py` is release-time and device-based; the diff-based decision to also run instrumented tests does not exist. The JDK situation worked (Studio's JBR at `G:\Android\AndroidStudio\jbr` is JDK 25, but Gradle selected the pinned JDK 21 from `G:\GradleUserHome\jdks`), though detekt's own note says the daemon JVM must be 22 or older, which the toolchain gives.
4. Release. A full run of every category is possible but split across scripts: `./gradlew connectedDebugAndroidTest` plus `.\test-weekly.ps1` (with the Worker External suite via `workers/scan-proxy/test-weekly.ps1`, and `scripts/coverage_gate.py`). Nothing runs them as one release command, and the freshness gate is not wired in. Paid steps (two Claude calls) currently run without an owner confirmation prompt, in conflict with rule 6; the script has no confirmation or call-cap counter.
5. Web gate. Not Android's; note that `.git/hooks` contains only the `*.sample` files, so the pre-push hook ADR-0008 describes is not installed in this checkout.

## 8. Incremental complexity

Ordered cheapest to most expensive for Android:

1. One JVM class: `./gradlew testDebugUnitTest --tests '<class>'`; seconds, no device, no network.
2. All JVM tests: `./gradlew test`; 21 s warm (measured), 38 tests; JDK 21 and Gradle cache only.
3. JVM plus coverage: add `createDebugUnitTestCoverageReport`; about 4 s extra warm (measured); no device. Number is 6.92%, not gated.
4. Static check: `./gradlew detekt` (two rules only: `UnusedPrivateMember`, `UnusedImports`); not runnable offline here; needs the network to fetch its tool dependencies once.
5. Freshness check for Android's chain: `uv run scripts/external_freshness.py --platform android`; reads git and the status file; today covers only `revenuecat-rest`, and reaches no registry for it (no packages listed). Needs network once Maven packages are listed.
6. Instrumented offline suite: `./gradlew connectedDebugAndroidTest`; several minutes (recorded by the repo, not measured here); needs a booted emulator or device, no network, no cost.
7. Instrumented coverage: `./gradlew createDebugCoverageReport` then `uv run scripts/coverage_gate.py`; same device; produces the gated 71.00% number.
8. External suite: `.\test-weekly.ps1`; needs device, network, wrangler deploy rights, `weekly-test-user`; about $0.02 and a Worker deploy per run.
9. Release run: steps 6 to 8 plus the Worker External suite and the freshness gate; Play Store push.

## 9. Gaps and suggested tickets

Suggestions only; no issues were created or edited.

1. Add a JVM-only session-end wrapper (one script or Gradle task running `test`, JVM coverage report and, once runnable, detekt, with a file-level `--tests` option); rule 3 and section 7; small.
2. Report JVM coverage next to the device number in the coverage tooling, with no verdict (rule 9); `coverage_gate.py` and `coverage_lib.py` only read device reports; small.
3. JVM tests for `ScanApiClient` (OkHttp `MockWebServer`: request body, headers, error mapping, idempotency `client_request_id`), `ScanFieldMapping`, `PhotoEncoding`, and `RecentRigsRepository` (including reading a Rig saved before a new field, which #47 needs); sections 3 to 5; medium.
4. JVM tests for `RigCheckViewModel` (disclaimer flag, credit refresh, scan, purchase, save-rig flows, using fakes); section 4; medium.
5. Add the `revenuecat-android-sdk` surface (#39) and `google-play-billing` surface (#40) to the manifest with boundary files (`RevenueCatManager.kt`, `RigCheckApplication.kt`), pins (`android/gradle/libs.versions.toml`, `android/app/build.gradle.kts`) and Maven packages; section 5; small each, but #40 needs a device-capable check.
6. Add a Maven fetcher to `external_freshness.py`: `_FETCHERS` has only `npm`. `com.revenuecat.purchases:purchases` is on Maven Central (its search API returns per-version timestamps). `com.android.billingclient:billing` is on Google Maven, whose `maven-metadata.xml` has no dates, so a date would have to come from the `Last-Modified` header of each version's `.pom` or from another source. Also keep the stable-only filter (`^\d+\.\d+\.\d+$`), since RevenueCat and Billing use `-beta` and `-rc` tags. Suggest also watching `com.squareup.okhttp3:okhttp` only if the Worker contract is counted as a surface; section 5; medium.
7. Add surface tags to Android External tests (a JUnit annotation or category per surface) and let `test-weekly.ps1` take the stale list, plus split the scan-fixture pool tests (Worker/Anthropic surface) from the RevenueCat ones; ADR-0008; medium.
8. Wire the Android release step to `external_freshness.py --platform android`, make `test-weekly.ps1` record per-surface results (not the legacy `android weekly` key), ask for owner confirmation before paid calls, and run the Worker deploy only after the freshness check; rules 4 and 6; medium.
9. Make golden-vector skips visible: fail or `assume` per skipped case so a new fixture capability (GCWR, #47) cannot be silently ignored; section 6; small.
10. Add the missing error-contract tests #39 asks for (unknown user, offline) and a test of the Disclaimer's per-launch reset; section 4; small to medium (device).
11. Remove or replace the two placeholder tests (`ExampleUnitTest`, `ExampleInstrumentedTest`) and refresh the counts in `android/TESTING.md`; sections 2 and 6; small.
12. Decide whether to widen detekt beyond two rules and cache its dependencies so it runs offline; section 7; small.
13. A planner script (rule 8) that maps a git diff in `android/` to: JVM suite always, instrumented suite when `ui/` or `data/` changed, External when `RevenueCatManager.kt` or pins changed; rule 8; medium.

Environment notes for the owner: `JAVA_HOME` is `G:\Android\AndroidStudio\jbr` (JDK 25), `ANDROID_SDK_ROOT` is `G:\Android\Sdk`, `GRADLE_USER_HOME` is `G:\GradleUserHome`; `android/local.properties` does not exist (the SDK path comes from the environment variable, which the build script falls back to). Running Gradle here rewrote the git-ignored `android/app/build` and `android/build` outputs and updated `G:\GradleUserHome` (its existing cache and daemon files); nothing tracked by git was changed apart from this report.
