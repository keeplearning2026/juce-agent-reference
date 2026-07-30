# Bootstrap script for JUCE Agent Reference Generator
# Checks environment and installs dependencies.
param(
    [string]$JuceRoot = "D:\project\JUCE"
)

$ErrorActionPreference = "Stop"

Write-Host "=== JUCE Reference Generator Bootstrap ==="

# Check Python
try {
    $pyVer = python --version 2>&1
    Write-Host "[OK] Python: $pyVer"
} catch {
    Write-Error "Python 3.12+ is required"
    exit 3
}

# Check Git
try {
    $gitVer = git --version 2>&1
    Write-Host "[OK] Git: $gitVer"
} catch {
    Write-Error "Git is required"
    exit 3
}

# Check Doxygen
try {
    $doxVer = doxygen --version 2>&1
    Write-Host "[OK] Doxygen: $doxVer"
} catch {
    Write-Error "Doxygen is required"
    exit 3
}

# Create virtual environment
$venvPath = Join-Path $PSScriptRoot ".." ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..."
    python -m venv $venvPath
}

# Activate and install
$activateScript = Join-Path $venvPath "Scripts" "Activate.ps1"
. $activateScript
python -m pip install -e ".[dev]" 2>&1

# Verify installation
python -m juce_reference doctor --juce-root $JuceRoot
Write-Host "[OK] Bootstrap complete."
