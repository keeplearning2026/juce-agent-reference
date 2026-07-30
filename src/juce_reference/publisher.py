"""Atomic release publisher.

Publishes generated references atomically, ensuring:
- Dirty builds cannot replace stable releases
- Same-commit content must be identical
- Failed publishes do not corrupt the current release
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from juce_reference.errors import PublishError


@dataclass(frozen=True)
class PublishResult:
    """Result of a publish operation."""

    published: bool
    release_path: Path
    reused: bool = False


def publish_release(
    candidate_dir: Path,
    output_root: Path,
    juce_commit: str,
    *,
    allow_dirty: bool = False,
    release: bool = True,
) -> PublishResult:
    """Atomically publish a generated reference.

    Args:
        candidate_dir: Directory containing the validated generated output.
        output_root: Root output directory (e.g. ``juce-reference/``).
        juce_commit: Full JUCE commit SHA.
        allow_dirty: If False, refuses to publish dirty builds as releases.
        release: If False, publishes to a temp location only.

    Returns:
        ``PublishResult`` describing the outcome.

    Raises:
        PublishError: If validation fails or the release is inconsistent.
    """
    if not candidate_dir.is_dir():
        raise PublishError(
            f"Candidate directory does not exist: {candidate_dir}",
            file_path=str(candidate_dir),
        )

    if not release:
        return PublishResult(published=False, release_path=candidate_dir)

    # Dirty builds cannot publish as official releases
    if not allow_dirty:
        # Check if the candidate manifest indicates dirty source
        manifest_path = candidate_dir / "manifest.json"
        if manifest_path.is_file():
            import json
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("juce_dirty"):
                raise PublishError(
                    "Cannot publish a dirty JUCE checkout as a release",
                    suggestion="Use --allow-dirty or commit JUCE changes first")

    releases_dir = output_root / "releases"
    release_dir = releases_dir / juce_commit

    # If this exact commit already has a release, content must match.
    if release_dir.is_dir():
        if _directories_equal(candidate_dir, release_dir):
            return PublishResult(published=True, release_path=release_dir, reused=True)
        raise PublishError(
            f"Release for commit {juce_commit} exists with different content",
            suggestion="This should not happen — investigate determinism",
        )

    # Ensure parent exists
    releases_dir.mkdir(parents=True, exist_ok=True)

    # Write to temp first, then atomically rename.
    tmp_dir = releases_dir / f".tmp-{juce_commit}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    _copy_tree(candidate_dir, tmp_dir)

    try:
        os.replace(tmp_dir, release_dir)
    except OSError:
        # On Windows, os.replace across drives may fail; fall back to rename.
        tmp_dir.rename(release_dir)

    # Update current.json atomically.
    _write_current(output_root, juce_commit)

    return PublishResult(published=True, release_path=release_dir)


def _write_current(output_root: Path, commit: str) -> None:
    """Atomically update ``current.json``."""
    current_data = {
        "commit": commit,
        "path": f"releases/{commit}",
    }
    current_path = output_root / "current.json"
    tmp = output_root / "current.json.tmp"
    tmp.write_text(
        json.dumps(current_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(tmp, current_path)


def _copy_tree(src: Path, dst: Path) -> None:
    """Copy a directory tree."""
    shutil.copytree(str(src), str(dst), symlinks=False)


def _directories_equal(a: Path, b: Path) -> bool:
    """Check if two directories contain the same files with the same content.

    Uses file listing and size comparison for efficiency.
    """
    a_files = sorted(p.relative_to(a).as_posix() for p in a.rglob("*") if p.is_file())
    b_files = sorted(p.relative_to(b).as_posix() for p in b.rglob("*") if p.is_file())

    if a_files != b_files:
        return False

    for f in a_files:
        fa = a / f
        fb = b / f
        if fa.stat().st_size != fb.stat().st_size:
            return False
        if fa.read_bytes() != fb.read_bytes():
            return False

    return True
