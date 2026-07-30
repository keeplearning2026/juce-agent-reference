"""Tests for JUCE source validation."""

from pathlib import Path

import pytest

from juce_reference.errors import JuceSourceError
from juce_reference.source import validate_juce_source


def test_validate_rejects_missing_root(tmp_path: Path) -> None:
    missing = tmp_path / "no-such-dir"
    with pytest.raises(JuceSourceError, match="does not exist"):
        validate_juce_source(missing)


def test_validate_rejects_non_juce_dir(tmp_path: Path) -> None:
    # A directory without modules/ is not a valid JUCE root.
    with pytest.raises(JuceSourceError, match="modules/"):
        validate_juce_source(tmp_path)


def test_validate_rejects_dirty(tmp_path: Path) -> None:
    """Integration-style test: create a fake JUCE tree in a git repo."""
    import subprocess

    root = tmp_path / "fake_juce"
    root.mkdir()

    # Init git
    subprocess.run(["git", "init"], cwd=root, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=root, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=root, capture_output=True, text=True,
    )

    # Create modules/
    (root / "modules").mkdir()

    # Create docs/doxygen/Doxyfile
    doxy_dir = root / "docs" / "doxygen"
    doxy_dir.mkdir(parents=True)
    (doxy_dir / "Doxyfile").write_text("# placeholder")

    # Commit so there's a HEAD
    subprocess.run(["git", "add", "."], cwd=root, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True, text=True)

    # Validate clean first
    src = validate_juce_source(root, allow_dirty=False)
    assert src.dirty is False
    assert len(src.commit) == 40

    # Make dirty
    (root / "dirty_file.txt").write_text("hello")
    with pytest.raises(JuceSourceError, match="dirty"):
        validate_juce_source(root, allow_dirty=False)

    # Should pass with --allow-dirty
    src_dirty = validate_juce_source(root, allow_dirty=True)
    assert src_dirty.dirty is True
