"""Load and validate YAML symbol alias configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from juce_reference.errors import ConversionError


@dataclass(frozen=True)
class AliasConfig:
    """A loaded and validated alias configuration."""

    symbols: dict[str, AliasEntry]
    alias_to_symbol: dict[str, str]


@dataclass(frozen=True)
class AliasEntry:
    """Aliases and concept tags for one symbol."""

    aliases: tuple[str, ...] = ()
    concepts: tuple[str, ...] = ()


def load_aliases(path: Path, valid_symbols: frozenset[str]) -> AliasConfig:
    """Load aliases from a YAML file and validate every target symbol exists.

    Args:
        path: Path to ``aliases.yml``.
        valid_symbols: Set of known qualified symbol names.

    Returns:
        ``AliasConfig`` with forward and reverse mappings.

    Raises:
        ConversionError: If an alias targets a non-existent symbol.
    """
    raw: dict[str, dict[str, list[str]]] = {}

    if not path.is_file():
        return AliasConfig(symbols={}, alias_to_symbol={})

    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    symbols: dict[str, AliasEntry] = {}
    alias_to_symbol: dict[str, str] = {}

    for symbol_name, entry_data in raw.items():
        sym = symbol_name.strip()
        if not sym:
            continue

        if sym not in valid_symbols:
            raise ConversionError(
                f"Alias target symbol not found in index: {sym}",
                symbol=sym,
                suggestion="Remove the alias or fix the symbol name",
            )

        aliases: list[str] = []
        concepts: list[str] = []

        if isinstance(entry_data, dict):
            for a in entry_data.get("aliases", []) or []:
                a = " ".join(str(a).split())
                aliases.append(a)
                alias_to_symbol[a.casefold()] = sym
            for c in entry_data.get("concepts", []) or []:
                c = " ".join(str(c).split())
                concepts.append(c)

        symbols[sym] = AliasEntry(
            aliases=tuple(aliases),
            concepts=tuple(concepts),
        )

    return AliasConfig(symbols=symbols, alias_to_symbol=alias_to_symbol)


def generate_auto_aliases(name: str) -> list[str]:
    """Generate automatic low-weight aliases from a symbol name.

    Examples for ``AudioProcessorValueTreeState``:
    - ``AudioProcessorValueTreeState`` (exact)
    - ``Audio Processor Value Tree State`` (camel-split)
    - ``audio processor value tree state`` (lowercase)
    """
    from juce_reference.util.text import camel_to_words

    short = name.rsplit("::", maxsplit=1)[-1]
    words = camel_to_words(short)
    return [short, words, words.lower()]
