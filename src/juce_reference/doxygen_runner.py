"""Doxygen runner with overlay support.

Reads the official JUCE Doxyfile, applies a reproducible overlay, executes
Doxygen, and captures all outputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from juce_reference.errors import DoxygenExecutionError
from juce_reference.source import JuceSource
from juce_reference.util.command import run


@dataclass(frozen=True)
class DoxygenResult:
    """Results of a Doxygen run."""

    xml_dir: Path
    generated_doxyfile: Path
    warnings_file: Path
    stdout_file: Path
    stderr_file: Path


# Doxygen overlay options that are appended to the generated Doxyfile.
# Order matters: later values override earlier ones for duplicate keys.
_DOXYGEN_OVERLAY: dict[str, str] = {
    "GENERATE_HTML": "NO",
    "GENERATE_XML": "YES",
    "XML_PROGRAMLISTING": "NO",
    "TIMESTAMP": "NO",
    # Force English for deterministic output.
    "OUTPUT_LANGUAGE": "English",
}

# Keys that must be set by the overlay regardless of what the original says.
_HARD_OVERRIDES: set[str] = {
    "GENERATE_HTML",
    "GENERATE_XML",
    "XML_PROGRAMLISTING",
    "TIMESTAMP",
    "OUTPUT_LANGUAGE",
}


def _parse_doxyfile(path: Path) -> dict[str, str]:
    """Parse a Doxygen configuration file into key-value pairs.

    Handles += continuations and simple multi-line values.
    """
    cfg: dict[str, str] = {}
    current_key: str | None = None

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()

        # Skip comments and blanks.
        if not line or line.startswith("#"):
            continue

        # Continuation of a previous value (lines that start with whitespace
        # after a key=value assignment).
        if current_key is not None and (raw_line.startswith(" ") or raw_line.startswith("\t")):
            cfg[current_key] += "\n" + raw_line.strip()
            continue

        # Match key (+=|=) value
        m = re.match(r"^(\w+)\s*(\+=|=)\s*(.*)", line)
        if not m:
            continue

        key = m.group(1)
        op = m.group(2)
        value = m.group(3).strip()

        if op == "+=":
            cfg[key] = cfg.get(key, "") + value
        else:
            cfg[key] = value

        current_key = key

    return cfg


def _merge_overlay(
    original: dict[str, str],
    overlay: dict[str, str],
    hard_overrides: set[str],
    project_number: str,
) -> str:
    """Merge the overlay into the original, producing a complete Doxyfile string.

    Args:
        original: Parsed original Doxyfile entries.
        overlay: Overlay values to apply.
        hard_overrides: Keys that must be overridden.
        project_number: Value for PROJECT_NUMBER.

    Returns:
        The complete generated Doxyfile content.
    """
    lines: list[str] = []
    seen_keys: set[str] = set()

    lines.append("# ============================================================")
    lines.append("# GENERATED DOXYFILE — DO NOT EDIT")
    lines.append("# Overlay applied to official JUCE docs/doxygen/Doxyfile")
    lines.append("# ============================================================")
    lines.append("")

    # Emit original keys, respecting order in the file.
    for key, value in original.items():
        seen_keys.add(key)
        val = overlay.get(key, original[key]) if key in hard_overrides or key in overlay else value
        lines.append(f"{key} = {val}")

    # Append overlay keys not in the original.
    for key in overlay:
        if key not in seen_keys:
            lines.append(f"{key} = {overlay[key]}")

    # PROJECT_NUMBER is the JUCE commit.
    lines.append(f"PROJECT_NUMBER = {project_number}")

    return "\n".join(lines) + "\n"


def _prepare_overlay(
    juce_doxyfile: Path,
    build_dir: Path,
    project_number: str,
    warnings_log: Path,
) -> Path:
    """Read the official Doxyfile, merge the overlay, and write the result.

    Returns the path to the generated Doxyfile.
    """
    original = _parse_doxyfile(juce_doxyfile)
    overlay = dict(_DOXYGEN_OVERLAY)

    # WARN_LOGFILE must be absolute.
    overlay["WARN_LOGFILE"] = str(warnings_log.resolve())

    content = _merge_overlay(
        original=original,
        overlay=overlay,
        hard_overrides=_HARD_OVERRIDES,
        project_number=project_number,
    )

    generated = build_dir / "Doxyfile.generated"
    generated.write_text(content, encoding="utf-8")
    return generated


def run_doxygen(
    juce_source: JuceSource,
    build_dir: Path,
    *,
    timeout: int = 600,
) -> DoxygenResult:
    """Run Doxygen on the JUCE checkout and return results.

    Args:
        juce_source: Validated `JuceSource`.
        build_dir: Temporary build directory.
        timeout: Maximum time in seconds for Doxygen.

    Returns:
        ``DoxygenResult`` with paths to all outputs.

    Raises:
        DoxygenExecutionError: If Doxygen fails or output is missing.
    """
    xml_dir = build_dir / "xml"
    xml_dir.mkdir(parents=True, exist_ok=True)

    warnings_file = build_dir / "doxygen-warnings.log"
    stdout_file = build_dir / "doxygen-stdout.log"
    stderr_file = build_dir / "doxygen-stderr.log"

    # The Doxyfile overlay sets OUTPUT_DIRECTORY to build_dir,
    # but Doxygen is run from the doxygen docs dir to resolve relative paths.
    generated_doxyfile = _prepare_overlay(
        juce_doxyfile=juce_source.doxygen_file,
        build_dir=build_dir,
        project_number=juce_source.commit,
        warnings_log=warnings_file,
    )

    # Patch OUTPUT_DIRECTORY into the file after initial creation.
    _patch_output_directory(generated_doxyfile, build_dir)

    # Run Doxygen from the docs/doxygen directory so relative paths in the
    # original Doxyfile resolve correctly.
    result = run(
        ["doxygen", str(generated_doxyfile)],
        cwd=juce_source.doxygen_dir,
        timeout=timeout,
    )

    # Write captured output.
    stdout_file.write_text(result.stdout, encoding="utf-8")
    stderr_file.write_text(result.stderr, encoding="utf-8")

    if not result.ok:
        raise DoxygenExecutionError(
            f"Doxygen exited with code {result.returncode}",
            command="doxygen",
            file_path=str(generated_doxyfile),
        )

    # Verify expected output files exist.
    index_xml = xml_dir / "index.xml"
    if not index_xml.is_file():
        raise DoxygenExecutionError(
            "Doxygen ran but xml/index.xml was not generated",
            command="doxygen",
            file_path=str(index_xml),
        )

    # Verify schemas exist.
    for schema in ("index.xsd", "compound.xsd"):
        p = xml_dir / schema
        if not p.is_file():
            raise DoxygenExecutionError(
                f"Doxygen output is missing {schema}",
                command="doxygen",
                file_path=str(p),
            )

    return DoxygenResult(
        xml_dir=xml_dir,
        generated_doxyfile=generated_doxyfile,
        warnings_file=warnings_file,
        stdout_file=stdout_file,
        stderr_file=stderr_file,
    )


def _patch_output_directory(generated_doxyfile: Path, build_dir: Path) -> None:
    """Ensure OUTPUT_DIRECTORY points to the build directory.

    Because Doxygen only respects the last occurrence of a key, we append
    OUTPUT_DIRECTORY at the end of the generated file.
    """
    content = generated_doxyfile.read_text(encoding="utf-8")
    output_line = f"\nOUTPUT_DIRECTORY = {build_dir.resolve()}\n"
    if "OUTPUT_DIRECTORY" in content:
        # Append so it takes precedence (last-wins semantics).
        content += output_line
    else:
        content += output_line
    generated_doxyfile.write_text(content, encoding="utf-8")


def classify_doxygen_warnings(warnings_path: Path) -> dict[str, Any]:
    """Parse Doxygen warnings into categories for reporting.

    Returns:
        A dict with ``total``, ``categories``, and ``critical`` counts.
    """
    text = ""
    if warnings_path.is_file():
        text = warnings_path.read_text(encoding="utf-8", errors="replace")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    total = len(lines)

    categories: dict[str, int] = {}
    critical = 0

    critical_patterns = [
        "cannot open",
        "unable to",
        "failed to open",
        "input file",
        "output file",
    ]

    for line in lines:
        lower = line.lower()
        # Extract the Doxygen warning prefix, e.g. "file:line: warning: …"
        parts = line.split(":", 2)
        cat = "other"
        if len(parts) >= 3 and "warning" in parts[2].lower():
            # Try to extract the warning kind.
            warn_part = parts[2].strip()
            cat = warn_part.split()[0] if warn_part else "other"

        cat_key = cat.lower()
        categories[cat_key] = categories.get(cat_key, 0) + 1

        for pat in critical_patterns:
            if pat in lower:
                critical += 1
                break

    return {
        "total": total,
        "categories": categories,
        "critical": critical,
    }
