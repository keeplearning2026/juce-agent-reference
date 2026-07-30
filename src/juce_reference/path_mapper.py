"""Deterministic path assignment for every compound and member.

Assigns output filesystem paths, detects case-insensitive collisions on
Windows, and produces stable member anchors from Doxygen refids.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from juce_reference.model import Compound
from juce_reference.util.hashing import short_id
from juce_reference.util.paths import sanitise_name


@dataclass(frozen=True)
class OutputTarget:
    """Where a compound or member is rendered."""

    refid: str
    path: str  # relative POSIX path to the Markdown file
    anchor: str | None = None  # member anchor within the page (None for compounds)


@dataclass(frozen=True)
class PathMap:
    """The complete path assignment for a generation run."""

    compounds: Mapping[str, OutputTarget]
    members: Mapping[str, OutputTarget]


def member_anchor(refid: str) -> str:
    """Generate a stable, deterministic anchor for a member.

    Format: ``m-<sha256(refid) first 10 hex chars>``

    This ensures:
    - overloaded methods get different anchors
    - template and operator names never cause invalid anchors
    - anchors are the same across platforms and runs
    """
    return f"m-{short_id(refid, 10)}"


def build_path_map(compounds: list[Compound]) -> PathMap:
    """Assign filesystem paths to every compound and member.

    Returns a ``PathMap`` with all assignments.
    """
    compound_targets: dict[str, OutputTarget] = {}
    member_targets: dict[str, OutputTarget] = {}

    # First pass: allocate naive paths.
    for c in compounds:
        cpath = _compound_path(c)
        compound_targets[c.refid] = OutputTarget(refid=c.refid, path=cpath, anchor=None)

        for m in c.members:
            anchor = member_anchor(m.refid)
            member_targets[m.refid] = OutputTarget(
                refid=m.refid, path=cpath, anchor=anchor
            )

    # Second pass: detect case-insensitive collisions and disambiguate.
    _resolve_collisions(compound_targets)

    return PathMap(compounds=compound_targets, members=member_targets)


def _compound_path(c: Compound) -> str:
    """Compute the relative POSIX path for a compound."""
    kind = c.kind.lower()

    if kind in ("group", "module"):
        # JUCE module: the compound name is the module name (juce_audio_processors etc.)
        name = sanitise_name(c.name)
        return f"reference/modules/{name}.md"

    if kind == "namespace":
        # Strip leading/trailing "::"
        name = c.name.replace("::", "/").strip("/")
        safe = "/".join(sanitise_name(seg) for seg in name.split("/"))
        return f"reference/namespaces/{safe}.md"

    if kind == "file":
        name = sanitise_name(c.name).replace("\\", "_").replace("/", "_")
        return f"reference/files/{name}.md"

    if kind == "page":
        name = sanitise_name(c.name)
        return f"reference/pages/{name}.md"

    # Default: type (class, struct, union, interface)
    name = c.name.replace("::", "/").strip("/")
    safe = "/".join(sanitise_name(seg) for seg in name.split("/"))
    return f"reference/types/{safe}.md"


def _resolve_collisions(targets: dict[str, OutputTarget]) -> None:
    """Detect and resolve case-insensitive path collisions.

    On Windows, ``Foo.md`` and ``foo.md`` are the same file.  We use
    ``path.as_posix().casefold()`` as the collision key and append a
    short hash when conflicts are detected.
    """
    by_key: dict[str, list[str]] = defaultdict(list)

    for refid, target in targets.items():
        key = target.path.casefold()
        by_key[key].append(refid)

    for _key, refids in by_key.items():
        if len(refids) <= 1:
            continue
        # All but the first get a disambiguator.
        for i, refid in enumerate(refids):
            if i == 0:
                continue
            target = targets[refid]
            hash_tag = short_id(refid, 8)
            path = target.path
            # Insert hash before .md
            if path.endswith(".md"):
                new_path = path[:-3] + f"--{hash_tag}.md"
            else:
                new_path = f"{path}--{hash_tag}"
            targets[refid] = OutputTarget(
                refid=target.refid, path=new_path, anchor=target.anchor
            )
