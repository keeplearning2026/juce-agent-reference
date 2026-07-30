#!/usr/bin/env bash
# Goal check script — validates that V1 completion criteria are met.
set -euo pipefail

JUCE_ROOT="${JUCE_ROOT:-D:/project/JUCE}"
OUTPUT="${OUTPUT:-D:/project/juce-reference}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== JUCE Reference V1 Goal Check ==="

# 1. Run unified verification
echo ""
echo "--- Running juce-doc all ---"
python -m juce_reference all --juce-root "$JUCE_ROOT" --output "$OUTPUT"
echo "[OK] juce-doc all passed"

# 2. Git cleanliness
echo ""
echo "--- Checking Git cleanliness ---"
if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]; then
    echo "[FAIL] Git working tree is not clean:"
    git -C "$REPO_ROOT" status --porcelain
    exit 15
fi
echo "[OK] Git working tree clean"

# 3. Blocker absence
echo ""
echo "--- Checking blocker absence ---"
if [ -f "$REPO_ROOT/.agent/blocker.json" ]; then
    echo "[FAIL] Blocker file exists"
    exit 20
fi
echo "[OK] No blocker file"

# 4. Progress completion
echo ""
echo "--- Checking progress completion ---"
COMPLETED=$(python -c "import json; print(json.load(open('$REPO_ROOT/.agent/progress.json'))['completed'])")
if [ "$COMPLETED" != "True" ]; then
    echo "[FAIL] progress.json not marked completed"
    exit 1
fi
echo "[OK] progress.completed = true"

echo ""
echo "=== Goal check PASSED ==="
exit 0
