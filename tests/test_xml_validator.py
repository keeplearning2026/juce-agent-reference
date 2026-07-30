"""Tests for XML validator."""

from pathlib import Path

import pytest

from juce_reference.errors import XmlValidationError
from juce_reference.xml_validator import (
    XmlValidationIssue,
    XmlValidationReport,
    validate_index,
    validate_member_refids,
)


def test_validation_issue_create() -> None:
    issue = XmlValidationIssue(file="test.xml", line=10, message="bad")
    assert issue.file == "test.xml"
    assert issue.line == 10
    assert "bad" in issue.message


def test_report_all_valid() -> None:
    report = XmlValidationReport(
        index_valid=True,
        compound_count=5,
        valid_compound_count=5,
        issues=(),
        duplicate_refids=(),
        missing_files=(),
    )
    assert report.all_valid is True


def test_report_not_all_valid() -> None:
    report = XmlValidationReport(
        index_valid=True,
        compound_count=5,
        valid_compound_count=4,
        issues=(XmlValidationIssue(file="x.xml", line=1, message="err"),),
        duplicate_refids=(),
        missing_files=(),
    )
    assert report.all_valid is False


def test_validate_index_missing_file(tmp_path: Path) -> None:
    with pytest.raises(XmlValidationError, match="index.xml not found"):
        validate_index(tmp_path)


def test_validate_member_refids_empty() -> None:
    result = validate_member_refids([])
    assert result == ()


def test_validate_member_refids_no_dupes() -> None:
    entries = [
        {"refid": "a", "kind": "class", "name": "A"},
        {"refid": "b", "kind": "class", "name": "B"},
    ]
    result = validate_member_refids(entries)
    assert result == ()
