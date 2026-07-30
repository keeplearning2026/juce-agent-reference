"""Tests for the environment doctor."""

import json

from juce_reference.doctor import (
    DoctorReport,
    check_python,
    check_sqlite,
    doctor_report_json,
)


def test_doctor_report_starts_passed() -> None:
    report = DoctorReport()
    assert report.passed is True
    assert report.checks == []


def test_add_failed_check_flips_passed() -> None:
    report = DoctorReport()
    report.add("test-check", False, detail="broken")
    assert report.passed is False
    assert len(report.checks) == 1


def test_add_passed_check_keeps_passed() -> None:
    report = DoctorReport()
    report.add("test-check", True, detail="ok")
    assert report.passed is True


def test_check_python_is_ok() -> None:
    report = DoctorReport()
    check_python(report)
    # On a working system with 3.12+, all checks should pass.
    for check in report.checks:
        assert check["passed"], f"{check['name']}: {check.get('detail', '')}"


def test_check_sqlite_fts5_available() -> None:
    report = DoctorReport()
    check_sqlite(report)
    assert report.checks[0]["passed"] is True


def test_doctor_report_json_is_valid() -> None:
    report = DoctorReport()
    report.add("test", True, detail="ok")
    raw = doctor_report_json(report)
    data = json.loads(raw)
    assert data["passed"] is True
    assert len(data["checks"]) == 1
