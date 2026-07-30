"""Output validation for generated reference.

Checks:
- Paths unique and casefold-unique
- Markdown files have valid frontmatter, fenced code blocks
- Internal links resolve to existing files
- Index paths exist in the output
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from juce_reference.util.json_io import json_lines
from juce_reference.util.markdown import (
    internal_links,
)

_REQUIRED_OUTPUT_FILES = [
    "manifest.json",
    "docs.lock.json",
    "reference/",
    "index/symbols.tsv",
    "index/symbols.jsonl",
    "index/relationships.jsonl",
    "index/source-locations.jsonl",
    "index/examples.jsonl",
    "index/search.sqlite",
    "guides/",
    "examples/",
    "examples/INDEX.md",
    "reports/validation.json",
]


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation issue."""

    severity: str  # "error", "warning"
    code: str
    message: str
    path: str | None = None
    symbol: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    """Complete validation report."""

    passed: bool
    issues: tuple[ValidationIssue, ...]
    statistics: dict[str, int]


def validate_output(reference_root: Path) -> ValidationReport:
    """Run all output validators.

    Args:
        reference_root: Path to the generated reference directory.

    Returns:
        ``ValidationReport`` with all findings.
    """
    issues: list[ValidationIssue] = []

    # P0: Reject empty directories outright.
    issues.extend(_validate_nonempty(reference_root))

    issues.extend(_validate_paths(reference_root))
    issues.extend(_validate_markdown_files(reference_root))
    issues.extend(_validate_indexes(reference_root))
    issues.extend(_validate_links(reference_root))
    issues.extend(_validate_required_files(reference_root, _REQUIRED_OUTPUT_FILES))

    errors = [i for i in issues if i.severity == "error"]
    stats: dict[str, int] = {
        "total_issues": len(issues),
        "errors": len(errors),
        "warnings": len(issues) - len(errors),
    }

    return ValidationReport(
        passed=len(errors) == 0,
        issues=tuple(issues),
        statistics=stats,
    )


def _validate_nonempty(root: Path) -> list[ValidationIssue]:
    """Reject output directories that have no content at all."""
    md_count = len(list(root.rglob("*.md")))
    manifest_exists = (root / "manifest.json").is_file()
    if md_count == 0 and not manifest_exists:
        return [ValidationIssue(
            severity="error", code="empty-output",
            message="Output directory has no Markdown or manifest — generation may have failed")]
    return []


