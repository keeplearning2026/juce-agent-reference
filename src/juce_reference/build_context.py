"""Immutable build context — created once, passed explicitly.

The BuildContext is the single source of truth for every path and version
identifier used during a generation run.  No module is allowed to
re-derive these values from the environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildContext:
    """Immutable context for a single build / generation run."""

    build_id: str
    """Unique opaque id for this build, used for temp directories."""

    repository_root: Path
    """Root of the *juce-reference* repository."""

    juce_root: Path
    """Root of the JUCE checkout."""

    output_root: Path
    """Where the final generated release is placed."""

    build_root: Path
    """Temporary build directory (``.build/<build_id>``)."""

    release_root: Path
    """Final release directory (``<output>/releases/<commit>``)."""

    juce_commit: str
    """Full 40-char SHA of the JUCE checkout."""

    juce_dirty: bool
    """True when the JUCE working tree has uncommitted changes."""

    doxygen_version: str
    """Exact Doxygen version used (e.g. ``1.9.5``)."""

    generator_version: str
    """Version of this generator (``0.1.0``)."""

    ir_schema_version: int = 1
    markdown_schema_version: int = 1
    index_schema_version: int = 1
