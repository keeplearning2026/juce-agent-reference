#!/usr/bin/env bash
# Bootstrap script for JUCE Agent Reference Generator
set -euo pipefail

JUCE_ROOT="${JUCE_ROOT:-D:/project/JUCE}"

echo "=== JUCE Reference Generator Bootstrap ==="

# Check Python
if command -v python &>/dev/null; then
    echo "[OK] Python: $(python --version 2>&1)"
else
    echo "[FAIL] Python 3.12+ is required"
    exit 3
fi

# Check Git
if command -v git &>/dev/null; then
    echo "[OK] Git: $(git --version 2>&1)"
else
    echo "[FAIL] Git is required"
    exit 3
fi

# Check Doxygen
if command -v doxygen &>/dev/null; then
    echo "[OK] Doxygen: $(doxygen --version 2>&1)"
else
    echo "[FAIL] Doxygen is required"
    exit 3
fi

# Create virtual environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$REPO_ROOT/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python -m venv "$VENV_DIR"
fi

# Activate and install
source "$VENV_DIR/Scripts/activate" 2>/dev/null || source "$VENV_DIR/bin/activate"
python -m pip install -e ".[dev]"

# Verify installation
python -m juce_reference doctor --juce-root "$JUCE_ROOT"
echo "[OK] Bootstrap complete."
