<#
.SYNOPSIS
    Runs the Python/core External suite for only the stale surfaces, then
    records the result per surface (ADR-0008).

.DESCRIPTION
    A thin shell: the decisions (which surfaces are stale, nothing to run
    when fresh, untagged-surface guard, -Skip, paid-call budget, pass/fail
    recording) live in scripts/external_wrapper.py and are unit-tested
    there. The tests run via scripts/run_external_pytest.py, narrowed to
    the stale surfaces' pytest markers.

    Needs ANTHROPIC_API_KEY in this shell's environment for the "anthropic"
    surface; a missing key fails the run. -Skip records `skipped` for the
    stale surfaces instead of running them; a skip never advances
    freshness, so they stay stale. "anthropic" is paid and asks for
    confirmation before it runs; -MaxPaidCalls sets an independent ceiling
    instead of trusting the sum of the stale paid surfaces' own declared
    costs.

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

$repoRoot = $PSScriptRoot
$skipArg = if ($Skip) { @('--skip') } else { @() }
$maxPaidCallsArg = if ($PSBoundParameters.ContainsKey('MaxPaidCalls')) { @('--max-paid-calls', $MaxPaidCalls) } else { @() }

& uv run --project $repoRoot (Join-Path $repoRoot 'scripts\external_wrapper.py') `
    --platform core --tests-dir (Join-Path $repoRoot 'tests') --cwd $repoRoot `
    --test-glob 'test_*_external.py' --tag-style marker @skipArg @maxPaidCallsArg `
    -- uv run python (Join-Path $repoRoot 'scripts\run_external_pytest.py')
exit $LASTEXITCODE
