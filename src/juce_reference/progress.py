"""Progress persistence for unattended goal execution.

Writes ``.agent/progress.json`` atomically so a resumed Agent can pick up
from the last verified state.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_DEFAULT_PROGRESS: dict[str, Any] = {
    "schema_version": 1,
    "goal": "Complete JUCE Agent Reference V1",
    "current_phase": 0,
    "completed_phases": [],
    "last_verified_commit": None,
    "last_successful_command": None,
    "current_failure": None,
    "next_action": "Initialize repository",
    "completed": False,
}


def progress_path(repo_root: Path) -> Path:
    return repo_root / ".agent" / "progress.json"


def read_progress(repo_root: Path) -> dict[str, Any]:
    """Read the current progress file, or return defaults."""
    path = progress_path(repo_root)
    if not path.exists():
        return dict(_DEFAULT_PROGRESS)
    try:
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT_PROGRESS)


def write_progress(repo_root: Path, data: dict[str, Any]) -> None:
    """Atomically write *data* to ``.agent/progress.json``."""
    path = progress_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def update_progress(repo_root: Path, **kwargs: Any) -> dict[str, Any]:
    """Read, update with *kwargs*, and write the progress file.

    Returns the updated data dict.
    """
    data = read_progress(repo_root)
    data.update(kwargs)
    write_progress(repo_root, data)
    return data
