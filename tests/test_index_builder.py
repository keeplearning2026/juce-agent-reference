"""Tests for index builder."""

from pathlib import Path

from juce_reference.documentation_nodes import Paragraph, Text
from juce_reference.index_builder import (
    build_manifest,
    build_relationships_jsonl,
    build_source_locations_jsonl,
    build_symbols_jsonl,
    build_symbols_tsv,
)
from juce_reference.model import (
    Compound,
    Member,
    Reference,
    SourceLocation,
)


def _sample_compounds() -> list[Compound]:
    return [
        Compound(
            refid="class_Foo", kind="class", name="juce::Foo",
            qualified_name="juce::Foo",
            brief=(Paragraph(children=(Text("A test class"),)),),
            location=SourceLocation(file="juce_Foo.h", line=10),
            members=(
                Member(refid="mem_bar", kind="function", name="bar",
                       qualified_name="juce::Foo::bar",
                       signature="void bar(int x)"),
            ),
            bases=(Reference(text="juce::Base", refid="class_Base"),),
        ),
    ]


def test_symbols_tsv(tmp_path: Path) -> None:
    p = tmp_path / "symbols.tsv"
    count = build_symbols_tsv(_sample_compounds(), p)
    assert count == 2  # compound + member
    content = p.read_text(encoding="utf-8")
    assert "juce::Foo" in content
    assert "juce::Foo::bar" in content


def test_symbols_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "symbols.jsonl"
    count = build_symbols_jsonl(_sample_compounds(), p)
    assert count == 2
    lines = p.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2


def test_relationships_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "relationships.jsonl"
    count = build_relationships_jsonl(_sample_compounds(), p)
    assert count >= 3  # derived-from, base-of, member-of


def test_source_locations_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "source-locations.jsonl"
    count = build_source_locations_jsonl(_sample_compounds(), p)
    assert count == 1  # Foo has location; bar does not


def test_manifest(tmp_path: Path) -> None:
    p = tmp_path / "manifest.json"
    build_manifest(_sample_compounds(), 10, 100, 5, "abc123", p)
    import json
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["juce_commit"] == "abc123"
    assert data["statistics"]["symbols"] == 100
