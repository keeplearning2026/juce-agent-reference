"""Doxygen XML → Canonical IR parser.

Two-phase parsing:
1. Index parser: reads ``index.xml`` to discover all compounds.
2. Compound parser: reads each ``<refid>.xml`` to build a ``Compound``.

Node classification (fail-closed):
- ``KNOWN_SEMANTIC`` tags → fully structured parsing.
- ``KNOWN_PRESENTATIONAL`` tags → degrade to text, record formatting-warning.
- ``BLOCK_PASSTHROUGH`` tags → parse children, passthrough.
- All other tags → ``UnsupportedSemanticNodeError``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lxml import etree  # type: ignore[import-untyped]

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
    TableRow,
    Text,
    UnorderedList,
    WarningNode,
)
from juce_reference.errors import ConversionError, UnsupportedSemanticNodeError
from juce_reference.model import (
    Compound,
    CompoundSection,
    Member,
    Parameter,
    Reference,
    SourceLocation,
)

# ---------------------------------------------------------------------------
# Node classification tables (fail-closed principle)
# ---------------------------------------------------------------------------

KNOWN_SEMANTIC: frozenset[str] = frozenset({
    "para", "simplesect", "xrefsect",
    "sect1", "sect2", "sect3", "sect4",
    "itemizedlist", "orderedlist", "table",
    "programlisting", "parameterlist", "verbatim",
    "image", "blockquote", "title", "heading",
    "highlight", "codeline", "sp",
    "ref", "ulink", "bold", "emphasis", "computeroutput",
    "formula", "linebreak", "hruler",
    "ndash", "mdash", "nonbreakablespace",
    "superscript", "subscript",
    "compounddef", "compoundname", "basecompoundref", "derivedcompoundref",
    "innerclass", "innernamespace", "location", "ingroup",
    "sectiondef", "memberdef", "name", "qualifiedname", "type",
    "definition", "argsstring", "param", "templateparamlist",
    "enumvalue", "briefdescription", "detaileddescription",
})

KNOWN_PRESENTATIONAL: frozenset[str] = frozenset({
    "center", "small", "strike", "preformatted",
})

BLOCK_PASSTHROUGH: frozenset[str] = frozenset({
    "doxygen", "compounddef",
})

_warnings: list[dict[str, Any]] = []


def reset_warnings() -> None:
    _warnings.clear()


def get_warnings() -> list[dict[str, Any]]:
    return list(_warnings)


def _record_warning(code: str, tag: str, file_path: str = "", line: int = 0) -> None:
    _warnings.append({"code": code, "tag": tag, "file": file_path, "line": line})


# ============== Index Parser ==============


@dataclass(frozen=True, slots=True)
class CompoundIndexEntry:
    refid: str
    kind: str
    name: str
    member_refids: tuple[str, ...] = ()


def parse_index(index_path: Path) -> list[CompoundIndexEntry]:
    if not index_path.is_file():
        raise ConversionError(f"index.xml not found: {index_path}", file_path=str(index_path))
    try:
        tree = etree.parse(str(index_path))
    except etree.XMLSyntaxError as exc:
        raise ConversionError(f"Malformed index.xml: {exc}", file_path=str(index_path)) from exc
    root = tree.getroot()
    entries: list[CompoundIndexEntry] = []
    for elem in root.iterfind("compound"):
        refid = elem.get("refid", "")
        kind = elem.get("kind", "")
        name = (elem.findtext("name") or "").strip()
        if not refid:
            raise ConversionError("Compound missing refid", file_path=str(index_path), xml_tag="compound")
        member_refids: list[str] = []
        for melem in elem.iterfind("member"):
            mrefid = melem.get("refid", "")
            if mrefid:
                member_refids.append(mrefid)
        entries.append(CompoundIndexEntry(refid=refid, kind=kind, name=name,
                                           member_refids=tuple(member_refids)))
    return entries


# ============== Compound Parser ==============

_MEMBER_KINDS = frozenset({
    "function", "variable", "typedef", "enum", "enumvalue",
    "define", "property", "friend",
})


def parse_compound(xml_path: Path) -> Compound:
    if not xml_path.is_file():
        raise ConversionError(f"Compound XML not found: {xml_path}", file_path=str(xml_path))
    try:
        tree = etree.parse(str(xml_path))
    except etree.XMLSyntaxError as exc:
        raise ConversionError(f"Malformed compound XML {xml_path.name}: {exc}",
                              file_path=str(xml_path)) from exc
    root = tree.getroot()
    cdef = root.find("compounddef")
    if cdef is None:
        raise ConversionError(f"No <compounddef> in {xml_path.name}", file_path=str(xml_path))
    refid = cdef.get("id", "")
    kind = cdef.get("kind", "")
    name_elem = cdef.find("compoundname")
    name = (name_elem.text or "").strip() if name_elem is not None else ""
    qualified_name = name
    title = qualified_name
    brief_raw = cdef.find("briefdescription")
    brief = tuple(_parse_doc_paragraphs(brief_raw)) if brief_raw is not None else ()
    details_raw = cdef.find("detaileddescription")
    details = tuple(_parse_doc_children(details_raw)) if details_raw is not None else ()
    bases: list[Reference] = []
    for belem in cdef.iterfind("basecompoundref"):
        bases.append(Reference(text=(belem.text or "").strip(), refid=belem.get("refid")))
    derived: list[Reference] = []
    for delem in cdef.iterfind("derivedcompoundref"):
        derived.append(Reference(text=(delem.text or "").strip(), refid=delem.get("refid")))
    inner_compounds: list[Reference] = []
    for icelem in cdef.iterfind("innerclass"):
        inner_compounds.append(Reference(text=(icelem.text or "").strip(), refid=icelem.get("refid"), kind="class"))
    for icelem in cdef.iterfind("innernamespace"):
        inner_compounds.append(Reference(text=(icelem.text or "").strip(), refid=icelem.get("refid"), kind="namespace"))
    location = None
    loc_elem = cdef.find("location")
    if loc_elem is not None:
        location = SourceLocation(
            file=loc_elem.get("file", ""), line=_parse_int(loc_elem.get("line")),
            column=_parse_int(loc_elem.get("column")),
            body_file=loc_elem.get("bodyfile"),
            body_start=_parse_int(loc_elem.get("bodystart")),
            body_end=_parse_int(loc_elem.get("bodyend")))
    module: str | None = None
    for grp in cdef.iterfind("ingroup"):
        mid = grp.get("refid", "")
        if mid:
            module = mid
    sections: list[CompoundSection] = []
    all_members: list[Member] = []
    for sdef in cdef.iterfind("sectiondef"):
        skind = sdef.get("kind", "")
        stitle = (sdef.findtext("header") or "").strip() or None
        member_refs: list[str] = []
        for mdef in sdef.iterfind("memberdef"):
            try:
                member = _parse_member(mdef)
                all_members.append(member)
                member_refs.append(member.refid)
            except Exception as exc:
                raise ConversionError(
                    f"Failed to parse member in {xml_path.name}: {exc}",
                    file_path=str(xml_path), compound_refid=refid) from exc
        if member_refs:
            sections.append(CompoundSection(kind=skind, title=stitle, member_refids=tuple(member_refs)))
    documented = cdef.get("prot", "public") != "private" or bool(brief) or bool(details)
    return Compound(refid=refid, kind=kind, name=name, qualified_name=qualified_name,
                    title=title, brief=brief, details=details, bases=tuple(bases),
                    derived=tuple(derived), inner_compounds=tuple(inner_compounds),
                    members=tuple(all_members), location=location, module=module,
                    documented=documented, sections=tuple(sections))


# ============== Member Parser ==============


def _parse_member(mdef: etree._Element) -> Member:
    refid = mdef.get("id", "")
    kind = mdef.get("kind", "")
    prot = mdef.get("prot", "public")
    static = mdef.get("static", "no") == "yes"
    const = mdef.get("const", "no") == "yes"
    explicit = mdef.get("explicit", "no") == "yes"
    inline = mdef.get("inline", "no") == "yes"
    mutable = mdef.get("mutable", "no") == "yes"
    virt = mdef.get("virt", "non-virtual")
    virtual_kind = virt if virt != "non-virtual" else None
    name_elem = mdef.find("name")
    name = (name_elem.text or "").strip() if name_elem is not None else ""
    qname_elem = mdef.find("qualifiedname")
    qname = (qname_elem.text or "").strip() if qname_elem is not None else name
    def_elem = mdef.find("definition")
    definition_nodes: tuple[DocNode, ...] = (
        (Text(def_elem.text or ""),) if def_elem is not None and def_elem.text else ())
    args_elem = mdef.find("argsstring")
    args_string_nodes: tuple[DocNode, ...] = (
        (Text(args_elem.text or ""),) if args_elem is not None and args_elem.text else ())
    sig_parts: list[str] = []
    if def_elem is not None and def_elem.text:
        sig_parts.append(def_elem.text.strip())
    if args_elem is not None and args_elem.text:
        sig_parts.append(args_elem.text.strip())
    signature = " ".join(sig_parts)
    parameters: list[Parameter] = []
    for pelem in mdef.iterfind("param"):
        type_nodes = _parse_doc_children(pelem.find("type"), default=(Text(""),))
        pname = (pelem.findtext("declname") or "").strip() or None
        defval_nodes = _parse_doc_children(pelem.find("defval"), default=())
        desc = _parse_doc_paragraphs(pelem.find("briefdescription"))
        parameters.append(Parameter(type_nodes=type_nodes, name=pname,
                                     default_value_nodes=defval_nodes, description=tuple(desc)))
    template_parameters: list[Parameter] = []
    tplist = mdef.find("templateparamlist")
    if tplist is not None:
        for tpelem in tplist.iterfind("param"):
            type_nodes = _parse_doc_children(tpelem.find("type"), default=(Text(""),))
            tpname = (tpelem.findtext("declname") or "").strip() or None
            template_parameters.append(Parameter(type_nodes=type_nodes, name=tpname))
    if kind == "enum":
        for ev_elem in mdef.iterfind("enumvalue"):
            ev_name = (ev_elem.findtext("name") or "").strip()
            ev_brief = _parse_doc_paragraphs(ev_elem.find("briefdescription"))
            parameters.append(Parameter(name=ev_name, description=tuple(ev_brief)))
    brief_raw = mdef.find("briefdescription")
    brief = tuple(_parse_doc_paragraphs(brief_raw)) if brief_raw is not None else ()
    details_raw = mdef.find("detaileddescription")
    details = tuple(_parse_doc_children(details_raw)) if details_raw is not None else ()
    deprecated = False
    for desc in mdef.iterfind("detaileddescription"):
        for para in desc.iterfind("para"):
            for child in para:
                if child.tag == "xrefsect":
                    xreftitle = child.findtext("xreftitle", "")
                    if "deprecated" in xreftitle.lower():
                        deprecated = True
    location = None
    loc_elem = mdef.find("location")
    if loc_elem is not None:
        location = SourceLocation(
            file=loc_elem.get("file", ""), line=_parse_int(loc_elem.get("line")),
            column=_parse_int(loc_elem.get("column")),
            body_file=loc_elem.get("bodyfile"),
            body_start=_parse_int(loc_elem.get("bodystart")),
            body_end=_parse_int(loc_elem.get("bodyend")))
    documented = bool(brief) or bool(details)
    return Member(refid=refid, kind=kind, name=name, qualified_name=qname,
                  definition_nodes=definition_nodes, args_string_nodes=args_string_nodes,
                  signature=signature, access=prot, static=static, const=const,
                  explicit=explicit, inline=inline, mutable=mutable,
                  virtual_kind=virtual_kind, parameters=tuple(parameters),
                  template_parameters=tuple(template_parameters), brief=brief,
                  details=details, location=location, deprecated=deprecated,
                  documented=documented)


# ============== Documentation Node Parser ==============


def _parse_doc_children(parent: etree._Element | None, *, default: tuple[DocNode, ...] = ()) -> tuple[DocNode, ...]:
    if parent is None:
        return default
    children: list[DocNode] = []
    for child_elem in parent:
        parsed = _parse_doc_element(child_elem)
        if parsed:
            if isinstance(parsed, list):
                children.extend(parsed)
            else:
                children.append(parsed)
    return tuple(children) if children else default


def _parse_doc_paragraphs(parent: etree._Element | None) -> list[DocNode]:
    return list(_parse_doc_children(parent))


def _parse_doc_element(elem: etree._Element) -> DocNode | list[DocNode] | None:
    tag = elem.tag

    if tag == "para":
        block_elements: list[DocNode] = []
        inline_elements: list[DocNode] = []
        current_inline: list[DocNode] = []
        if elem.text and elem.text.strip():
            current_inline.append(Text(elem.text.strip()))
        for child in elem:
            ctag = child.tag
            if ctag in ("simplesect", "xrefsect", "sect1", "sect2", "sect3", "sect4",
                        "itemizedlist", "orderedlist", "table", "programlisting",
                        "parameterlist", "verbatim", "image", "blockquote"):
                if current_inline:
                    inline_elements.append(Paragraph(children=tuple(current_inline)))
                    current_inline = []
                parsed = _parse_doc_element(child)
                if parsed:
                    if isinstance(parsed, list):
                        block_elements.extend(parsed)
                    else:
                        block_elements.append(parsed)
            else:
                current_inline.extend(_parse_inline_element(child))
            if child.tail and child.tail.strip():
                current_inline.append(Text(child.tail.strip()))
        if current_inline:
            inline_elements.append(Paragraph(children=tuple(current_inline)))
        if block_elements:
            return inline_elements + block_elements if inline_elements else block_elements
        if inline_elements:
            return inline_elements[0] if len(inline_elements) == 1 else inline_elements
        return None

    if tag == "simplesect":
        skind = elem.get("kind", "")
        children = _parse_doc_children(elem, default=())
        if skind == "return":
            return ParameterList(kind="return", entries=(ParameterEntry(children=children),))
        if skind == "see":
            return Paragraph(children=(Text("See also: "), *children))
        if skind == "note":
            return Note(children=children)
        if skind == "warning":
            return WarningNode(children=children)
        if skind == "deprecated":
            return DeprecatedNode(children=children)
        if skind == "pre":
            return Paragraph(children=(Text("Precondition: "), *children))
        if skind == "post":
            return Paragraph(children=(Text("Postcondition: "), *children))
        return Paragraph(children=children)

    if tag == "xrefsect":
        xreftitle = elem.findtext("xreftitle", "")
        xrefdesc = elem.find("xrefdescription")
        children = _parse_doc_children(xrefdesc, default=())
        if "deprecated" in xreftitle.lower():
            return DeprecatedNode(children=children)
        label = xreftitle.strip().rstrip(":")
        if label:
            return Note(children=(Paragraph(children=(
                Bold(children=(Text(f"{label}: "),)), *children)),))
        return None

    if tag in ("sect1", "sect2", "sect3", "sect4"):
        level = int(tag[-1])
        sect_title: tuple[DocNode, ...] = (
            tuple(_parse_inline_children(elem.find("title")))
            if elem.find("title") is not None else ())
        body = _parse_doc_children(elem, default=())
        return Section(level=level, title=sect_title, children=body)

    if tag == "title":
        return DocTitle(children=tuple(_parse_inline_children(elem)))

    if tag == "itemizedlist":
        list_items: list[DocNode] = []
        for li in elem.iterfind("listitem"):
            list_items.append(ListItem(children=_parse_doc_children(li, default=())))
        return UnorderedList(items=tuple(list_items))

    if tag == "orderedlist":
        ord_items: list[DocNode] = []
        for li in elem.iterfind("listitem"):
            ord_items.append(ListItem(children=_parse_doc_children(li, default=())))
        return OrderedList(items=tuple(ord_items))

    if tag == "table":
        rows: list[TableRow] = []
        for re in elem.iterfind("row"):
            cells: list[TableCell] = []
            for ce in re.iterfind("entry"):
                cells.append(TableCell(children=_parse_doc_children(ce, default=())))
            rows.append(TableRow(cells=tuple(cells), header=bool(elem.find("caption"))))
        return Table(rows=tuple(rows))

    if tag == "programlisting":
        code = "".join(itertext(elem))
        return CodeBlock(code=code, language="cpp")

    if tag in ("codeline", "highlight"):
        return None

    if tag == "parameterlist":
        pkind = elem.get("kind", "")
        entries: list[ParameterEntry] = []
        for pitem in elem.iterfind("parameteritem"):
            pname_elem = pitem.find("parameternamelist")
            pnames: list[str] = []
            if pname_elem is not None:
                for pn in pname_elem.iterfind("parametername"):
                    pnames.append((pn.text or "").strip())
            pdesc = _parse_doc_children(pitem.find("parameterdescription"), default=())
            for pn in pnames or [""]:
                entries.append(ParameterEntry(name=pn, children=pdesc))
        return ParameterList(kind=pkind, entries=tuple(entries))

    if tag == "verbatim":
        text = "".join(itertext(elem))
        return Preformatted(text=text)

    if tag == "formula":
        text = "".join(itertext(elem))
        display = elem.get("display", "no") == "yes"
        return Formula(value=text, display=display)

    if tag == "image":
        name = elem.get("name", "")
        caption_raw = elem.find("caption")
        caption = _parse_doc_children(caption_raw, default=())
        return ImageNode(name=name, caption=caption)

    if tag == "linebreak":
        return LineBreak()

    if tag == "hruler":
        return Text("\n---\n")

    if tag == "blockquote":
        children = _parse_doc_children(elem, default=())
        return Paragraph(children=(Text("> "), *children))

    if tag == "ref":
        refid = elem.get("refid")
        kind = elem.get("kindref")
        text = (elem.text or "").strip() or "".join(itertext(elem))
        return ReferenceNode(
            refid=refid if refid is not None and "#" not in refid else None,
            external_url=refid if refid and refid.startswith("http") else None,
            kind=kind, children=tuple(_parse_inline_children(elem)))

    if tag == "ulink":
        url = elem.get("url", "")
        text = (elem.text or "").strip() or url
        return ReferenceNode(external_url=url, children=(Text(text),))

    return _parse_inline_fallback(elem)


# ============== Inline Parsers ==============


def _parse_inline_children(elem: etree._Element | None) -> list[DocNode]:
    if elem is None:
        return []
    nodes: list[DocNode] = []
    if elem.text and elem.text.strip():
        nodes.append(Text(elem.text.strip()))
    for child in elem:
        nodes.extend(_parse_inline_element(child))
        if child.tail and child.tail.strip():
            nodes.append(Text(child.tail.strip()))
    return nodes


def _parse_inline_element(elem: etree._Element) -> list[DocNode]:
    tag = elem.tag
    if tag == "ref":
        refid = elem.get("refid")
        kind = elem.get("kindref")
        children = tuple(_parse_inline_children(elem))
        return [ReferenceNode(
            refid=refid if refid and not refid.startswith("http") else None,
            external_url=refid if refid and refid.startswith("http") else None,
            kind=kind, children=children)]
    if tag == "ulink":
        url = elem.get("url", "")
        text = (elem.text or "").strip() or url
        return [ReferenceNode(external_url=url, children=(Text(text),))]
    if tag == "bold":
        return [Bold(children=tuple(_parse_inline_children(elem)))]
    if tag == "emphasis":
        return [Emphasis(children=tuple(_parse_inline_children(elem)))]
    if tag == "computeroutput":
        return [InlineCode(value=(elem.text or "").strip())]
    if tag == "programlisting":
        code = "".join(itertext(elem))
        return [CodeBlock(code=code, language="cpp")]
    if tag == "formula":
        return [Formula(value="".join(itertext(elem)))]
    if tag == "linebreak":
        return [LineBreak()]
    if tag == "sp":
        return [Text(" ")]
    if tag == "ndash":
        return [Text("–")]
    if tag == "mdash":
        return [Text("—")]
    if tag == "nonbreakablespace":
        return [Text(" ")]
    if tag == "superscript":
        return [Text("^(" + "".join(itertext(elem)) + ")")]
    if tag == "subscript":
        return [Text("_(" + "".join(itertext(elem)) + ")")]
    return _parse_inline_fallback(elem)


def _parse_inline_fallback(elem: etree._Element) -> list[DocNode]:
    """Fail-closed fallback: presentational → text+warn, unknown → error."""
    tag = elem.tag
    if tag in KNOWN_PRESENTATIONAL:
        _record_warning("unsupported-presentational", tag)
        return [Paragraph(children=(Text("".join(itertext(elem))),))]
    raise UnsupportedSemanticNodeError(
        f"Unsupported XML tag: <{tag}>", xml_tag=tag,
        suggestion="Extend the parser or classify as presentational.")


# ============== Helpers ==============


def itertext(elem: etree._Element) -> list[str]:
    parts: list[str] = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        parts.extend(itertext(child))
        if child.tail:
            parts.append(child.tail)
    return parts


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
