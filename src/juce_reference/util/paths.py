"""Deterministic path helpers."""

from __future__ import annotations

import unicodedata
from pathlib import Path

# Characters not allowed in Windows filenames.
_WINDOWS_ILLEGAL = frozenset(r'<>:"/\|?*')
_WINDOWS_RESERVED = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
)


def posix(path: Path) -> str:
    """Return a normalised POSIX representation of *path*."""
    return path.as_posix()


def relative_posix(path: Path, root: Path) -> str:
    """Return *path* relative to *root* as a POSIX string."""
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        rel = path
    return rel.as_posix()


def sanitise_name(name: str) -> str:
    """Replace characters that are illegal in Windows filenames."""
    sanitised: list[str] = []
    for ch in name:
        if ch in _WINDOWS_ILLEGAL or ord(ch) < 32:
            sanitised.append("_")
        else:
            sanitised.append(ch)
    result = "".join(sanitised).strip()
    if not result:
        result = "_unknown_"
    if result.upper() in _WINDOWS_RESERVED:
        result = f"_{result}_"
    # Normalise unicode to avoid composed/decomposed conflicts.
    result = unicodedata.normalize("NFC", result)
    return result
