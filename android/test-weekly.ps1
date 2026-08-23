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

& .\gradlew.bat assembleDebug assembleDebugAndroidTest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $adb install -r app\build\outputs\apk\debug\app-debug.apk
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $adb install -r app\build\outputs\apk\androidTest\debug\app-debug-androidTest.apk
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$markerPath = '/data/local/tmp/rigcheck_weekly_mode'
& $adb shell touch $markerPath
try {
    & $adb shell am instrument -w `
        -e class com.rigcheck.app.ui.screens.PaywallScreenWeeklyTest `
        com.rigcheck.app.test/com.rigcheck.app.CustomTestRunner
    $testExitCode = $LASTEXITCODE
} finally {
    & $adb shell rm -f $markerPath
}
exit $testExitCode
