"""Source location indexer using Doxygen-provided file/line data.

Never guesses definition locations — returns ``None`` when Doxygen
doesn't provide reliable body location information.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_source_locations_jsonl(jsonl_path: Path, juce_root: Path) -> dict[str, Any]:
    """Validate all source file paths in a source-locations.jsonl file.

    Args:
        jsonl_path: Path to ``source-locations.jsonl``.
        juce_root: Root of JUCE checkout (for path resolution).

    Returns:
        A dict with ``valid`` count, ``missing`` list, and ``total``.
    """
    from juce_reference.util.json_io import json_lines

    records = json_lines(jsonl_path)
    total = len(records)
    valid = 0
    missing: list[str] = []

    for rec in records:
        file_path = rec.get("file", "")
        if not file_path:
            missing.append(f"{rec.get('symbol', '?')}:empty_file")
            continue

        full_path = juce_root / file_path
        if full_path.is_file():
            valid += 1
        else:
            missing.append(f"{rec.get('symbol', '?')}:{file_path}")

    return {"total": total, "valid": valid, "missing": missing}


def _resolve_definition(member: Any) -> str | None:
    """Check if a definition location is available — do not guess."""
    # In V1, we only report definitions that Doxygen provides explicitly.
    # body_file and body_start come from the <location> element.
    if hasattr(member, "location") and member.location and member.location.body_file:
        return str(member.location.body_file)
    return None
