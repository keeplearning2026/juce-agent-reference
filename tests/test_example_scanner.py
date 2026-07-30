"""Tests for example scanner."""

from pathlib import Path

from juce_reference.example_scanner import (
    ExampleSymbolUse,
    find_example_symbols,
    scan_examples,
)


def test_scan_empty_dir(tmp_path: Path) -> None:
    examples = scan_examples(tmp_path)
    assert examples == []


def test_scan_minimal_structure(tmp_path: Path) -> None:
    # Create a minimal example structure
    plugins = tmp_path / "Plugins"
    example_dir = plugins / "MyPlugin"
    example_dir.mkdir(parents=True)
    (example_dir / "PluginProcessor.h").write_text(
        "#include <juce_audio_processors.h>\n"
        "class MyPlugin : public juce::AudioProcessor {\n"
        "};\n",
        encoding="utf-8",
    )

    examples = scan_examples(tmp_path)
    assert len(examples) == 1
    assert examples[0].name == "MyPlugin"
    assert examples[0].category == "plugins"
    assert len(examples[0].files) == 1


def test_find_qualified_symbols(tmp_path: Path) -> None:
    plugins = tmp_path / "Plugins"
    example_dir = plugins / "TestPlugin"
    example_dir.mkdir(parents=True)
    (example_dir / "Source.cpp").write_text(
        "auto apvts = juce::AudioProcessorValueTreeState(processor, nullptr);\n"
        "auto proc = juce::AudioProcessor();\n",
        encoding="utf-8",
    )

    examples = scan_examples(tmp_path)
    known = frozenset({
        "juce::AudioProcessorValueTreeState",
        "juce::AudioProcessor",
    })
    uses = find_example_symbols(examples, tmp_path, known)
    assert len(uses) == 2
    assert uses[0].confidence == "qualified-text"


def test_find_inheritance_symbols(tmp_path: Path) -> None:
    plugins = tmp_path / "Plugins"
    example_dir = plugins / "InheritPlugin"
    example_dir.mkdir(parents=True)
    (example_dir / "Editor.h").write_text(
        "class MyEditor : public juce::AudioProcessorEditor {\n"
        "};\n",
        encoding="utf-8",
    )

    examples = scan_examples(tmp_path)
    known = frozenset({"juce::AudioProcessorEditor"})
    uses = find_example_symbols(examples, tmp_path, known)
    assert len(uses) >= 1
    assert uses[0].confidence == "qualified-inheritance"


def test_example_symbol_use_dataclass() -> None:
    u = ExampleSymbolUse(
        example_name="Test",
        category="plugins",
        file="Source.cpp",
        line=10,
        symbol="juce::AudioProcessor",
        confidence="qualified-text",
    )
    assert u.symbol == "juce::AudioProcessor"
