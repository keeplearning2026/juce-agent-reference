"""Tests for output validator."""

from pathlib import Path

from juce_reference.output_validator import (
    ValidationIssue,
    validate_output,
)


def test_validation_issue_create() -> None:
    i = ValidationIssue(
        severity="error",
        code="test-code",
        message="test message",
        path="test.md",
        symbol="juce::Foo",
    )
    assert i.severity == "error"
    assert i.symbol == "juce::Foo"


def test_validate_empty_dir(tmp_path: Path) -> None:
    report = validate_output(tmp_path)
    assert report.passed is True


def test_validate_missing_links(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text(
        "[broken](./nonexistent.md)\n", encoding="utf-8"
    )
    report = validate_output(tmp_path)
    # Should find broken internal link
    broken = [i for i in report.issues if i.code == "broken-internal-link"]
    assert len(broken) > 0


def test_validate_unresolved_references(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text(
        "[ref](unresolved:abc123)\n", encoding="utf-8"
    )
    report = validate_output(tmp_path)
    unresolved = [i for i in report.issues if i.code == "unresolved-reference"]
    assert len(unresolved) > 0


def test_validate_unclosed_code_block(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text(
        "```cpp\nsome code\n", encoding="utf-8"
    )
    report = validate_output(tmp_path)
    unclosed = [i for i in report.issues if i.code == "unclosed-code-block"]
    assert len(unclosed) > 0
