<#
.SYNOPSIS
    Runs the scan-proxy Weekly (through-our-service) External suite and
    records the result for the README dashboard.

.DESCRIPTION
    Thin wrapper around `npm run test:weekly` (real, bounded calls
    against the deployed Worker using the dedicated weekly-test-user /
    weekly-test-user-no-credits RevenueCat test customers - see
    workers/scan-proxy/TESTING.md). New 2026-08-24 (roadmap item #7):
    before this wrapper existed, this suite only ever ran via bare `npm
    run test:weekly`, which had no hook to record a real result anywhere
    - scripts/generate_dashboard.py's External column needs a real
    last-known result to show without re-running real network calls on
    every dashboard regen, so this wrapper adds exactly that, mirroring
    test-release.ps1's shape.

.EXAMPLE
    .\test-weekly.ps1
#>

npm run test:weekly
$testExitCode = $LASTEXITCODE

& uv run --project ..\.. ..\..\scripts\record_external_result.py scan_proxy weekly $testExitCode

exit $testExitCode
