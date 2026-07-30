"""Tests for utility modules."""

from pathlib import Path

import pytest

from juce_reference.util.command import run
from juce_reference.util.hashing import file_sha256, sha256_hex, short_id
from juce_reference.util.json_io import json_lines, read_json, write_json, write_json_nosort
from juce_reference.util.markdown import (
    collect_anchors,
    collect_headings,
    extract_links,
    internal_links,
    split_frontmatter,
)
from juce_reference.util.paths import posix, relative_posix, sanitise_name
from juce_reference.util.text import camel_to_words, is_fully_qualified, normalise_whitespace


class TestHashing:
    def test_sha256_hex_string(self) -> None:
        h = sha256_hex("hello")
        assert len(h) == 64
        assert h == sha256_hex(b"hello")

    def test_sha256_hex_deterministic(self) -> None:
        assert sha256_hex("abc") == sha256_hex("abc")

    def test_file_sha256(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("data", encoding="utf-8")
        h = file_sha256(f)
        assert len(h) == 64

    def test_short_id(self) -> None:
        assert len(short_id("foo")) == 10
        assert short_id("abc") == sha256_hex("abc")[:10]


class TestCommand:
    def test_echo_run(self) -> None:
        result = run(["echo", "hello"])
        assert result.ok
        assert "hello" in result.stdout

    def test_command_result_dict(self) -> None:
        result = run(["echo", "hi"])
        d = result.to_dict()
        assert d["returncode"] == 0
        assert "stdout" in d

    def test_nonzero_command(self) -> None:
        result = run(["python", "-c", "import sys; sys.exit(2)"])
        assert not result.ok
        assert result.returncode == 2


class TestJsonIO:
    def test_write_and_read(self, tmp_path: Path) -> None:
        p = tmp_path / "test.json"
        write_json(p, {"a": 1})
        assert read_json(p) == {"a": 1}

    def test_ordered_keys(self, tmp_path: Path) -> None:
        p = tmp_path / "test.json"
        write_json_nosort(p, {"z": 9, "a": 1})
        assert read_json(p) == {"z": 9, "a": 1}

    def test_json_lines(self, tmp_path: Path) -> None:
        p = tmp_path / "test.jsonl"
        p.write_text('{"a":1}\n{"b":2}\n', encoding="utf-8")
        lines = json_lines(p)
        assert len(lines) == 2
        assert lines[0] == {"a": 1}


class TestMarkdown:
    def test_split_frontmatter(self) -> None:
        text = "---\nsymbol: foo\n---\n\n# Title\n\nBody"
        fm, body = split_frontmatter(text)
        assert fm["symbol"] == "foo"
        assert body.startswith("# Title")

    def test_no_frontmatter(self) -> None:
        text = "# Title\nBody"
        fm, body = split_frontmatter(text)
        assert fm == {}
        assert body == text

    def test_collect_headings(self) -> None:
        md = "# H1\n## H2\n### H3\n"
        headings = collect_headings(md)
        assert headings == [(1, "H1"), (2, "H2"), (3, "H3")]

    def test_collect_anchors(self) -> None:
        md = '<a id="foo"></a>\n<a id="bar"></a>'
        anchors = collect_anchors(md)
        assert anchors == ["foo", "bar"]

    def test_extract_links(self) -> None:
        md = "[text](url) and [other](https://example.com)"
        links = extract_links(md)
        assert links == [("text", "url"), ("other", "https://example.com")]

    def test_internal_links(self) -> None:
        md = "[a](./a.md) [b](https://ext.com) [c](../c.md)"
        links = internal_links(md)
        assert set(link[1] for link in links) == {"./a.md", "../c.md"}


class TestPaths:
    def test_posix_windows_path(self) -> None:
        p = Path(r"C:\foo\bar\baz")
        assert posix(p) == "C:/foo/bar/baz"

    def test_relative_posix(self) -> None:
        root = Path("/a/b")
        child = Path("/a/b/c/d")
        assert relative_posix(child, root) == "c/d"

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("foo", "foo"),
            ("foo<bar", "foo_bar"),
            ('has"quote', "has_quote"),
            ("", "_unknown_"),
            ("CON", "_CON_"),
            ("aux", "_aux_"),
        ],
    )
    def test_sanitise_name(self, name: str, expected: str) -> None:
        result = sanitise_name(name)
        assert result == expected


class TestText:
    def test_camel_to_words(self) -> None:
        assert camel_to_words("AudioProcessorValueTreeState") == "Audio Processor Value Tree State"

    def test_normalise_whitespace(self) -> None:
        assert normalise_whitespace("a  b\tc\n d") == "a b c d"

    def test_is_fully_qualified(self) -> None:
        assert is_fully_qualified("juce::AudioProcessor") is True
        assert is_fully_qualified("Component") is False
