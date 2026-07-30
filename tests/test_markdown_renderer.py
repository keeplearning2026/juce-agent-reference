"""Tests for the Markdown renderer."""

from juce_reference.documentation_nodes import (
    CodeBlock,
    InlineCode,
    Note,
    Paragraph,
    ParameterEntry,
    ParameterList,
    Text,
    WarningNode,
)
from juce_reference.markdown_renderer import (
    _escape_yaml,
    _render_node,
    _short_name,
)
from juce_reference.model import (
    Compound,
    SourceLocation,
)
from juce_reference.path_mapper import OutputTarget, PathMap


def _empty_path_map() -> PathMap:
    return PathMap(compounds={}, members={})


def test_escape_yaml_simple() -> None:
    assert _escape_yaml("hello") == "hello"


def test_escape_yaml_with_colon() -> None:
    result = _escape_yaml("juce::Foo")
    assert result == '"juce::Foo"'


def test_short_name() -> None:
    assert _short_name("juce::dsp::ProcessorChain") == "ProcessorChain"
    assert _short_name("juce::AudioProcessor") == "AudioProcessor"


def test_render_text() -> None:
    node = Text("hello world")
    result = _render_node(node, _empty_path_map())
    assert result == "hello world"


def test_render_paragraph() -> None:
    node = Paragraph(children=(Text("A"), Text("B")))
    result = _render_node(node, _empty_path_map())
    assert "A" in result
    assert "B" in result


def test_render_inline_code() -> None:
    node = InlineCode("int")
    result = _render_node(node, _empty_path_map())
    assert result == "`int`"


def test_render_code_block() -> None:
    node = CodeBlock(code="void foo();", language="cpp")
    result = _render_node(node, _empty_path_map())
    assert "```cpp" in result
    assert "void foo();" in result


def test_render_note() -> None:
    node = Note(children=(Paragraph(children=(Text("important"),)),))
    result = _render_node(node, _empty_path_map())
    assert "**Note:**" in result
    assert "important" in result


def test_render_warning() -> None:
    node = WarningNode(children=(Paragraph(children=(Text("careful"),)),))
    result = _render_node(node, _empty_path_map())
    assert "**Warning:**" in result


def test_render_parameter_list() -> None:
    node = ParameterList(
        kind="param",
        entries=(
            ParameterEntry(name="x", children=(Text("the x coordinate"),)),
        ),
    )
    result = _render_node(node, _empty_path_map())
    assert "`x`" in result
    assert "the x coordinate" in result


def test_render_compound_frontmatter(tmp_path) -> None:
    compound = Compound(
        refid="class_Foo", kind="class", name="juce::Foo",
        qualified_name="juce::Foo",
        location=SourceLocation(file="juce_Foo.h", line=42),
    )
    pm = PathMap(
        compounds={
            "class_Foo": OutputTarget(
                refid="class_Foo",
                path="reference/types/juce/Foo.md",
                anchor=None,
            ),
        },
        members={},
    )
    from juce_reference.markdown_renderer import render_compound
    doc = render_compound(compound, pm, juce_commit="abc123def")
    assert "juce_commit: abc123def" in doc.content
    assert "juce::Foo" in doc.content
    assert "# juce::Foo" in doc.content
