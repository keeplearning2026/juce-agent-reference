# Goal check script — validates that V1 completion criteria are met.
param(
    [string]$JuceRoot = "D:\project\JUCE",
    [string]$Output = "D:\project\juce-reference"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent

Write-Host "=== JUCE Reference V1 Goal Check ==="

# 1. Run unified verification
Write-Host ""
Write-Host "--- Running juce-doc all ---"
$allResult = python -m juce_reference all --juce-root $JuceRoot --output $Output 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] juce-doc all returned exit code $LASTEXITCODE"
    Write-Host $allResult
    exit $LASTEXITCODE
}
Write-Host "[OK] juce-doc all passed"

# 2. Git cleanliness
Write-Host ""
Write-Host "--- Checking Git cleanliness ---"
Push-Location $RepoRoot
$status = git status --porcelain 2>&1
if ($status) {
    Write-Host "[FAIL] Git working tree is not clean:"
    Write-Host $status
    Pop-Location
    exit 15
}
Write-Host "[OK] Git working tree clean"
Pop-Location

# 3. Blocker absence
Write-Host ""
Write-Host "--- Checking blocker absence ---"
$blockerPath = Join-Path $RepoRoot ".agent" "blocker.json"
if (Test-Path $blockerPath) {
    Write-Host "[FAIL] Blocker file exists at $blockerPath"
    exit 20
}
Write-Host "[OK] No blocker file"

# 4. Progress completion
Write-Host ""
Write-Host "--- Checking progress completion ---"
$progressPath = Join-Path $RepoRoot ".agent" "progress.json"
$progress = Get-Content $progressPath | ConvertFrom-Json
if (-not $progress.completed) {
    Write-Host "[FAIL] progress.json not marked completed"
    exit 1
}
Write-Host "[OK] progress.completed = true"

Write-Host ""
Write-Host "=== Goal check PASSED ==="
exit 0
