"""Tests for the immutable generator configuration."""

import dataclasses
from pathlib import Path

import pytest

from juce_reference.config import GeneratorConfig


def test_defaults_for_builds_config() -> None:
    cfg = GeneratorConfig.defaults_for(Path("/juce"), Path("/out"))
    assert cfg.juce_root == Path("/juce")
    assert cfg.output_root == Path("/out")
    assert cfg.allow_dirty is False
    assert cfg.release is False


def test_config_is_frozen() -> None:
    cfg = GeneratorConfig.defaults_for(Path("/juce"), Path("/out"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.allow_dirty = True  # type: ignore[misc]
