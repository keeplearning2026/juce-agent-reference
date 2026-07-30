"""Immutable generator configuration.

Configuration sources, in priority order:
    1. CLI arguments
    2. Environment variables
    3. Default values
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GeneratorConfig:
    """Immutable configuration for a single generator run."""

    juce_root: Path
    output_root: Path
    allow_dirty: bool = False
    keep_build: bool = False
    release: bool = False
    aliases_file: Path | None = None
    strict_external_links: bool = False
    verbose: bool = False
    no_color: bool = False

    @classmethod
    def defaults_for(cls, juce_root: Path, output_root: Path) -> GeneratorConfig:
        """Build a config from the two mandatory paths, with sensible defaults."""
        return cls(juce_root=juce_root, output_root=output_root)
