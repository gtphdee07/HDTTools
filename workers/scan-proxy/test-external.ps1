<#
.SYNOPSIS
    Runs scan-proxy's External suite for only the stale surfaces, then
    records the result per surface (ADR-0008).

.DESCRIPTION
    A thin shell: the decisions (which surfaces are stale, nothing to run
    when fresh, untagged-surface guard, -Skip, pass/fail recording) live in
    scripts/external_wrapper.py and are unit-tested there. The tests run via
    `npm run test:external`, narrowed to the stale surfaces' "[surface]" tags.

    Needs REVENUECAT_SECRET_KEY/ANTHROPIC_API_KEY in this shell's
    environment for whichever surfaces are stale; a missing key fails the
    run. -Skip records `skipped` for the stale surfaces instead of running
    them; a skip never advances freshness, so they stay stale. A paid
    surface (anthropic) asks for confirmation before it runs; -MaxPaidCalls
    sets an independent ceiling instead of trusting the sum of the stale
    paid surfaces' own declared costs.

.PARAMETER MaxPaidCalls
    Independent ceiling for paid calls this run may confirm (default: the
    sum of the stale paid surfaces' own manifest max_paid_calls).

.EXAMPLE
    .\test-external.ps1
.EXAMPLE
    .\test-external.ps1 -Skip
.EXAMPLE
    .\test-external.ps1 -MaxPaidCalls 3
#>
param(
    [switch]$Skip,
    [int]$MaxPaidCalls
)

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$skipArg = if ($Skip) { @('--skip') } else { @() }
$maxPaidCallsArg = if ($PSBoundParameters.ContainsKey('MaxPaidCalls')) { @('--max-paid-calls', $MaxPaidCalls) } else { @() }

& uv run --project $repoRoot (Join-Path $repoRoot 'scripts\external_wrapper.py') `
    --platform scan-proxy --tests-dir (Join-Path $PSScriptRoot 'src\external') --cwd $PSScriptRoot @skipArg @maxPaidCallsArg `
    -- npm run test:external
exit $LASTEXITCODE
