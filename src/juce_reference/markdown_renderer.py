"""Canonical IR → Markdown renderer.

Produces deterministic, UTF-8, LF-terminated Markdown with YAML frontmatter
and stable member anchors.  All internal links go through the ``PathMap``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from juce_reference.documentation_nodes import (
    Bold,
    CodeBlock,
    DeprecatedNode,
    DocNode,
    DocTitle,
    Emphasis,
    Formula,
    ImageNode,
    InlineCode,
    LineBreak,
    ListItem,
    Note,
    OrderedList,
    Paragraph,
    ParameterEntry,
    ParameterList,
    Preformatted,
    ReferenceNode,
    Section,
    Table,
    TableCell,
    Text,
    UnorderedList,
    WarningNode,
)
from juce_reference.model import (
    Compound,
    Member,
    Reference,
    SourceLocation,
)
from juce_reference.path_mapper import PathMap


@dataclass(frozen=True)
class RenderedDocument:
    """A rendered Markdown document ready to write to disk."""

    path: str
    content: str
    symbols: tuple[str, ...]
    anchors: tuple[str, ...]


def render_compound(
    compound: Compound,
    path_map: PathMap,
    *,
    juce_commit: str = "",
) -> RenderedDocument:
    """Render a single compound into a Markdown document.

    Args:
        compound: The parsed compound from the IR.
        path_map: The complete path map for the generation run.
        juce_commit: Full JUCE SHA for frontmatter metadata.

    Returns:
        ``RenderedDocument`` ready to write.
    """
    target = path_map.compounds.get(compound.refid)
    if target is None:
        raise ValueError(f"No path target for compound {compound.refid}")

    global _current_doc_path
    _current_doc_path = target.path

    lines: list[str] = []
    symbols: list[str] = [compound.qualified_name]
    anchors: list[str] = []

    # --- Frontmatter ---
    lines.append("---")
    lines.append(f"symbol: {_escape_yaml(compound.qualified_name)}")
    lines.append(f"short_name: {_escape_yaml(_short_name(compound.name))}")
    lines.append(f"kind: {compound.kind}")
    if compound.module:
        lines.append(f"module: {_escape_yaml(compound.module)}")
    if compound.location:
        lines.append(f"header: {_escape_yaml(compound.location.file)}")
    lines.append(f"doxygen_id: {compound.refid}")
    if juce_commit:
        lines.append(f"juce_commit: {juce_commit}")
    lines.append(f"documented: {str(compound.documented).lower()}")
    lines.append("---")
    lines.append("")

    # --- Title ---
    title = compound.title or compound.qualified_name
    lines.append(f"# {title}")
    lines.append("")

    # --- Brief ---
    if compound.brief:
        lines.append(_render_nodes(compound.brief, path_map))
        lines.append("")

    # --- Quick Reference ---
    if compound.location:
        loc = compound.location
        lines.append("**Header:** " + _render_location_file(loc))
        if loc.line:
            lines.append(f"<br>**Declaration:** line {loc.line}")
        lines.append("")

    # --- Inheritance ---
    if compound.bases:
        lines.append("## Inheritance")
        lines.append("")
        for base in compound.bases:
            base_path = _ref_to_link(base, path_map)
            if base_path:
                lines.append(f"- Inherits from [{base.text}]({base_path})")
            else:
                lines.append(f"- Inherits from {base.text}")
        lines.append("")

    if compound.derived:
        lines.append("**Derived classes:**")
        for d in compound.derived:
            d_path = _ref_to_link(d, path_map)
            if d_path:
                lines.append(f"- [{d.text}]({d_path})")
            else:
                lines.append(f"- {d.text}")
        lines.append("")

    # --- Detailed description ---
    if compound.details:
        lines.append("## Detailed Description")
        lines.append("")
        lines.append(_render_nodes(compound.details, path_map))
        lines.append("")

    # --- Member index ---
    if compound.sections:
        for section in compound.sections:
            section_members = [m for m in compound.members if m.refid in section.member_refids]
            if not section_members:
                continue
            heading = section.title or _section_heading(section.kind)
            lines.append(f"## {heading}")
            lines.append("")
            lines.append("| Name | Description |")
            lines.append("|------|-------------|")
            for member in section_members:
                mt = path_map.members.get(member.refid)
                anchor = mt.anchor if mt else ""
                anchor_link = f"#{anchor}" if anchor else ""
                brief_text = _brief_to_text(member.brief)
                lines.append(
                    f"| [{member.name}]({anchor_link}) "
                    f"| {_escape_table(brief_text)} |"
                )
            lines.append("")

    # --- Member details ---
    if compound.members:
        lines.append("## Member Details")
        lines.append("")
        for member in compound.members:
            lines.extend(_render_member_detail(member, path_map))
            lines.append("")

    # --- Source ---
    if compound.location:
        lines.append("## Source")
        lines.append("")
        loc = compound.location
        lines.append(f"- **File:** {_render_location_file(loc)}")
        if loc.line:
            lines.append(f"- **Line:** {loc.line}")
        if loc.body_file:
            lines.append(f"- **Definition:** {loc.body_file}")
            if loc.body_start:
                lines.append(f"  lines {loc.body_start}–{loc.body_end or '?'}")
        lines.append("")

    content = "\n".join(lines) + "\n"
    return RenderedDocument(
        path=target.path,
        content=content,
        symbols=tuple(symbols),
        anchors=tuple(anchors),
    )


# ---------------------------------------------------------------------------
# DocNode → Markdown rendering
# ---------------------------------------------------------------------------


def _render_nodes(nodes: Sequence[DocNode], path_map: PathMap) -> str:
    """Render a sequence of DocNodes to Markdown."""
    parts: list[str] = []
    for node in nodes:
        parts.append(_render_node(node, path_map))
    return "\n\n".join(p for p in parts if p)


def _render_node(node: DocNode, path_map: PathMap) -> str:
    """Dispatch a single DocNode to its Markdown representation."""
    if isinstance(node, Paragraph):
        children = [_render_inline(n, path_map) for n in node.children]
        text = " ".join(c for c in children if c)
        return text if text else ""

    if isinstance(node, Text):
        return node.value

    if isinstance(node, InlineCode):
        return f"`{node.value}`"

    if isinstance(node, CodeBlock):
        lang = node.language or "cpp"
        return f"```{lang}\n{node.code}\n```"

    if isinstance(node, Section):
        prefix = "#" * node.level
        title = " ".join(_render_inline(n, path_map) for n in node.title)
        body = _render_nodes(node.children, path_map)
        return f"{prefix} {title}\n\n{body}"

    if isinstance(node, Note):
        body = _render_nodes(node.children, path_map)
        return f"> **Note:** {body}"

    if isinstance(node, WarningNode):
        body = _render_nodes(node.children, path_map)
        return f"> **Warning:** {body}"

    if isinstance(node, DeprecatedNode):
        body = _render_nodes(node.children, path_map)
        return f"> **Deprecated:** {body}"

    if isinstance(node, ReferenceNode):
        text = " ".join(_render_inline(n, path_map) for n in node.children)
        if node.external_url:
            return f"[{text}]({node.external_url})"
        if node.refid:
            # Look up the refid in path_map
            target = path_map.compounds.get(node.refid) or path_map.members.get(node.refid)
            if target:
                anchor = f"#{target.anchor}" if target.anchor else ""
                # Make the link relative within the output tree.
                rel_path = _relative_link(target.path, path_map, current_refid=None)
                return f"[{text}]({rel_path}{anchor})"
            # Fallback: use text as-is with a marker
            return f"[{text}][unresolved:{node.refid}]"
        return text or node.refid or ""

    if isinstance(node, UnorderedList):
        items = [_render_node(li, path_map) for li in node.items]
        return "\n".join(f"- {it}" for it in items if it)

    if isinstance(node, OrderedList):
        items = [_render_node(li, path_map) for li in node.items]
        return "\n".join(f"{i + 1}. {it}" for i, it in enumerate(items) if it)

    if isinstance(node, ListItem):
        return _render_nodes(node.children, path_map)

    if isinstance(node, Table):
        rows: list[str] = []
        for i, row in enumerate(node.rows):
            cells = [_render_node(cell, path_map) for cell in row.cells]
            rows.append("| " + " | ".join(cells) + " |")
            if i == 0:
                rows.append("|" + "|".join("---" for _ in row.cells) + "|")
        return "\n".join(rows)

    if isinstance(node, TableCell):
        return _render_nodes(node.children, path_map)

    if isinstance(node, ParameterList):
        parts: list[str] = [f"**{node.kind.title()}:**"]
        for entry in node.entries:
            label = f"`{entry.name}`" if entry.name else ""
            desc = _render_nodes(entry.children, path_map)
            if label:
                parts.append(f"- {label} — {desc}")
            else:
                parts.append(f"- {desc}")
        return "\n".join(parts)

    if isinstance(node, ParameterEntry):
        return _render_nodes(node.children, path_map)

    if isinstance(node, Bold):
        text = " ".join(_render_inline(n, path_map) for n in node.children)
        return f"**{text}**"

    if isinstance(node, Emphasis):
        text = " ".join(_render_inline(n, path_map) for n in node.children)
        return f"*{text}*"

    if isinstance(node, DocTitle):
        text = " ".join(_render_inline(n, path_map) for n in node.children)
        return f"## {text}"

    if isinstance(node, Formula):
        if node.display:
            return f"$$\n{node.value}\n$$"
        return f"${node.value}$"

    if isinstance(node, ImageNode):
        url = node.external_url or node.name
        caption = _render_nodes(node.caption, path_map)
        return f"![{caption}]({url})"

    if isinstance(node, LineBreak):
        return "<br>"

    if isinstance(node, Preformatted):
        return f"```\n{node.text}\n```"

    # Fallback
    return ""


def _render_inline(node: DocNode, path_map: PathMap) -> str:
    """Render a single inline DocNode to Markdown (no block spacing)."""
    if isinstance(node, Text):
        return node.value
    if isinstance(node, InlineCode):
        return f"`{node.value}`"
    if isinstance(node, Bold):
        return "**" + " ".join(_render_inline(n, path_map) for n in node.children) + "**"
    if isinstance(node, Emphasis):
        return "*" + " ".join(_render_inline(n, path_map) for n in node.children) + "*"
    if isinstance(node, ReferenceNode):
        text = " ".join(_render_inline(n, path_map) for n in node.children)
        if node.external_url:
            return f"[{text}]({node.external_url})"
        if node.refid:
            target = path_map.compounds.get(node.refid) or path_map.members.get(node.refid)
            if target:
                anchor = f"#{target.anchor}" if target.anchor else ""
                rel_path = _relative_link(target.path, path_map, current_refid=None)
                return f"[{text}]({rel_path}{anchor})"
            return f"[{text}][unresolved:{node.refid}]"
        return text or node.refid or ""
    if isinstance(node, LineBreak):
        return "<br>"
    if isinstance(node, Formula):
        return f"${node.value}$"
    if isinstance(node, DocNode):
        # Generic fallback: handle embedded Paragraphs, etc.
        return _render_node(node, path_map)
    return ""


def _render_member_detail(member: Member, path_map: PathMap) -> list[str]:
    """Render the detailed section for one member."""
    lines: list[str] = []
    mt = path_map.members.get(member.refid)
    anchor = mt.anchor if mt else ""
    if anchor:
        lines.append(f'<a id="{anchor}"></a>')
        lines.append("")

    # Signature
    qualifiers: list[str] = []
    if member.static:
        qualifiers.append("static")
    if member.virtual_kind == "pure-virtual":
        qualifiers.append("pure virtual")
    elif member.virtual_kind == "virtual":
        qualifiers.append("virtual")
    if member.const:
        qualifiers.append("const")
    if member.explicit:
        qualifiers.append("explicit")

    lines.append(f"### {member.name}")
    lines.append("")

    if qualifiers:
        lines.append(f"*{' '.join(qualifiers)}*")
        lines.append("")

    if member.signature:
        lines.append(f"```cpp\n{member.signature}\n```")
        lines.append("")

    # Brief
    if member.brief:
        lines.append(_render_nodes(member.brief, path_map))
        lines.append("")

    # Parameters
    if member.parameters:
        lines.append("**Parameters:**")
        lines.append("")
        lines.append("| Name | Type | Description |")
        lines.append("|------|------|-------------|")
        for p in member.parameters:
            ptype = " ".join(_render_inline(n, path_map) for n in p.type_nodes)
            pdesc = _render_nodes(p.description, path_map)
            lines.append(f"| {p.name or ''} | {_escape_table(ptype)} | {_escape_table(pdesc)} |")
        lines.append("")

    # Template parameters
    if member.template_parameters:
        lines.append("**Template Parameters:**")
        for tp in member.template_parameters:
            tptype = " ".join(_render_inline(n, path_map) for n in tp.type_nodes)
            lines.append(f"- `{tp.name or ''}` — {tptype}")
        lines.append("")

    # Details
    if member.details:
        lines.append(_render_nodes(member.details, path_map))
        lines.append("")

    # Location
    if member.location:
        loc = member.location
        lines.append(f"*Declared in {_render_location_file(loc)}*")
        if loc.line:
            lines.append(f"  at line {loc.line}")
        lines.append("")

    if member.deprecated:
        lines.append("> **Deprecated**")
        lines.append("")

    return lines


# ---------------------------------------------------------------------------
# Path resolution helpers
# ---------------------------------------------------------------------------

_current_path: str | None = None  # module-level context for relative links


# Module-level context set by render_compound for relative link computation.
_current_doc_path: str = ""


def _relative_link(
    target_path: str, path_map: PathMap, current_refid: str | None,
    current_path: str = "",
) -> str:
    """Compute a relative POSIX link from one output file to another."""
    import os.path
    from_path = current_path or _current_doc_path
    if not from_path and current_refid:
        ct = path_map.compounds.get(current_refid)
        if ct is not None:
            from_path = ct.path
    if from_path and os.path.dirname(from_path):
        try:
            return os.path.relpath(target_path, os.path.dirname(from_path)).replace("\\", "/")
        except ValueError:
            pass
    return f"{target_path}"


def _ref_to_link(ref: Reference, path_map: PathMap) -> str | None:
    """Convert a ``Reference`` to a Markdown link path, if resolvable."""
    if ref.refid is None:
        return None
    target = path_map.compounds.get(ref.refid) or path_map.members.get(ref.refid)
    if target is None:
        return None
    return _relative_link(target.path, path_map, None)
    return f"./{target.path}"


def _render_location_file(loc: SourceLocation) -> str:
    """Format a source file path for display."""
    if not loc.file:
        return "*(unknown)*"
    return f"`{loc.file}`"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _escape_yaml(value: str) -> str:
    """Escape a string for YAML frontmatter."""
    if not value:
        return '""'
    if any(ch in value for ch in ('"', "'", ":", "#", "{", "}", "[",
                                     "]", ",", "&", "*", "!", ">", "|", "@")):
        return f'"{value}"'
    return value


def _escape_table(value: str) -> str:
    """Escape pipe characters in table cells."""
    return value.replace("\n", " ").replace("|", "\\|")


def _short_name(full: str) -> str:
    """Extract the short name from a fully qualified name."""
    parts = full.rsplit("::", maxsplit=1)
    return parts[-1]


def _brief_to_text(brief: tuple[DocNode, ...]) -> str:
    """Extract a one-line summary from brief DocNodes."""
    texts: list[str] = []
    for node in brief:
        if isinstance(node, Text):
            texts.append(node.value)
        elif isinstance(node, Paragraph):
            for child in node.children:
                if isinstance(child, (Text, InlineCode)):
                    texts.append(child.value)
    return " ".join(texts)[:100]


def _section_heading(kind: str) -> str:
    """Human-readable section title from Doxygen section kind."""
    return {
        "public-func": "Public Methods",
        "protected-func": "Protected Methods",
        "private-func": "Private Methods",
        "public-attrib": "Public Members",
        "protected-attrib": "Protected Members",
        "private-attrib": "Private Members",
        "public-type": "Public Types",
        "protected-type": "Protected Types",
        "public-static-func": "Static Public Methods",
        "protected-static-func": "Static Protected Methods",
        "public-static-attrib": "Static Public Members",
        "properties": "Properties",
    }.get(kind, kind.replace("-", " ").title())


def _member_kind_label(kind: str) -> str:
    """Human-readable label for a member kind."""
    return {
        "function": "method",
        "variable": "field",
        "define": "macro",
        "typedef": "typedef",
        "enum": "enum",
        "enumvalue": "enum value",
        "property": "property",
    }.get(kind, kind)
