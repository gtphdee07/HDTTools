<#
.SYNOPSIS
    Runs Android's External suite for only the stale surfaces it owns, then
    records the result per surface (ADR-0008).

.DESCRIPTION
    A thin shell: the decisions (which surfaces are stale, nothing to run
    when fresh, untagged-surface guard, -Skip, pass/fail recording) live in
    scripts/external_wrapper.py and are unit-tested there. The tests run
    through scripts/run_external_android.py, which builds and installs the
    debug and androidTest APKs, runs the classes tagged
    @ExternalSurface("<surface>") with `am instrument`, and writes the
    per-test JUnit XML the wrapper reads. This is the first Android runner
    (#39); #40's Google Play Billing tests join it by adding a tagged
    *ExternalTest.kt class next to RevenueCatAndroidSdkExternalTest.kt.

    REQUIRES a device: exactly one attached device or emulator with Google
    Play Services (the medium_phone AVD qualifies), and no other Android
    ticket using it. Start it with
        emulator -avd medium_phone -no-snapshot-save -gpu swangle_indirect
    and wait for it to boot. No device, no Play Services, or a funded
    Supabase test account that cannot sign in (WEB_EXTERNAL_TEST_EMAIL /
    WEB_EXTERNAL_TEST_PASSWORD, VITE_SUPABASE_URL,
    VITE_SUPABASE_PUBLISHABLE_KEY, from the environment or web/.env.local)
    FAILS the run and records the stale surfaces failed; it is never
    silently skipped. -Skip records `skipped` for the stale surfaces
    instead of running them; a skip never advances freshness, so they stay
    stale.

    Only the surfaces this platform owns run here. A stale surface in
    Android's chain that another platform owns (the Worker's, Supabase
    Auth) is reported with the script that runs it. The old weekly suite
    (test-weekly.ps1) is separate and unchanged.

    Nothing here is paid: the surfaces make no purchase and spend no scan.

.EXAMPLE
    .\test-external.ps1
.EXAMPLE
    .\test-external.ps1 -Skip
#>
param(
    [switch]$Skip
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$skipArg = if ($Skip) { @('--skip') } else { @() }
# --tests-dir and --test-glob are the same two values as TESTS_DIR and TEST_GLOB in
# scripts/run_external_android.py (a test keeps them equal); the glob is not recursive.
$testsDir = Join-Path $PSScriptRoot 'app\src\androidTest\java\com\rigcheck\app'

& uv run --project $repoRoot (Join-Path $repoRoot 'scripts\external_wrapper.py') `
    --platform android --tests-dir $testsDir --test-glob '*ExternalTest.kt' --tag-style annotation `
    --cwd $repoRoot @skipArg `
    -- uv run python (Join-Path $repoRoot 'scripts\run_external_android.py')
exit $LASTEXITCODE
