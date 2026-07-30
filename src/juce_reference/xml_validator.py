"""Doxygen XML schema and integrity validation.

Validates index.xml and every compound XML file against the Doxygen-supplied
XSD schemas.  Also checks for duplicate refids and missing files.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from lxml import etree  # type: ignore[import-untyped]

from juce_reference.errors import XmlValidationError


@dataclass(frozen=True)
class XmlValidationIssue:
    """A single validation problem."""

    file: str
    line: int | None
    message: str


@dataclass(frozen=True)
class XmlValidationReport:
    """Results of validating a Doxygen XML output directory."""

    index_valid: bool
    compound_count: int
    valid_compound_count: int
    issues: tuple[XmlValidationIssue, ...]
    duplicate_refids: tuple[str, ...]
    missing_files: tuple[str, ...]

    @property
    def all_valid(self) -> bool:
        return self.index_valid and self.valid_compound_count == self.compound_count


def _load_xml(filepath: Path) -> etree._ElementTree:
    """Load and parse an XML file, returning the element tree."""
    try:
        tree = etree.parse(str(filepath))
        return tree
    except etree.XMLSyntaxError as exc:
        raise XmlValidationError(
            f"XML syntax error in {filepath.name}: {exc}",
            file_path=str(filepath),
        ) from exc


def validate_index(xml_dir: Path) -> tuple[bool, list[dict[str, str]], list[XmlValidationIssue]]:
    """Validate index.xml against index.xsd.

    Returns:
        (valid, compound_entries, issues)
    """
    index_path = xml_dir / "index.xml"
    schema_path = xml_dir / "index.xsd"

    if not index_path.is_file():
        raise XmlValidationError(
            f"index.xml not found in {xml_dir}",
            file_path=str(index_path),
        )
    if not schema_path.is_file():
        raise XmlValidationError(
            f"index.xsd not found in {xml_dir}",
            file_path=str(schema_path),
        )

    issues: list[XmlValidationIssue] = []

    # Load and validate against XSD.
    try:
        schema_doc = etree.parse(str(schema_path))
        schema = etree.XMLSchema(schema_doc)
        tree = _load_xml(index_path)
        valid = schema.validate(tree)
        if not valid:
            for error in schema.error_log:
                issues.append(
                    XmlValidationIssue(
                        file="index.xml",
                        line=error.line,
                        message=error.message,
                    )
                )
    except Exception as exc:
        raise XmlValidationError(
            f"Failed to validate index.xml: {exc}",
            file_path=str(index_path),
        ) from exc

    # Extract compound entries.
    compounds: list[dict[str, str]] = []
    root = tree.getroot()
    for elem in root.iterfind("compound"):
        refid = elem.get("refid")
        kind = elem.get("kind")
        name = elem.findtext("name", "")
        if refid:
            compounds.append(
                {
                    "refid": refid,
                    "kind": kind or "",
                    "name": name or "",
                }
            )

    return valid, compounds, issues


def validate_compounds(
    xml_dir: Path,
    compound_entries: list[dict[str, str]],
) -> tuple[int, int, list[XmlValidationIssue], list[str], list[str]]:
    """Validate each compound XML against compound.xsd.

    Also checks for duplicate refids and missing compound files.

    Returns:
        (total, valid_count, issues, duplicate_refids, missing_files)
    """
    schema_path = xml_dir / "compound.xsd"
    if not schema_path.is_file():
        raise XmlValidationError(
            f"compound.xsd not found in {xml_dir}",
            file_path=str(schema_path),
        )

    try:
        schema_doc = etree.parse(str(schema_path))
        schema = etree.XMLSchema(schema_doc)
    except Exception as exc:
        raise XmlValidationError(
            f"Failed to load compound.xsd: {exc}",
            file_path=str(schema_path),
        ) from exc

    # Check for duplicate refids.
    refid_counts = Counter(e["refid"] for e in compound_entries)
    duplicate_refids = [rid for rid, count in refid_counts.items() if count > 1]

    issues: list[XmlValidationIssue] = []
    valid_count = 0
    missing_files: list[str] = []

    for entry in compound_entries:
        refid = entry["refid"]
        compound_path = xml_dir / f"{refid}.xml"

        if not compound_path.is_file():
            missing_files.append(refid)
            issues.append(
                XmlValidationIssue(
                    file=f"{refid}.xml",
                    line=None,
                    message="Compound XML file is missing",
                )
            )
            continue

        try:
            tree = _load_xml(compound_path)
            ok = schema.validate(tree)
            if ok:
                valid_count += 1
            else:
                for error in schema.error_log:
                    issues.append(
                        XmlValidationIssue(
                            file=f"{refid}.xml",
                            line=error.line,
                            message=error.message,
                        )
                    )
        except XmlValidationError as exc:
            issues.append(
                XmlValidationIssue(
                    file=f"{refid}.xml",
                    line=None,
                    message=str(exc),
                )
            )

    return len(compound_entries), valid_count, issues, duplicate_refids, missing_files


def validate_xml_output(xml_dir: Path) -> XmlValidationReport:
    """Run the full XML validation pipeline.

    Args:
        xml_dir: Path to the Doxygen XML output directory.

    Returns:
        ``XmlValidationReport`` with all results.

    Raises:
        XmlValidationError: If a critical error prevents validation.
    """
    # 1. Validate index.
    index_valid, compounds, index_issues = validate_index(xml_dir)

    # 2. Validate compounds.
    total, valid_count, compound_issues, dupes, missing = validate_compounds(
        xml_dir, compounds
    )

    all_issues = tuple(index_issues + compound_issues)

    return XmlValidationReport(
        index_valid=index_valid,
        compound_count=total,
        valid_compound_count=valid_count,
        issues=all_issues,
        duplicate_refids=tuple(dupes),
        missing_files=tuple(missing),
    )


def validate_member_refids(compound_entries: list[dict[str, str]]) -> tuple[str, ...]:
    """Check for duplicate member refids across all compounds.

    Doxygen member refids must be globally unique.

    Returns:
        Tuple of duplicate refids (empty if all unique).
    """
    # We need to parse each compound to collect member refids.
    all_member_refids: list[str] = []

    for entry in compound_entries:
        member_refids_raw: str | list[str] = entry.get("member_refids", [])
        if isinstance(member_refids_raw, str):
            all_member_refids.extend(member_refids_raw.split())
        elif isinstance(member_refids_raw, list):
            all_member_refids.extend(member_refids_raw)

    counts = Counter(all_member_refids)
    return tuple(rid for rid, count in counts.items() if count > 1)
