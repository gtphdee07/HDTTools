<#
.SYNOPSIS
    Runs Web's External suite for only the stale surfaces, then records the
    result per surface (ADR-0008).

.DESCRIPTION
    Asks scripts/external_freshness.py which surfaces in Web's dependency
    chain are stale. Fresh surfaces are not exercised. Stale ones run via
    `npm run test:external`, narrowed to their "[surface]" test-name tag, and
    each is recorded pass or fail through scripts/record_external_result.py
    along with the registry versions seen.

    -Skip records `skipped` for the stale surfaces instead of running them.
    A skip never advances freshness, so they stay stale.

    A missing credential in web/.env.local fails the run (and is recorded as
    a fail); it is never silently skipped.

.EXAMPLE
    .\test-external.ps1
.EXAMPLE
    .\test-external.ps1 -Skip
#>
param(
    [switch]$Skip
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

# Exit code 1 only means "something is stale"; the verdict is in the JSON.
$freshnessJson = & uv run --project $repoRoot (Join-Path $repoRoot 'scripts\external_freshness.py') --json --platform web
if ($LASTEXITCODE -gt 1) { throw "external_freshness.py failed (exit $LASTEXITCODE)" }
$verdict = ($freshnessJson -join "`n") | ConvertFrom-Json
$stale = @($verdict.stale)

foreach ($name in $verdict.surfaces.PSObject.Properties.Name) {
    $s = $verdict.surfaces.$name
    $reasons = if ($s.reasons.Count -gt 0) { ': ' + ($s.reasons -join '; ') } else { '' }
    Write-Output "$name - $($s.state)$reasons"
}

if ($stale.Count -eq 0) {
    Write-Output 'No stale Web surfaces; nothing to run.'
    exit 0
}

function Record([string]$surface, [string]$outcome) {
    $versions = ($verdict.surfaces.$surface.versions | ConvertTo-Json -Compress)
    if (-not $versions -or $versions -eq 'null') { $versions = '{}' }
    & uv run --project $repoRoot (Join-Path $repoRoot 'scripts\record_external_result.py') `
        --surface $surface --outcome $outcome --versions ($versions -replace '"', '\"')
    if ($LASTEXITCODE -ne 0) { throw "Recording $surface failed (exit $LASTEXITCODE)" }
}

if ($Skip) {
    foreach ($surface in $stale) { Record $surface 'skipped' }
    Write-Output "Recorded skipped for: $($stale -join ', '). They remain stale."
    exit 0
}

$env:EXTERNAL_SURFACES = $stale -join ','
Push-Location $PSScriptRoot
try {
    & npm run test:external
    $testExitCode = $LASTEXITCODE
} finally {
    Pop-Location
    Remove-Item Env:\EXTERNAL_SURFACES -ErrorAction SilentlyContinue
}

$outcome = if ($testExitCode -eq 0) { 'pass' } else { 'fail' }
foreach ($surface in $stale) { Record $surface $outcome }
exit $testExitCode
