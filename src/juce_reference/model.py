"""Canonical Intermediate Representation data model.

These immutable dataclasses represent the output of the Doxygen XML parser
and the input to the Markdown renderer and index builders.
"""

from __future__ import annotations

from dataclasses import dataclass

from juce_reference.documentation_nodes import DocNode, EntityDisposition

# ---------------------------------------------------------------------------
# Source location
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """File and line information for a declaration or definition."""

    file: str
    line: int | None = None
    column: int | None = None
    body_file: str | None = None
    body_start: int | None = None
    body_end: int | None = None


# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Reference:
    """A typed reference to another entity (internal refid or external URL)."""

    text: str
    refid: str | None = None
    external_url: str | None = None
    kind: str | None = None


# ---------------------------------------------------------------------------
# Parameter
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Parameter:
    """A function / template parameter with type, name, and description."""

    type_nodes: tuple[DocNode, ...] = ()
    name: str | None = None
    default_value_nodes: tuple[DocNode, ...] = ()
    description: tuple[DocNode, ...] = ()


# ---------------------------------------------------------------------------
# Member
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Member:
    """One member (method, field, enum, typedef, macro, …)."""

    refid: str
    kind: str
    name: str
    qualified_name: str

    # Signature info
    definition_nodes: tuple[DocNode, ...] = ()
    args_string_nodes: tuple[DocNode, ...] = ()
    signature: str = ""

    # Qualifiers
    access: str = "public"
    static: bool = False
    const: bool = False
    explicit: bool = False
    inline: bool = False
    mutable: bool = False
    virtual_kind: str | None = None

    # Parameters
    parameters: tuple[Parameter, ...] = ()
    template_parameters: tuple[Parameter, ...] = ()

    # Documentation
    brief: tuple[DocNode, ...] = ()
    details: tuple[DocNode, ...] = ()
    location: SourceLocation | None = None
    deprecated: bool = False
    documented: bool = True

    # Disposition
    disposition: EntityDisposition = EntityDisposition.RENDERED
    skip_reason: str = ""


# ---------------------------------------------------------------------------
# Compound (class, struct, namespace, module, …)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Compound:
    """A top-level Doxygen compound (class, struct, namespace, group, file, page)."""

    refid: str
    kind: str
    name: str
    qualified_name: str

    title: str | None = None
    brief: tuple[DocNode, ...] = ()
    details: tuple[DocNode, ...] = ()

    # Inheritance
    bases: tuple[Reference, ...] = ()
    derived: tuple[Reference, ...] = ()

    # Contained items
    inner_compounds: tuple[Reference, ...] = ()
    members: tuple[Member, ...] = ()

    # Location & module
    location: SourceLocation | None = None
    module: str | None = None
    documented: bool = True

    # Groups / pages may have sub-sections
    sections: tuple[CompoundSection, ...] = ()

    # Disposition
    disposition: EntityDisposition = EntityDisposition.RENDERED
    skip_reason: str = ""


@dataclass(frozen=True, slots=True)
class CompoundSection:
    """A member-group section within a compound (e.g. public methods, constructors)."""

    kind: str  # "public-func", "protected-func", "public-attrib", …
    title: str | None = None
    member_refids: tuple[str, ...] = ()
