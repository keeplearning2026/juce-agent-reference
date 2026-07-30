"""Lightweight Markdown utilities."""

from __future__ import annotations

import re

# Match an ATX heading: `## Title`  (1–6 leading `#`).
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

# Match an explicit anchor / link target: `<a id="..."></a>`.
_ANCHOR_RE = re.compile(r'<a\s+id="([^"]+)"\s*></a>')

# Match an inline Markdown link: `[text](url)`.
_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract YAML frontmatter (``---`` … ``---``) from Markdown text.

    Returns ``({}, original_text)`` when there is no frontmatter.
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    front = parts[1].strip()
    body = parts[2].lstrip("\n")
    data: dict[str, str] = {}
    for line in front.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip().strip('"').strip("'")
    return data, body


def collect_headings(content: str) -> list[tuple[int, str]]:
    """Return ``[(level, title_text), ...]`` for every ATX heading."""
    return [(len(m.group(1)), m.group(2).strip()) for m in _HEADING_RE.finditer(content)]


def collect_anchors(content: str) -> list[str]:
    """Return explicit anchor ids defined in the Markdown."""
    return [m.group(1) for m in _ANCHOR_RE.finditer(content)]


def extract_links(content: str) -> list[tuple[str, str]]:
    """Return ``[(text, url), ...]`` for every Markdown link."""
    return [(m.group(1), m.group(2)) for m in _LINK_RE.finditer(content)]


def internal_links(content: str) -> list[tuple[str, str]]:
    """Extract links whose target does NOT look like an external URL."""
    links = extract_links(content)
    return [(t, u) for t, u in links if not u.startswith(("http://", "https://", "mailto:"))]
