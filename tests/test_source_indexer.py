"""Tests for source indexer."""

from pathlib import Path

from juce_reference.index_builder import build_source_locations_jsonl
from juce_reference.model import Compound, SourceLocation
from juce_reference.source_indexer import validate_source_locations_jsonl


def test_validate_locations_all_valid(tmp_path: Path) -> None:
    # Create a source file
    source_file = tmp_path / "test.h"
    source_file.write_text("// test", encoding="utf-8")

    compounds = [
        Compound(
            refid="class_Foo", kind="class", name="Foo",
            qualified_name="Foo",
            location=SourceLocation(file=str(source_file), line=1),
        ),
    ]

    jsonl = tmp_path / "source-locations.jsonl"
    build_source_locations_jsonl(compounds, jsonl)

    result = validate_source_locations_jsonl(jsonl, tmp_path)
    assert result["total"] == 1
    assert result["valid"] == 1
    assert result["missing"] == []


def test_validate_locations_missing(tmp_path: Path) -> None:
    compounds = [
        Compound(
            refid="class_Foo", kind="class", name="Foo",
            qualified_name="Foo",
            location=SourceLocation(file="nonexistent.h", line=1),
        ),
    ]

    jsonl = tmp_path / "source-locations.jsonl"
    build_source_locations_jsonl(compounds, jsonl)

    result = validate_source_locations_jsonl(jsonl, tmp_path)
    assert result["total"] == 1
    assert result["valid"] == 0
    assert len(result["missing"]) == 1
