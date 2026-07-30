"""Tests for alias loader."""

from pathlib import Path

import pytest

from juce_reference.alias_loader import (
    generate_auto_aliases,
    load_aliases,
)
from juce_reference.errors import ConversionError


def test_generate_auto_aliases() -> None:
    aliases = generate_auto_aliases("juce::AudioProcessorValueTreeState")
    assert "AudioProcessorValueTreeState" in aliases
    assert "Audio Processor Value Tree State" in aliases


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    cfg = load_aliases(tmp_path / "nonexistent.yml", frozenset())
    assert cfg.symbols == {}
    assert cfg.alias_to_symbol == {}


def test_valid_aliases(tmp_path: Path) -> None:
    p = tmp_path / "aliases.yml"
    p.write_text("""
juce::Foo:
  aliases:
    - FOO
  concepts:
    - do something with foo
""", encoding="utf-8")
    cfg = load_aliases(p, frozenset({"juce::Foo"}))
    assert "FOO" in cfg.symbols["juce::Foo"].aliases
    assert cfg.alias_to_symbol["foo"] == "juce::Foo"


def test_invalid_symbol_fails(tmp_path: Path) -> None:
    p = tmp_path / "aliases.yml"
    p.write_text("juce::Missing: {aliases: [MISS]}", encoding="utf-8")
    with pytest.raises(ConversionError, match="not found"):
        load_aliases(p, frozenset({"juce::Foo"}))
