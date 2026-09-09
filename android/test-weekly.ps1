<#
.SYNOPSIS
    Runs the Android Weekly-equivalent tier (real RevenueCat Test Store,
    a real purchase, a real scan against the deployed Worker).

.DESCRIPTION
    Unlike the Daily tier (./gradlew connectedDebugAndroidTest), this tier
    touches a device-side marker file before running, which
    CustomTestRunner checks to substitute WeeklyTestApplication (real
    Purchases.configure() against the dedicated weekly-test-user Test
    Store customer) instead of the Daily tier's plain, offline
    Application - see android/TESTING.md and CustomTestRunner.kt's own
    comment for the two mechanisms tried first that didn't work (a second
    named instrumentation runner - AGP's manifest merger only allows one
    <instrumentation> element per test APK; and -e weekly true - fired too
    late, newApplication() runs before instrumentation args are readable
    in this environment). Both confirmed hands-on 2026-08-23.

    First redeploys workers/scan-proxy (typecheck, then `wrangler
    deploy`) so the Worker these instrumented tests hit against is
    guaranteed to match what's on disk right now, not whatever was last
    manually deployed - found the hard way 2026-08-23, when a real
    hands-on verification against the Android app genuinely failed
    because the deployed Worker was stale (see NEXT_STEPS.md /
    ARCHIVE_MONETIZATION.md item #5). Also wakes the emulator screen
    before running - an idle/sleeping screen makes instrumented Compose
    tests fail with a misleading "No compose hierarchies found" error
    (see ARCHIVE_TESTING.md), a flakiness source that's bitten this tier
    before.

    Builds the debug + androidTest APKs, installs both on the attached
    device/emulator, sets the marker, runs PaywallScreenWeeklyTest, then
    clears the marker so a later Daily-tier run is unaffected either way.

    Identity is hardcoded (weekly-test-user), not an env secret, so
    unlike test-release.ps1 there's no key-based skip logic here - this
    either runs for real or you don't run it.

.EXAMPLE
    .\test-weekly.ps1
    Builds, installs, and runs the full Weekly tier against the
    attached device/emulator.
#>

$ErrorActionPreference = 'Stop'

# Resolves adb explicitly rather than assuming it's on PATH - it often
# isn't in a plain shell even when Android Studio/the emulator work fine
# (Studio launches tools via its own configured SDK path, not PATH).
$adbCmd = Get-Command adb -ErrorAction SilentlyContinue
if ($adbCmd) {
    $adb = $adbCmd.Source
} elseif ($env:ANDROID_SDK_ROOT) {
    $adb = Join-Path $env:ANDROID_SDK_ROOT 'platform-tools\adb.exe'
} elseif ($env:ANDROID_HOME) {
    $adb = Join-Path $env:ANDROID_HOME 'platform-tools\adb.exe'
} else {
    throw 'adb not found on PATH and neither ANDROID_SDK_ROOT nor ANDROID_HOME is set.'
}
if (-not (Test-Path $adb)) { throw "adb not found at resolved path: $adb" }

# Redeploy the Worker first, every time - these tests hit the real deployed
# URL (ScanApiClient.kt's SCAN_ENDPOINT), so if this step is skipped a
# stale deploy passes silently while actually testing yesterday's code.
# --prefix runs npm against workers/scan-proxy's own package.json without
# needing to cd there and back. Typecheck runs first so a real syntax/type
# error stops this before anything gets deployed, not after.
& npm run typecheck --prefix ..\workers\scan-proxy
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& npm run deploy --prefix ..\workers\scan-proxy
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# An idle/sleeping emulator screen makes instrumented Compose tests fail
# with a misleading "No compose hierarchies found in the app" error
# instead of a clear one - see ARCHIVE_TESTING.md. Wake it and keep it
# awake for the duration of this run.
& $adb shell input keyevent KEYCODE_WAKEUP
& $adb shell svc power stayon true

& .\gradlew.bat assembleDebug assembleDebugAndroidTest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $adb install -r app\build\outputs\apk\debug\app-debug.apk
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $adb install -r app\build\outputs\apk\androidTest\debug\app-debug-androidTest.apk
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$markerPath = '/data/local/tmp/rigcheck_weekly_mode'
# App-private storage (needs `run-as`, not a plain `adb pull`) rather than
# /sdcard or the app's own external-files dir - both of the latter were
# tried first and confirmed hands-on 2026-09-09 to silently fail under
# this app's scoped-storage config (am instrument prints "Generated code
# coverage data to <path>" - and even a contradictory "Error: Failed to
# generate Emma/JaCoCo coverage." - either way, no file actually lands
# there). /data/data/<pkg>/ is the instrumentation process's own sandbox,
# so it can always write there with no extra permission.
$coverageDevicePath = "/data/data/com.rigcheck.app/coverage-external.ec"
$coverageLocalPath = "app\build\outputs\code_coverage\debugAndroidTest\external\coverage-external.ec"
& $adb shell touch $markerPath
try {
    # Real bug, found and fixed 2026-09-08 (NEXT_STEPS.md item #19):
    # `adb shell am instrument`'s own exit code does NOT reflect an
    # internal JUnit failure - confirmed empirically with a deliberately-
    # failing scratch test that printed "FAILURES!!!" but still exited 0.
    # $LASTEXITCODE only catches a harness-level failure (e.g. a missing/
    # uninstalled test package - INSTRUMENTATION_FAILED, confirmed
    # separately to exit non-zero). The real pass/fail signal is in the
    # printed summary text itself ("OK (N tests)" vs "FAILURES!!!"), so
    # this is captured via Tee-Object (still prints live to the console,
    # exactly as before) and checked directly instead of trusting
    # $LASTEXITCODE alone.
    & $adb shell am instrument -w `
        -e coverage true -e coverageFile $coverageDevicePath `
        -e class com.rigcheck.app.ui.screens.PaywallScreenWeeklyTest `
        com.rigcheck.app.test/com.rigcheck.app.CustomTestRunner | Tee-Object -Variable instrumentOutput
    $harnessExitCode = $LASTEXITCODE
    $outputText = $instrumentOutput -join "`n"
    $testsFailed = ($outputText -notmatch 'OK \(\d+ tests?\)') -or ($outputText -match 'FAILURES!!!')
    $testExitCode = if ($harnessExitCode -ne 0) { $harnessExitCode } elseif ($testsFailed) { 1 } else { 0 }

    # Pull the coverage file the run just wrote, for
    # jacocoMergedCoverageReport (ClaudePlans/2026-09-09-merge-external-
    # tier-coverage-paywallscreen.md) to merge with Major's own coverage.ec
    # later. Only if the harness actually ran (a harness-level failure -
    # e.g. INSTRUMENTATION_FAILED - means no file was ever written) and
    # only best-effort (a genuine JUnit test failure inside the run
    # shouldn't also fail this whole script over a coverage file it may or
    # may not have finished writing).
    if ($harnessExitCode -eq 0) {
        New-Item -ItemType Directory -Force -Path (Split-Path $coverageLocalPath) | Out-Null
        # Plain `adb pull` fails with "Permission denied" against
        # /data/data/<pkg>/ (confirmed hands-on 2026-09-09) - it isn't
        # world-readable, so this goes through `run-as` instead, which
        # runs as the app's own UID. `adb exec-out` (not a piped `adb
        # shell`) avoids stdout newline translation corrupting the binary
        # .ec content - and even `exec-out`'s own output has to be
        # redirected through `cmd /c ... >`, not PowerShell's native `>`/
        # `Set-Content`: confirmed hands-on 2026-09-09 that PowerShell's
        # redirection silently corrupts binary stdout (a spurious UTF-8
        # BOM prepended, non-UTF8 bytes replaced with U+FFFD - a 7,708-byte
        # real .ec file came back as 8,588 bytes and failed to parse),
        # while cmd.exe's redirection is a raw byte-for-byte OS-level pipe
        # and round-tripped the same file's exact byte count and JaCoCo
        # header correctly.
        cmd /c "`"$adb`" exec-out run-as com.rigcheck.app cat $coverageDevicePath > `"$coverageLocalPath`""
        if ((Test-Path $coverageLocalPath) -and (Get-Item $coverageLocalPath).Length -gt 0) {
            Write-Output "Pulled External-tier coverage data to $coverageLocalPath"
        } else {
            Write-Warning "Could not pull $coverageDevicePath - jacocoMergedCoverageReport will fall back to Major-only coverage."
        }
    }
} finally {
    & $adb shell run-as com.rigcheck.app rm -f $coverageDevicePath
    & $adb shell rm -f $markerPath
}

# Records this real run's result for the README dashboard (roadmap item
# #7) - so generating the dashboard graphic never has to re-run this
# suite just to know its status; see scripts/record_external_result.py.
& uv run --project .. ..\scripts\record_external_result.py android weekly $testExitCode

exit $testExitCode
