<#
.SYNOPSIS
    Runs the Android release set in one command (#63): the JVM suite, the
    instrumented suite on an attached device, the stale surfaces in
    Android's chain (including the Worker's) and the old weekly suite
    (which redeploys the Worker and makes real Claude calls).

.DESCRIPTION
    A thin shell: the step order, the missing-device failure, the paid-call
    confirmation prompt and the shared paid-call budget all live in
    scripts/android_release.py and are unit-tested there with a fake
    runner and a fake device list. A missing device/emulator fails the run
    outright - it is never silently skipped. The old weekly suite needs the
    owner to confirm (it both deploys the Worker and spends); confirming
    beyond the declared maximum aborts the run instead of spending further.

.PARAMETER MaxPaidCalls
    Declared ceiling for paid calls this run may confirm (default: 2 -
    the old weekly suite's cost).

.EXAMPLE
    .\release.ps1
.EXAMPLE
    .\release.ps1 -MaxPaidCalls 4
#>
param(
    [int]$MaxPaidCalls
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$extraArgs = if ($PSBoundParameters.ContainsKey('MaxPaidCalls')) { @('--max-paid-calls', $MaxPaidCalls) } else { @() }

& uv run --project $repoRoot (Join-Path $repoRoot 'scripts\android_release.py') @extraArgs
exit $LASTEXITCODE
