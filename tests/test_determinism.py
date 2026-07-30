"""Tests for determinism checker."""

from pathlib import Path

import pytest

from juce_reference.determinism import (
    compare_generations,
    compare_sqlite_logical,
)
from juce_reference.errors import DeterminismError


def test_identical_dirs_are_deterministic(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()

    (a / "test.md").write_text("# Title\n\nHello\n", encoding="utf-8")
    (b / "test.md").write_text("# Title\n\nHello\n", encoding="utf-8")

    result = compare_generations(a, b)
    assert result["passed"] is True
    assert result["files_compared"] == 1


def test_different_content_fails(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()

    (a / "test.md").write_text("A\n", encoding="utf-8")
    (b / "test.md").write_text("B\n", encoding="utf-8")

    with pytest.raises(DeterminismError):
        compare_generations(a, b)


def test_missing_file_in_b(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()

    (a / "test.md").write_text("hello\n", encoding="utf-8")

    with pytest.raises(DeterminismError):
        compare_generations(a, b)


def test_sqlite_logical_comparison(tmp_path: Path) -> None:
    """Two identical logical databases."""
    import sqlite3

    db_a = tmp_path / "a.sqlite"
    db_b = tmp_path / "b.sqlite"

    for db_path in (db_a, db_b):
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE symbols (id INTEGER, symbol TEXT)")
        conn.execute("INSERT INTO symbols VALUES (1, 'juce::Foo')")
        conn.execute(
            "CREATE VIRTUAL TABLE symbol_fts USING fts5(symbol)"
        )
        conn.execute("INSERT INTO symbol_fts VALUES ('juce::Foo')")
        conn.commit()
        conn.close()

    result = compare_sqlite_logical(db_a, db_b)
    assert result["passed"] is True
