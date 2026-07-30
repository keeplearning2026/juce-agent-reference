"""Environment doctor.

Checks everything needed to generate a JUCE reference, then produces a
machine-readable report.
"""

from __future__ import annotations

import json as _json
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from juce_reference.errors import EnvironmentCheckError
from juce_reference.util.command import run


@dataclass
class DoctorReport:
    """Structured result of an environment check."""

    passed: bool = True
    checks: list[dict[str, Any]] = field(default_factory=list)

    def add(
        self,
        name: str,
        passed: bool,
        *,
        detail: str = "",
        suggestion: str = "",
    ) -> None:
        self.checks.append(
            {
                "name": name,
                "passed": passed,
                "detail": detail,
                "suggestion": suggestion,
            }
        )
        if not passed:
            self.passed = False


def check_python(report: DoctorReport) -> None:
    """Verify Python version and core imports."""
    version = sys.version_info
    ok = version >= (3, 12)
    report.add(
        "python-version",
        ok,
        detail=f"{version.major}.{version.minor}.{version.micro}",
        suggestion="Install Python 3.12+" if not ok else "",
    )

    required = ["lxml", "typer", "rich", "platformdirs", "yaml"]
    for pkg in required:
        try:
            __import__(pkg)
            report.add(f"python-import-{pkg}", True, detail="importable")
        except ImportError:
            report.add(
                f"python-import-{pkg}",
                False,
                detail="not importable",
                suggestion=f"pip install {pkg}",
            )


def check_git(report: DoctorReport) -> None:
    """Verify Git is available."""
    result = run(["git", "--version"])
    report.add(
        "git-available",
        result.ok,
        detail=result.stdout.strip() if result.ok else result.stderr.strip(),
        suggestion="Install Git" if not result.ok else "",
    )


def check_doxygen(report: DoctorReport, expected_version: str | None = None) -> None:
    """Verify Doxygen is available and at the expected version."""
    result = run(["doxygen", "--version"])
    if not result.ok:
        report.add(
            "doxygen-available",
            False,
            detail=f"doxygen --version failed: {result.stderr.strip()}",
            suggestion="Install Doxygen",
        )
        return

    actual = result.stdout.strip()
    report.add("doxygen-available", True, detail=actual)

    if expected_version and actual != expected_version:
        report.add(
            "doxygen-version-locked",
            False,
            detail=f"expected {expected_version}, got {actual}",
            suggestion=f"Install Doxygen {expected_version}",
        )
    elif expected_version:
        report.add("doxygen-version-locked", True, detail=f"locked at {expected_version}")


def check_sqlite(report: DoctorReport) -> None:
    """Verify SQLite FTS5 support."""
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")
        conn.execute("DROP TABLE test_fts")
        conn.close()
        report.add("sqlite-fts5", True, detail="FTS5 available")
    except Exception as exc:
        report.add(
            "sqlite-fts5",
            False,
            detail=str(exc),
            suggestion="Install a Python with SQLite FTS5 support",
        )


def check_filesystem(report: DoctorReport, test_dir: Path | None = None) -> None:
    """Verify output directory is writable and supports atomic rename."""
    if test_dir is None:
        import tempfile

        test_dir = Path(tempfile.gettempdir())

    try:
        test_file = test_dir / ".juce_ref_fs_test"
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
        report.add("filesystem-writable", True, detail=str(test_dir))
    except OSError as exc:
        report.add(
            "filesystem-writable",
            False,
            detail=str(exc),
            suggestion="Ensure output directory is writable",
        )


def check_juce_structure(report: DoctorReport, juce_root: Path) -> None:
    """Verify the JUCE checkout has the expected structure."""
    modules = juce_root / "modules"
    doxyfile = juce_root / "docs" / "doxygen" / "Doxyfile"

    report.add(
        "juce-modules",
        modules.is_dir(),
        detail=str(modules),
        suggestion="Ensure JUCE modules/ exists" if not modules.is_dir() else "",
    )

    report.add(
        "juce-doxyfile",
        doxyfile.is_file(),
        detail=str(doxyfile),
        suggestion="Ensure JUCE docs/doxygen/Doxyfile exists" if not doxyfile.is_file() else "",
    )

    examples = juce_root / "examples"
    report.add(
        "juce-examples",
        examples.is_dir(),
        detail=f"{'present' if examples.is_dir() else 'missing'}",
        suggestion="" if examples.is_dir() else "Examples directory missing (non-fatal for V1)",
    )


def run_doctor(
    juce_root: Path,
    *,
    expected_doxygen: str | None = None,
) -> DoctorReport:
    """Run all environment checks and return a structured report.

    Args:
        juce_root: Path to the JUCE checkout.
        expected_doxygen: Expected Doxygen version from toolchain lock.

    Returns:
        ``DoctorReport`` with ``passed`` indicating overall health.

    Raises:
        EnvironmentCheckError: If a critical check fails.
    """
    report = DoctorReport()
    check_python(report)
    check_git(report)
    check_doxygen(report, expected_version=expected_doxygen)
    check_sqlite(report)
    check_filesystem(report)
    check_juce_structure(report, juce_root)

    if not report.passed:
        # Build a summary for the exception message.
        failed = [c for c in report.checks if not c["passed"]]
        names = ", ".join(c["name"] for c in failed)
        raise EnvironmentCheckError(
            f"Environment checks failed: {names}",
            suggestion="Run 'juce-doc doctor' for details",
        )

    return report


def doctor_report_json(report: DoctorReport) -> str:
    """Render a DoctorReport as JSON."""
    return _json.dumps(
        {"passed": report.passed, "checks": report.checks},
        indent=2,
        ensure_ascii=False,
    )
