"""Content hashing helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_hex(data: bytes | str) -> str:
    """Return hex SHA-256 of *data*."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    """Return hex SHA-256 of the file at *path*."""
    return sha256_hex(path.read_bytes())


def short_id(refid: str, n: int = 10) -> str:
    """Return the first *n* hex chars of sha256(refid)."""
    return sha256_hex(refid)[:n]
