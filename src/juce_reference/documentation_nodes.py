"""Canonical documentation node types for the Intermediate Representation.

All documentation content from Doxygen XML is converted into a tree of
these immutable nodes.  No `lxml` objects ever cross this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DocNode:
    """Base for all documentation nodes in the canonical IR."""


class EntityDisposition(StrEnum):
    """Records how an entity was handled during generation."""

    RENDERED = "rendered"
    INDEXED_ONLY = "indexed-only"
    SKIPPED_WITH_REASON = "skipped-with-reason"


# -- Leaf nodes ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Text(DocNode):
    """Plain text content."""

    value: str


@dataclass(frozen=True, slots=True)
class InlineCode(DocNode):
    """Inline ``code`` fragment."""

    value: str


@dataclass(frozen=True, slots=True)
class CodeBlock(DocNode):
    """Fenced code block from documentation (NOT source listing)."""

    code: str
    language: str | None = None


@dataclass(frozen=True, slots=True)
class LineBreak(DocNode):
    """Explicit line break."""


@dataclass(frozen=True, slots=True)
class Formula(DocNode):
    """LaTeX formula."""

    value: str
    display: bool = False


@dataclass(frozen=True, slots=True)
class ImageNode(DocNode):
    """Image reference."""

    name: str
    caption: tuple[DocNode, ...] = ()
    external_url: str | None = None


# -- Container nodes ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Paragraph(DocNode):
    """Paragraph block."""

    children: tuple[DocNode, ...] = ()


@dataclass(frozen=True, slots=True)
class Section(DocNode):
    """Section heading with body content."""

    level: int
    title: tuple[DocNode, ...] = ()
    children: tuple[DocNode, ...] = ()


@dataclass(frozen=True, slots=True)
class UnorderedList(DocNode):
    """Bullet list."""

    items: tuple[DocNode, ...] = ()  # Each item is typically a Paragraph or Text.


@dataclass(frozen=True, slots=True)
class OrderedList(DocNode):
    """Numbered list."""

    items: tuple[DocNode, ...] = ()


@dataclass(frozen=True, slots=True)
class ListItem(DocNode):
    """Single item within an (un)ordered list."""

    children: tuple[DocNode, ...] = ()


# -- Table --------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TableCell(DocNode):
    """A single table cell."""

    children: tuple[DocNode, ...] = ()


@dataclass(frozen=True, slots=True)
class TableRow(DocNode):
    """A table row."""

    cells: tuple[TableCell, ...] = ()
    header: bool = False


@dataclass(frozen=True, slots=True)
class Table(DocNode):
    """A complete table."""

    rows: tuple[TableRow, ...] = ()


# -- Semantic admonitions -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class Note(DocNode):
    """@note block."""

    children: tuple[DocNode, ...] = ()


@dataclass(frozen=True, slots=True)
class WarningNode(DocNode):
    """@warning block."""

    children: tuple[DocNode, ...] = ()


@dataclass(frozen=True, slots=True)
class DeprecatedNode(DocNode):
    """@deprecated block."""

    children: tuple[DocNode, ...] = ()


# -- Reference -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReferenceNode(DocNode):
    """A cross-reference (internal refid or external URL)."""

    refid: str | None = None
    external_url: str | None = None
    kind: str | None = None
    children: tuple[DocNode, ...] = ()


# -- Parameter lists ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ParameterEntry(DocNode):
    """A single entry in a param / return / throws list."""

    name: str = ""
    children: tuple[DocNode, ...] = ()


@dataclass(frozen=True, slots=True)
class ParameterList(DocNode):
    """A group of parameter descriptions (param, return, throws, etc.)."""

    kind: str = ""  # "param", "return", "throws", "retval", …
    entries: tuple[ParameterEntry, ...] = ()


# -- Bold / emphasis -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Bold(DocNode):
    """Bold / strong text."""

    children: tuple[DocNode, ...] = ()


@dataclass(frozen=True, slots=True)
class Emphasis(DocNode):
    """Italic / emphasized text."""

    children: tuple[DocNode, ...] = ()


@dataclass(frozen=True, slots=True)
class DocTitle(DocNode):
    """Document-level title."""

    children: tuple[DocNode, ...] = ()


@dataclass(frozen=True, slots=True)
class Preformatted(DocNode):
    """Preformatted text block (from @verbatim, etc.)."""

    text: str = ""
