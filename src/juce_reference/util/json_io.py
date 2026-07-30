"""Safe JSON I/O with atomic writes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    """Read and parse a JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any, *, indent: int = 2, sort_keys: bool = True) -> None:
    """Atomically write *data* as JSON."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=indent, ensure_ascii=False, sort_keys=sort_keys),
        encoding="utf-8",
    )
    tmp.replace(path)


def write_json_nosort(path: Path, data: Any, *, indent: int = 2) -> None:
    """Atomically write *data* as JSON, preserving key order."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=indent, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(path)


def json_lines(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dicts."""
    lines: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            lines.append(json.loads(stripped))
    return lines