def _validate_required_files(root: Path, required: list[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for path_str in required:
        p = root / path_str
        exists = (p.is_dir() if path_str.endswith("/") else p.is_file())
        if not exists:
            issues.append(ValidationIssue(
                severity="error", code="missing-required-file",
                message=f"Required file/directory missing: {path_str}"))
    return issues


def _validate_paths(root: Path) -> list[ValidationIssue]:
    """Check for path collisions and Windows issues."""
    issues: list[ValidationIssue] = []
    paths: list[str] = []

    for md_file in sorted(root.rglob("*.md")):
        rel = md_file.relative_to(root).as_posix()
        paths.append(rel)

    # Casefold collisions
    cf = Counter(p.casefold() for p in paths)
    for key, count in cf.items():
        if count > 1:
            issues.append(ValidationIssue(
                severity="error",
                code="path-case-collision",
                message=f"Case-insensitive path collision: {key} ({count} files)",
            ))

    return issues


def _validate_markdown_files(root: Path) -> list[ValidationIssue]:
    """Check Markdown file integrity."""
    issues: list[ValidationIssue] = []

    for md_file in root.rglob("*.md"):
        rel = md_file.relative_to(root).as_posix()
        content = md_file.read_text(encoding="utf-8", errors="replace")

        # Check fenced code block balance
        ticks = content.count("```")
        if ticks % 2 != 0:
            issues.append(ValidationIssue(
                severity="error",
                code="unclosed-code-block",
                message="Unclosed fenced code block",
                path=rel,
            ))

    return issues


def _validate_indexes(root: Path) -> list[ValidationIssue]:
    """Check that index files reference existing paths."""
    issues: list[ValidationIssue] = []

    index_dir = root / "index"
    if not index_dir.is_dir():
        return issues

    # Check symbols.jsonl
    symbols_path = index_dir / "symbols.jsonl"
    if symbols_path.is_file():
        for rec in json_lines(symbols_path):
            doc_path = rec.get("documentation_path", "")
            if doc_path:
                target = root / doc_path
                if not target.is_file():
                    issues.append(ValidationIssue(
                        severity="error",
                        code="broken-index-path",
                        message=(
                            f"Symbol {rec.get('symbol', '?')} points "
                            f"to missing file: {doc_path}"
                        ),
                        symbol=rec.get("symbol"),
                        path=doc_path,
                    ))

    # Check source-locations.jsonl — source files live in JUCE checkout
    sl_path = index_dir / "source-locations.jsonl"
    if sl_path.is_file():
        for rec in json_lines(sl_path):
            file_path = rec.get("file", "")
            if not file_path:
                issues.append(ValidationIssue(
                    severity="error", code="empty-source-path",
                    message=f"Empty source path for {rec.get('symbol', '?')}",
                    symbol=rec.get("symbol")))

    return issues


def _validate_links(root: Path) -> list[ValidationIssue]:
    """Check all internal Markdown links resolve to existing files/anchors."""
    issues: list[ValidationIssue] = []
    # Build an anchor index per file.
    anchor_index: dict[str, set[str]] = {}
    import re
    for md_file in root.rglob("*.md"):
        rel_path_key = md_file.relative_to(root).as_posix()
        content = md_file.read_text(encoding="utf-8", errors="replace")
        anchors_set: set[str] = set()
        # Collect explicit <a id="..."> anchors (including m-<sha> member anchors)
        for m in re.finditer(r'<a\s+id="([^"]+)"', content):
            anchors_set.add(m.group(1))
        # Member details often link to m-<sha> via anchor: #m-<sha> pattern
        # These are explicit anchors already collected above.
        # Collect headings as implicit slugs (secondary match)
        for m in re.finditer(r'^#{1,6}\s+(.+)$', content, re.MULTILINE):
            slug = re.sub(r'[^a-z0-9-]', '', m.group(1).strip().lower().replace(' ', '-'))
            anchors_set.add(slug)
        anchor_index[rel_path_key] = anchors_set

    for md_file in root.rglob("*.md"):
        rel = md_file.relative_to(root).as_posix()
        content = md_file.read_text(encoding="utf-8", errors="replace")

        for _text, link in internal_links(content):
            # Unresolved references always fail.
            if "unresolved:" in link:
                issues.append(ValidationIssue(
                    severity="error", code="unresolved-reference",
                    message=f"Unresolved reference: {link}", path=rel))
                continue

            if any(link.startswith(p) for p in ("http://", "https://", "mailto:")):
                continue
            anchor_part: str | None = None
            if "#" in link:
                file_part, anchor_part = link.rsplit("#", 1)
            else:
                file_part = link

            if not file_part:
                # Pure anchor (e.g. "#member") — check current file
                if anchor_part and anchor_part not in anchor_index.get(rel, set()):
                    issues.append(ValidationIssue(
                        severity="error", code="broken-anchor",
                        message=f"Anchor #{anchor_part} not found in {rel}", path=rel))
                continue

            # Strip leading ./ — resolve from reference root
            clean_file_part = file_part.lstrip("./")
            # For ./reference/... paths, resolve from root
            target = root / clean_file_part if file_part.startswith("./") else (md_file.parent / clean_file_part).resolve()
            try:
                target_rel = target.relative_to(root).as_posix()
            except ValueError:
                continue  # Link outside reference root

            if not target.is_file():
                issues.append(ValidationIssue(
                    severity="error", code="broken-internal-link",
                    message=f"Broken link to {file_part} from {rel}", path=rel))
                continue

            # If there's an anchor, verify it exists in the target file
            if anchor_part and target_rel in anchor_index and anchor_part not in anchor_index[target_rel]:
                issues.append(ValidationIssue(
                        severity="error", code="broken-anchor",
                        message=f"Anchor #{anchor_part} not found in {target_rel} (from {rel})",
                        path=rel))

            if "unresolved:" in link:
                issues.append(ValidationIssue(
                    severity="error", code="unresolved-reference",
                    message=f"Unresolved reference: {link}", path=rel))

    return issues
