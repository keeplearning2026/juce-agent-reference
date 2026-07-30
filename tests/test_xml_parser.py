"""Tests for the Doxygen XML parser."""

from pathlib import Path

from juce_reference.documentation_nodes import (
    DocNode,
    Note,
    Paragraph,
    WarningNode,
)
from juce_reference.xml_parser import (
    parse_compound,
    parse_index,
)

FIXTURES = Path(__file__).parent / "fixtures" / "doxygen"


class TestIndexParser:
    def test_parse_fixture_index(self) -> None:
        entries = parse_index(FIXTURES / "index.xml")
        assert len(entries) == 3
        assert entries[0].refid == "class_juce_1_1_audio_processor"
        assert entries[0].kind == "class"
        assert entries[0].name == "juce::AudioProcessor"
        assert len(entries[0].member_refids) == 1
        assert entries[0].member_refids[0] == "class_juce_1_1_audio_processor_1a_process_block"

    def test_parse_missing_index(self) -> None:
        import pytest

        from juce_reference.errors import ConversionError
        with pytest.raises(ConversionError, match="index.xml not found"):
            parse_index(Path("/nonexistent/index.xml"))


class TestCompoundParser:
    def test_parse_audio_processor(self) -> None:
        compound = parse_compound(FIXTURES / "class_juce_1_1_audio_processor.xml")
        assert compound.refid == "class_juce_1_1_audio_processor"
        assert compound.kind == "class"
        assert compound.name == "juce::AudioProcessor"
        assert compound.qualified_name == "juce::AudioProcessor"

        # Brief
        assert len(compound.brief) > 0
        assert isinstance(compound.brief[0], Paragraph)

        # Bases
        assert len(compound.bases) == 1
        assert compound.bases[0].text == "juce::ReferenceCountedObject"

        # Members
        assert len(compound.members) == 1
        member = compound.members[0]
        assert member.name == "processBlock"
        assert member.kind == "function"
        assert member.virtual_kind == "pure-virtual"
        assert "processBlock" in member.signature

    def test_member_signature(self) -> None:
        compound = parse_compound(FIXTURES / "class_juce_1_1_audio_processor.xml")
        member = compound.members[0]
        assert "processBlock" in member.signature
        assert member.qualified_name == "juce::AudioProcessor::processBlock"

    def test_compound_location(self) -> None:
        compound = parse_compound(FIXTURES / "class_juce_1_1_audio_processor.xml")
        assert compound.location is not None
        assert "juce_AudioProcessor.h" in compound.location.file
        assert compound.location.line == 123

    def test_documentation_nodes_in_details(self) -> None:
        compound = parse_compound(FIXTURES / "class_juce_1_1_audio_processor.xml")
        # Find a Note node in the details
        has_note = _contains_node_type(compound.details, Note)
        has_warning = _contains_node_type(compound.details, WarningNode)
        assert has_note, "Expected Note in details"
        assert has_warning, "Expected WarningNode in details"


def _contains_node_type(nodes: tuple[DocNode, ...], node_type: type) -> bool:
    """Recursively check if any node matches the given type."""
    for node in nodes:
        if isinstance(node, node_type):
            return True
        if hasattr(node, "children") and _contains_node_type(node.children, node_type):
            return True
        if hasattr(node, "items") and _contains_node_type(node.items, node_type):
            return True
        if hasattr(node, "rows"):
            for row in node.rows:
                for cell in getattr(row, "cells", ()):
                    if _contains_node_type(getattr(cell, "children", ()), node_type):
                        return True
        if hasattr(node, "entries"):
            for entry in node.entries:
                if _contains_node_type(getattr(entry, "children", ()), node_type):
                    return True
    return False
