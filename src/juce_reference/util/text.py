"""Small text utilities."""

from __future__ import annotations

import re

# Split CamelCase / PascalCase into space-separated tokens.
_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def camel_to_words(name: str) -> str:
    """Convert a CamelCase identifier to a space-separated phrase."""
    return re.sub(r"\s+", " ", _CAMEL_SPLIT_RE.sub(" ", name)).strip()


def normalise_whitespace(text: str) -> str:
    """Collapse all whitespace sequences to a single space."""
    return " ".join(text.split())


def is_fully_qualified(name: str) -> bool:
    """Return True if *name* looks like a qualified C++ symbol (contains ``::``)."""
    return "::" in name
