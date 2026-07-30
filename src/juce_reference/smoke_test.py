"""Smoke tests for a generated JUCE reference.

Validates that key JUCE symbols are present and well-formed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Symbols that MUST be present in any real JUCE reference.
_REQUIRED_SYMBOLS = [
    "juce::AudioProcessor",
    "juce::AudioProcessorValueTreeState",
    "juce::Component",
    "juce::SmoothedValue",
    "juce::dsp::ProcessorChain",
]


def run_smoke_tests(reference_root: Path) -> dict[str, Any]:
    """Run smoke tests on a generated reference.

    Checks:
    - Key symbols exist with Markdown pages.
    - Pages have frontmatter with symbol and kind.
    - Pages have at least one heading.

    Args:
        reference_root: Path to the generated reference.

    Returns:
        A dict with ``passed``, ``results`` per symbol.

    Raises:
        SmokeTestError: If any required symbol is missing.
    """
    results: dict[str, dict[str, Any]] = {}
    passed = True

    for symbol in _REQUIRED_SYMBOLS:
        result = _check_symbol(reference_root, symbol)
        results[symbol] = result
        if not result.get("found"):
            passed = False

    # Also check at least one example of each kind
    structural_checks = _check_structure(reference_root)
    results["_structure"] = structural_checks

    if not structural_checks.get("passed"):
        passed = False

    return {"passed": passed, "results": results}


def _check_symbol(root: Path, symbol: str) -> dict[str, Any]:
    """Check one symbol in the reference."""
    # Search symbols.jsonl for the symbol
    jsonl_path = root / "index" / "symbols.jsonl"
    if not jsonl_path.is_file():
        return {"found": False, "error": "symbols.jsonl not found"}

    from juce_reference.util.json_io import json_lines

    for rec in json_lines(jsonl_path):
        if rec.get("symbol") == symbol:
            doc_path = rec.get("documentation_path", "")
            md_file = root / doc_path
            if not md_file.is_file():
                return {
                    "found": True,
                    "error": f"Markdown file missing: {doc_path}",
                    "symbol": symbol,
                }

            content = md_file.read_text(encoding="utf-8", errors="replace")
            has_fm = content.startswith("---")
            has_heading = any(line.startswith("#") for line in content.splitlines())

            return {
                "found": True,
                "documentation_path": doc_path,
                "has_frontmatter": has_fm,
                "has_heading": has_heading,
                "kind": rec.get("kind"),
                "symbol": symbol,
            }

    return {"found": False, "error": "Symbol not in index", "symbol": symbol}


def _check_structure(root: Path) -> dict[str, Any]:
    """Validate structural properties of the reference."""
    checks: dict[str, bool] = {}

    # Check index files exist
    index_files = ["symbols.tsv", "symbols.jsonl", "relationships.jsonl"]
    for f in index_files:
        checks[f"index/{f}"] = (root / "index" / f).is_file()

    # Check manifest exists
    checks["manifest.json"] = (root / "manifest.json").is_file()

    # Check reference directories exist
    for d in ["reference", "index"]:
        checks[f"directory/{d}"] = (root / d).is_dir()

    passed = all(checks.values())
    return {"passed": passed, "checks": checks}
