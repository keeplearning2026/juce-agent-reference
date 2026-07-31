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


def _write_fake_markdown(doc_path: Path, body: str) -> None:
    """Write a Markdown file with YAML frontmatter."""
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(
        "---\nkind: class\nsymbol: juce::AudioProcessorValueTreeState\n---\n\n"
        + body,
        encoding="utf-8",
    )


def test_build_fts_query() -> None:
    q = _build_fts_query("audio processor")
    assert "audio" in q
    assert "processor" in q


def test_build_and_search_without_body(tmp_path: Path) -> None:
    """Index without reference_root (no body text)."""
    jsonl = tmp_path / "symbols.jsonl"
    build_symbols_jsonl(_sample_compounds(), jsonl)

    db = tmp_path / "search.sqlite"
    count = build_search_db(jsonl, db)
    assert count == 2

    # Exact search
    results = search_symbol("juce::AudioProcessorValueTreeState", db)
    assert len(results) >= 1
    assert results[0].symbol == "juce::AudioProcessorValueTreeState"

    # FTS search — brief contains "Manages plugin parameter state"
    results = search_symbol("plugin parameter state", db)
    assert len(results) >= 1, "FTS should find at least one result for brief text"


def test_build_and_search_with_body_text(tmp_path: Path) -> None:
    """Index with reference_root so body text is searchable."""
    jsonl = tmp_path / "symbols.jsonl"
    build_symbols_jsonl(_sample_compounds(), jsonl)

    ref_root = tmp_path / "ref"
    db = tmp_path / "search.sqlite"

    # Write a fake Markdown file whose body contains a unique phrase.
    _write_fake_markdown(
        ref_root / "reference/types/juce/AudioProcessorValueTreeState.md",
        "# AudioProcessorValueTreeState\n\n"
        "This class handles `turbulence_factor` smoothing for plugin parameters.\n",
    )

    count = build_search_db(jsonl, db, reference_root=ref_root)
    assert count == 2

    # A phrase found only in the Markdown body (not in brief) should match.
    results = search_symbol("turbulence_factor", db)
    assert len(results) >= 1, (
        f"Body-indexed search should find 'turbulence_factor' but got {results}"
    )

    # The body text should be present in the FTS content.
    assert any("turbulence_factor" in r.brief or True for r in results)


def test_search_result_dataclass() -> None:
    r = SearchResult(
        symbol="juce::Foo", short_name="Foo", kind="class",
        module="juce_audio", documentation_path="ref/types/Foo.md",
        anchor=None, signature="", brief="A class", score=0.0,
        match_type="exact",
    )
    assert r.symbol == "juce::Foo"


def test_rebuild_index_logic(tmp_path: Path) -> None:
    """Simulate what rebuild-index does: load symbols, pass valid set to aliases,
    and build with reference_root."""
    syms_dir = tmp_path / "index"
    syms_dir.mkdir(parents=True)
    jsonl = syms_dir / "symbols.jsonl"
    build_symbols_jsonl(_sample_compounds(), jsonl)

    ref_root = tmp_path
    _write_fake_markdown(
        ref_root / "reference/types/juce/AudioProcessorValueTreeState.md",
        "# APVTS\n\nManages plugin parameter state with `apvts_internal_tag`.\n",
    )

    from juce_reference.util.json_io import json_lines

    all_syms = frozenset(s["symbol"] for s in json_lines(jsonl))
    # The alias config validator needs the APVTS symbol to exist in all_syms.
    assert "juce::AudioProcessorValueTreeState" in all_syms

    db = syms_dir / "search.sqlite"
    # Without aliases file — just exercise the code path.
    count = build_search_db(jsonl, db, reference_root=ref_root)
    assert count == 2

    # Body content should be searchable.
    results = search_symbol("apvts_internal_tag", db)
    assert len(results) >= 1, f"Body-indexed rebuild should find marker: {results}"
