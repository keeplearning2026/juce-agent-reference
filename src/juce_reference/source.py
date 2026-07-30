"""JUCE checkout inspection and validation.

Reads the Git state of a local JUCE checkout without modifying it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from juce_reference.errors import JuceSourceError
from juce_reference.util.command import run


@dataclass(frozen=True)
class JuceSource:
    """Validated snapshot of a JUCE checkout."""

    root: Path
    git_root: Path
    commit: str
    dirty: bool
    modules_dir: Path
    docs_dir: Path
    doxygen_dir: Path
    doxygen_file: Path
    examples_dir: Path | None = None
    extras_dir: Path | None = None


def _git(args: list[str], cwd: Path, timeout: int = 30) -> str:
    """Run a git command and return stripped stdout on success."""
    result = run(["git"] + args, cwd=cwd, timeout=timeout)
    if not result.ok:
        raise JuceSourceError(
            f"Git command failed: git {' '.join(args)}\n{result.stderr}",
            command="git",
            file_path=str(cwd),
        )
    return result.stdout.strip()


def validate_juce_source(root: Path, *, allow_dirty: bool = False) -> JuceSource:
    """Validate a JUCE checkout at *root* and return an immutable snapshot.

    Args:
        root: Path to the JUCE repository root.
        allow_dirty: If False, raise when the working tree is dirty.

    Returns:
        A fully-populated `JuceSource`.

    Raises:
        JuceSourceError: If the checkout is missing, not a git repo, or dirty.
    """
    root = root.resolve()

    if not root.is_dir():
        raise JuceSourceError(f"JUCE root does not exist: {root}", file_path=str(root))

    modules_dir = root / "modules"
    if not modules_dir.is_dir():
        raise JuceSourceError(
            f"JUCE modules/ directory not found at {modules_dir}",
            file_path=str(modules_dir),
        )

    # Determine git root.
    git_root_str = _git(["rev-parse", "--show-toplevel"], cwd=root)
    git_root = Path(git_root_str).resolve()

    commit = _git(["rev-parse", "HEAD"], cwd=root)
    if len(commit) != 40:
        raise JuceSourceError(
            f"Expected 40-char SHA, got '{commit}'", command="git rev-parse HEAD"
        )

    status = _git(["status", "--porcelain=v1", "--untracked-files=normal"], cwd=root)
    dirty = len(status) > 0

    if dirty and not allow_dirty:
        raise JuceSourceError(
            "JUCE working tree is dirty. Commit changes or use --allow-dirty.",
            file_path=str(root),
        )

    doxygen_dir = root / "docs" / "doxygen"
    doxygen_file = doxygen_dir / "Doxyfile"
    if not doxygen_file.is_file():
        raise JuceSourceError(
            f"JUCE Doxyfile not found: {doxygen_file}",
            file_path=str(doxygen_file),
        )

    docs_dir = root / "docs"
    examples_dir_raw = root / "examples"
    examples_dir: Path | None = examples_dir_raw if examples_dir_raw.is_dir() else None

    extras_dir_raw = root / "extras"
    extras_dir: Path | None = extras_dir_raw if extras_dir_raw.is_dir() else None

    return JuceSource(
        root=root,
        git_root=git_root,
        commit=commit,
        dirty=dirty,
        modules_dir=modules_dir,
        docs_dir=docs_dir,
        doxygen_dir=doxygen_dir,
        doxygen_file=doxygen_file,
        examples_dir=examples_dir,
        extras_dir=extras_dir,
    )
