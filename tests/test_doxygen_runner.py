"""Tests for Doxygen runner."""

from pathlib import Path

from juce_reference.doxygen_runner import (
    _HARD_OVERRIDES,
    _merge_overlay,
    _parse_doxyfile,
    classify_doxygen_warnings,
)


class TestDoxyfileParsing:
    def test_parse_simple(self) -> None:
        content = "PROJECT_NAME = JUCE\nOUTPUT_DIRECTORY = ./output\n"
        path = _write_temp_doxyfile(content)
        cfg = _parse_doxyfile(path)
        assert cfg["PROJECT_NAME"] == "JUCE"
        assert cfg["OUTPUT_DIRECTORY"] == "./output"

    def test_parse_with_comments(self) -> None:
        content = "# Comment\nKEY = VALUE\n# Another comment\nKEY2 = VALUE2\n"
        path = _write_temp_doxyfile(content)
        cfg = _parse_doxyfile(path)
        assert cfg == {"KEY": "VALUE", "KEY2": "VALUE2"}

    def test_parse_plus_equals(self) -> None:
        content = "INPUT = src\nINPUT += extra\n"
        path = _write_temp_doxyfile(content)
        cfg = _parse_doxyfile(path)
        assert cfg["INPUT"] == "srcextra"

    def test_parse_multiline_value(self) -> None:
        content = "KEY = line1\n  line2\n  line3\nNEXT = val\n"
        path = _write_temp_doxyfile(content)
        cfg = _parse_doxyfile(path)
        assert cfg["KEY"] == "line1\nline2\nline3"
        assert cfg["NEXT"] == "val"


class TestOverlay:
    def test_hard_overrides_applied(self) -> None:
        original = {"GENERATE_HTML": "YES", "GENERATE_XML": "NO", "KEEP_ME": "kept"}
        overlay = {"GENERATE_HTML": "NO", "GENERATE_XML": "YES"}
        result = _merge_overlay(original, overlay, _HARD_OVERRIDES, "abc123")
        assert "GENERATE_HTML = NO" in result
        assert "GENERATE_XML = YES" in result
        assert "KEEP_ME = kept" in result
        assert "PROJECT_NUMBER = abc123" in result

    def test_new_keys_appended(self) -> None:
        original = {"EXISTING": "val"}
        overlay = {"NEW_KEY": "new_val"}
        result = _merge_overlay(original, overlay, set(), "sha")
        assert "NEW_KEY = new_val" in result
        assert "EXISTING = val" in result


class TestWarningClassification:
    def test_empty_warnings(self, tmp_path: Path) -> None:
        p = tmp_path / "warnings.log"
        p.write_text("", encoding="utf-8")
        result = classify_doxygen_warnings(p)
        assert result["total"] == 0

    def test_categorises_warnings(self, tmp_path: Path) -> None:
        p = tmp_path / "warnings.log"
        p.write_text(
            "file.h:10: warning: found undocumented parameter\n"
            "other.cpp:5: warning: unable to resolve reference\n",
            encoding="utf-8",
        )
        result = classify_doxygen_warnings(p)
        assert result["total"] == 2


def _write_temp_doxyfile(content: str) -> Path:
    import tempfile

    with tempfile.NamedTemporaryFile(
        suffix=".doxyfile", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write(content)
        return Path(f.name)
