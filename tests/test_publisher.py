"""Tests for atomic publisher."""

from pathlib import Path

import pytest

from juce_reference.errors import PublishError
from juce_reference.publisher import publish_release


def test_publish_non_release(tmp_path: Path) -> None:
    """Non-release publishes don't create release structure."""
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "test.md").write_text("hello", encoding="utf-8")

    output = tmp_path / "output"
    output.mkdir()

    result = publish_release(candidate, output, "a" * 40, release=False)
    assert result.published is False


def test_publish_release_new(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "test.md").write_text("hello", encoding="utf-8")

    output = tmp_path / "output"
    output.mkdir()

    result = publish_release(candidate, output, "a" * 40, release=True)
    assert result.published is True
    assert result.reused is False
    release_dir = output / "releases" / ("a" * 40)
    assert release_dir.is_dir()
    assert (output / "current.json").is_file()


def test_publish_same_content_reuses(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "test.md").write_text("hello", encoding="utf-8")

    output = tmp_path / "output"
    output.mkdir()

    # First publish
    r1 = publish_release(candidate, output, "a" * 40, release=True)
    assert r1.published
    assert not r1.reused

    # Second publish with same content
    candidate2 = tmp_path / "candidate2"
    candidate2.mkdir()
    (candidate2 / "test.md").write_text("hello", encoding="utf-8")

    r2 = publish_release(candidate2, output, "a" * 40, release=True)
    assert r2.published
    assert r2.reused  # Should reuse, content is the same


def test_different_content_fails(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "test.md").write_text("version1", encoding="utf-8")

    output = tmp_path / "output"
    output.mkdir()

    publish_release(candidate, output, "a" * 40, release=True)

    # Different content with same commit
    candidate2 = tmp_path / "candidate2"
    candidate2.mkdir()
    (candidate2 / "test.md").write_text("version2", encoding="utf-8")

    with pytest.raises(PublishError, match="different content"):
        publish_release(candidate2, output, "a" * 40, release=True)


def test_failed_publish_preserves_current(tmp_path: Path) -> None:
    """A failed publish doesn't corrupt existing current.json."""
    output = tmp_path / "output"
    output.mkdir()

    # Publish version A
    c_a = tmp_path / "candidate_a"
    c_a.mkdir()
    (c_a / "test.md").write_text("A", encoding="utf-8")
    publish_release(c_a, output, "a" * 40, release=True)

    import json
    current_a = json.loads((output / "current.json").read_text())
    assert current_a["commit"] == "a" * 40

    # Try to publish different content with same commit (should fail)
    c_b = tmp_path / "candidate_b"
    c_b.mkdir()
    (c_b / "test.md").write_text("B", encoding="utf-8")
    from contextlib import suppress
    with suppress(PublishError):
        publish_release(c_b, output, "a" * 40, release=True)

    # Current should still point to A
    current_after = json.loads((output / "current.json").read_text())
    assert current_after["commit"] == "a" * 40
