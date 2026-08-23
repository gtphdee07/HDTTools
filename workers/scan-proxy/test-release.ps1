<#
.SYNOPSIS
    Runs the scan-proxy Release tier (real RevenueCat/Anthropic API calls).

.DESCRIPTION
    Default behavior is strict: if ANTHROPIC_API_KEY or REVENUECAT_SECRET_KEY
    isn't set in this shell's environment, the underlying test file stops
    before running any test (a reported failure, not a silent skip) - see
    src/release/scan.release.test.ts for that enforcement, which applies
    regardless of whether this wrapper is used.

    -SkipKeys grants explicit permission to skip instead: missing keys fall
    back to a per-boundary skip (RevenueCat and Anthropic skip
    independently), so you can still verify whichever boundary you do have
    a key for.

.PARAMETER SkipKeys
    Allow missing ANTHROPIC_API_KEY/REVENUECAT_SECRET_KEY to skip their
    tests instead of stopping the whole run.

.EXAMPLE
    .\test-release.ps1
    Runs the full Release tier - stops immediately if either key is missing.

.EXAMPLE
    .\test-release.ps1 -SkipKeys
    Runs whatever the currently-set keys allow, skipping the rest.
#>
param(
    [switch]$SkipKeys
)

if ($SkipKeys) {
    $env:SKIP_KEYS = '1'
} else {
    Remove-Item Env:\SKIP_KEYS -ErrorAction SilentlyContinue
}

npm run test:release
exit $LASTEXITCODE
