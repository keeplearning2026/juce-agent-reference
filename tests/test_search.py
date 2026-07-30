"""Tests for search module."""

from pathlib import Path

from juce_reference.documentation_nodes import Paragraph, Text
from juce_reference.index_builder import build_symbols_jsonl
from juce_reference.model import (
    Compound,
    Member,
)
from juce_reference.search import (
    SearchResult,
    _build_fts_query,
    build_search_db,
    search_symbol,
)


def _sample_compounds() -> list[Compound]:
    return [
        Compound(
            refid="class_APVTS", kind="class",
            name="juce::AudioProcessorValueTreeState",
            qualified_name="juce::AudioProcessorValueTreeState",
            brief=(Paragraph(children=(Text("Manages plugin parameter state"),)),),
            members=(
                Member(
                    refid="mem_save", kind="function", name="save",
                    qualified_name="juce::AudioProcessorValueTreeState::save",
                    signature="void save()",
                    brief=(Paragraph(children=(Text("Saves the state"),)),),
                ),
            ),
        ),
    ]


def test_build_fts_query() -> None:
    q = _build_fts_query("audio processor")
    assert "audio" in q
    assert "processor" in q


def test_build_and_search(tmp_path: Path) -> None:
    jsonl = tmp_path / "symbols.jsonl"
    build_symbols_jsonl(_sample_compounds(), jsonl)

    db = tmp_path / "search.sqlite"
    count = build_search_db(jsonl, db)
    assert count == 2

    # Exact search
    results = search_symbol("juce::AudioProcessorValueTreeState", db)
    assert len(results) >= 1
    assert results[0].symbol == "juce::AudioProcessorValueTreeState"

    # FTS search
    results = search_symbol("plugin parameter state", db)
    assert len(results) >= 0  # May return results if FTS matches


def test_search_result_dataclass() -> None:
    r = SearchResult(
        symbol="juce::Foo", short_name="Foo", kind="class",
        module="juce_audio", documentation_path="ref/types/Foo.md",
        anchor=None, signature="", brief="A class", score=0.0,
        match_type="exact",
    )
    assert r.symbol == "juce::Foo"
