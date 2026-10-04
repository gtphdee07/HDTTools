<#
.SYNOPSIS
    Runs scan-proxy's External suite for only the stale surfaces, then
    records the result per surface (ADR-0008).

.DESCRIPTION
    A thin shell: the decisions (which surfaces are stale, nothing to run
    when fresh, untagged-surface guard, -Skip, pass/fail recording) live in
    scripts/external_wrapper.py and are unit-tested there. The tests run via
    `npm run test:external`, narrowed to the stale surfaces' "[surface]" tags.

    Needs REVENUECAT_SECRET_KEY in this shell's environment; a missing key
    fails the run. -Skip records `skipped` for the stale surfaces instead of
    running them; a skip never advances freshness, so they stay stale.

.EXAMPLE
    .\test-external.ps1
.EXAMPLE
    .\test-external.ps1 -Skip
#>
param(
    [switch]$Skip
)

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$skipArg = if ($Skip) { @('--skip') } else { @() }

& uv run --project $repoRoot (Join-Path $repoRoot 'scripts\external_wrapper.py') `
    --platform scan-proxy --tests-dir (Join-Path $PSScriptRoot 'src\external') --cwd $PSScriptRoot @skipArg `
    -- npm run test:external
exit $LASTEXITCODE
