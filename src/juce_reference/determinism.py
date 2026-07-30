"""Deterministic output tests.

Run generation twice and compare outputs byte-for-byte.
"""

from __future__ import annotations

import filecmp
from pathlib import Path
from typing import Any

from juce_reference.errors import DeterminismError


def compare_generations(dir_a: Path, dir_b: Path) -> dict[str, Any]:
    """Compare two generation runs for deterministic output.

    Compares file listing and byte content for all non-temporary files.

    Args:
        dir_a: First generation output.
        dir_b: Second generation output.

    Returns:
        A dict with ``passed``, ``differences``, and ``files_compared``.

    Raises:
        DeterminismError: If outputs differ.
    """
    # Files to skip (non-deterministic by nature)
    skip_patterns = {
        "reports/generation.json",
        "reports/doxygen-warnings.log",
        "search.sqlite",  # SQLite may differ in bytes but should have same logical content
    }

    a_files: dict[str, Path] = {}
    b_files: dict[str, Path] = {}

    for p in dir_a.rglob("*"):
        if p.is_file():
            rel = p.relative_to(dir_a).as_posix()
            if rel not in skip_patterns:
                a_files[rel] = p

    for p in dir_b.rglob("*"):
        if p.is_file():
            rel = p.relative_to(dir_b).as_posix()
            if rel not in skip_patterns:
                b_files[rel] = p

    differences: list[str] = []

    # Files in A but not B
    for f in a_files:
        if f not in b_files:
            differences.append(f"missing from B: {f}")

    # Files in B but not A
    for f in b_files:
        if f not in a_files:
            differences.append(f"extra in B: {f}")

    # Compare content
    for f in sorted(a_files):
        if f in b_files and not _files_equal(a_files[f], b_files[f]):
            differences.append(f"content differs: {f}")

    passed = len(differences) == 0
    if not passed:
        raise DeterminismError(
            f"Outputs differ: {len(differences)} differences",
            suggestion="First differences:\n" + "\n".join(differences[:10]),
        )

    return {
        "passed": True,
        "differences": [],
        "files_compared": len(a_files),
    }


def _files_equal(a: Path, b: Path) -> bool:
    """Compare two files byte-for-byte."""
    return filecmp.cmp(str(a), str(b), shallow=False)


def compare_sqlite_logical(db_a: Path, db_b: Path) -> dict[str, Any]:
    """Compare SQLite databases logically (not byte-for-byte).

    Exports all rows and compares them.
    """
    import sqlite3

    if not db_a.is_file() and not db_b.is_file():
        return {"passed": True, "differences": []}

    if not db_a.is_file() or not db_b.is_file():
        return {"passed": False, "differences": ["one SQLite file is missing"]}

    conn_a = sqlite3.connect(str(db_a))
    conn_b = sqlite3.connect(str(db_b))

    diffs: list[str] = []

    try:
        rows_a = list(conn_a.execute("SELECT * FROM symbols ORDER BY id"))
        rows_b = list(conn_b.execute("SELECT * FROM symbols ORDER BY id"))
        if rows_a != rows_b:
            diffs.append("symbols table differs")

        rows_a_fts = list(conn_a.execute("SELECT * FROM symbol_fts ORDER BY rowid"))
        rows_b_fts = list(conn_b.execute("SELECT * FROM symbol_fts ORDER BY rowid"))
        if rows_a_fts != rows_b_fts:
            diffs.append("symbol_fts table differs")
    finally:
        conn_a.close()
        conn_b.close()

    return {"passed": len(diffs) == 0, "differences": diffs}
