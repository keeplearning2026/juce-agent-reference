"""Scan JUCE examples directory for official examples and their symbol usage.

Deterministic V1 approach: only flags fully qualified ``juce::`` symbols,
explicit inheritance, and known namespace chains. Does NOT guess from
plain short names.
"""

from __future__ import annotations

import json as _json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExampleInfo:
    """Metadata for one JUCE example."""

    name: str
    category: str
    directory: str
    files: tuple[str, ...]


@dataclass(frozen=True)
class ExampleSymbolUse:
    """A symbol usage found in an example file."""

    example_name: str
    category: str
    file: str
    line: int
    symbol: str
    confidence: str  # "qualified-text", "qualified-inheritance", "qualified-template"


_CATEGORY_MAP = {
    "Plugins": "plugins",
    "Audio": "audio",
    "DSP": "dsp",
    "GUI": "gui",
    "MIDI": "midi",
    "Utilities": "utilities",
    "Assets": "other",
    "CMake": "other",
}

_SCAN_EXTENSIONS = frozenset({
    ".h", ".hpp", ".cpp", ".cc", ".cxx", ".mm", ".m", ".inl",
    ".txt",  # CMakeLists.txt
    ".jucer",
    ".md",
})

# Regex for fully qualified juce symbols
_JUCESYM_RE = re.compile(r"\b(juce::\w+(?:::\w+)*)")
# Regex for inheritance: class X : public juce::Y
_INHERIT_RE = re.compile(r"(?:class|struct)\s+\w+\s*:.*?\b(juce::\w+(?:::\w+)*)")


def scan_examples(examples_root: Path) -> list[ExampleInfo]:
    """Discover all official JUCE examples.

    Args:
        examples_root: Path to ``JUCE/examples``.

    Returns:
        List of ``ExampleInfo`` sorted by category then name.
    """
    if not examples_root.is_dir():
        return []

    examples: list[ExampleInfo] = []

    for cat_dir in sorted(examples_root.iterdir()):
        if not cat_dir.is_dir():
            continue
        cat_name = cat_dir.name
        category = _CATEGORY_MAP.get(cat_name, "other")

        for ex_dir in sorted(cat_dir.iterdir()):
            if not ex_dir.is_dir():
                continue
            ex_name = ex_dir.name
            files = _collect_files_recursive(ex_dir, examples_root)
            if files:
                examples.append(ExampleInfo(
                    name=ex_name,
                    category=category,
                    directory=str(ex_dir.relative_to(examples_root)),
                    files=tuple(sorted(files)),
                ))

    examples.sort(key=lambda e: (e.category, e.name))
    return examples


def find_example_symbols(
    examples: list[ExampleInfo],
    examples_root: Path,
    known_symbols: frozenset[str],
) -> list[ExampleSymbolUse]:
    """Scan example source files for deterministic symbol references.

    Only matches:
    1. Fully qualified ``juce::Foo::Bar`` text.
    2. Explicit inheritance of ``juce::`` types.

    Args:
        examples: Discovered examples.
        examples_root: Root of examples directory.
        known_symbols: Set of known qualified symbol names.

    Returns:
        List of ``ExampleSymbolUse`` sorted by example then symbol.
    """
    uses: list[ExampleSymbolUse] = []

    for ex in examples:
        for fname in ex.files:
            fpath = examples_root / fname
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            lines = content.splitlines()

            for i, line in enumerate(lines, start=1):
                found_on_line: set[str] = set()

                # Qualified text match
                for m in _JUCESYM_RE.finditer(line):
                    sym = m.group(1)
                    if sym in known_symbols and sym not in found_on_line:
                        found_on_line.add(sym)
                        uses.append(ExampleSymbolUse(
                            example_name=ex.name,
                            category=ex.category,
                            file=str(fpath.relative_to(examples_root)),
                            line=i,
                            symbol=sym,
                            confidence="qualified-text",
                        ))

                # Inheritance match (higher confidence, overrides text match)
                for m in _INHERIT_RE.finditer(line):
                    sym = m.group(1)
                    if sym in known_symbols:
                        # Remove any existing qualified-text entry for this
                        # symbol on this line.
                        uses = [u for u in uses
                                if not (u.file == str(fpath.relative_to(examples_root))
                                        and u.line == i
                                        and u.symbol == sym
                                        and u.confidence == "qualified-text")]
                        uses.append(ExampleSymbolUse(
                            example_name=ex.name,
                            category=ex.category,
                            file=str(fpath.relative_to(examples_root)),
                            line=i,
                            symbol=sym,
                            confidence="qualified-inheritance",
                        ))

    uses.sort(key=lambda u: (u.example_name, u.symbol, u.file, u.line))
    return uses


def build_examples_jsonl(
    examples: list[ExampleInfo],
    uses: list[ExampleSymbolUse],
    output_path: Path,
) -> int:
    """Write ``examples.jsonl`` with deterministic ordering.

    Returns the number of use entries written.
    """
    with output_path.open("w", encoding="utf-8") as fh:
        for u in uses:
            rec: dict[str, Any] = {
                "example_name": u.example_name,
                "category": u.category,
                "file": u.file,
                "line": u.line,
                "symbol": u.symbol,
                "confidence": u.confidence,
            }
            fh.write(
                _json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n"
            )

    return len(uses)


def build_examples_markdown(
    examples: list[ExampleInfo],
    uses: list[ExampleSymbolUse],
    output_dir: Path,
) -> int:
    """Generate example navigation Markdown pages.

    Returns the number of pages written.
    """

    output_dir.mkdir(parents=True, exist_ok=True)

    # Build symbol → examples index
    sym_to_ex: dict[str, list[str]] = {}
    for u in uses:
        sym_to_ex.setdefault(u.symbol, []).append(u.example_name)

    # INDEX.md
    by_cat: dict[str, list[ExampleInfo]] = {}
    for ex in examples:
        by_cat.setdefault(ex.category, []).append(ex)

    lines: list[str] = [
        "# JUCE Official Examples",
        "",
        "| Category | Examples |",
        "|----------|----------|",
    ]
    cat_order = ["plugins", "dsp", "audio", "gui", "midi", "utilities", "other"]
    for cat in cat_order:
        exs = by_cat.get(cat, [])
        if exs:
            lines.append(f"| [{cat.title()}]({cat}.md) | {len(exs)} |")
    (output_dir / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Category pages
    count = 1
    for cat in cat_order:
        exs = by_cat.get(cat, [])
        if not exs:
            continue
        clines = [
            f"# {cat.title()} Examples",
            "",
            "| Example | Directory | Files |",
            "|---------|-----------|-------|",
        ]
        for ex in sorted(exs, key=lambda e: e.name):
            clines.append(
                f"| {ex.name} | `{ex.directory}` | {len(ex.files)} |"
            )
        (output_dir / f"{cat}.md").write_text("\n".join(clines) + "\n", encoding="utf-8")
        count += 1

    return count


def _collect_files_recursive(directory: Path, root: Path) -> list[str]:
    """Collect source files from an example directory (recursive)."""
    files: list[str] = []
    for child in sorted(directory.rglob("*")):
        if child.is_file():
            is_scan_ext = child.suffix.lower() in _SCAN_EXTENSIONS
            if is_scan_ext or child.name == "CMakeLists.txt":
                files.append(str(child.relative_to(root)))
    return files
