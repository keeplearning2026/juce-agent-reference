"""Tests for the immutable BuildContext."""

import dataclasses
from pathlib import Path

import pytest

from juce_reference.build_context import BuildContext


def test_build_context_is_frozen() -> None:
    ctx = BuildContext(
        build_id="test-1",
        repository_root=Path("/repo"),
        juce_root=Path("/juce"),
        output_root=Path("/out"),
        build_root=Path("/build"),
        release_root=Path("/out/releases/abc123"),
        juce_commit="a" * 40,
        juce_dirty=False,
        doxygen_version="1.9.5",
        generator_version="0.1.0",
    )
    assert ctx.juce_commit == "a" * 40
    assert ctx.juce_dirty is False
    assert ctx.doxygen_version == "1.9.5"

    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.juce_commit = "new"  # type: ignore[misc]
