<#
.SYNOPSIS
    Runs the Worker's full release set in one command (#62): the offline
    suite, the stale surface suites, the direct-provider release suite and
    the through-the-Worker weekly suite (which redeploys the Worker).

.DESCRIPTION
    A thin shell: the step order, the paid-call confirmation prompts, the
    shared paid-call budget and the abort-on-exceeded behaviour all live in
    scripts/scan_proxy_release.py and are unit-tested there with a fake
    runner. The release suite and weekly suite each need the owner to
    confirm before they run (both are paid); confirming beyond the declared
    maximum aborts the run instead of spending further.

.PARAMETER MaxPaidCalls
    Declared ceiling for paid calls this run may confirm (default: 3 -
    the release suite's 1 plus the weekly suite's 2).

.EXAMPLE
    .\release.ps1
.EXAMPLE
    .\release.ps1 -MaxPaidCalls 5
#>
param(
    [int]$MaxPaidCalls
)

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$extraArgs = if ($PSBoundParameters.ContainsKey('MaxPaidCalls')) { @('--max-paid-calls', $MaxPaidCalls) } else { @() }

& uv run --project $repoRoot (Join-Path $repoRoot 'scripts\scan_proxy_release.py') @extraArgs
exit $LASTEXITCODE
