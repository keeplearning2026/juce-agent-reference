"""Tests for the deterministic path mapper."""

from juce_reference.model import Compound, Member
from juce_reference.path_mapper import (
    build_path_map,
    member_anchor,
)


def test_member_anchor_stable() -> None:
    a1 = member_anchor("class_foo_1a2b3c")
    a2 = member_anchor("class_foo_1a2b3c")
    assert a1 == a2
    assert a1.startswith("m-")
    assert len(a1) == 12  # "m-" + 10 hex


def test_member_anchor_different_for_different_refids() -> None:
    a1 = member_anchor("ref_aaa")
    a2 = member_anchor("ref_bbb")
    assert a1 != a2


def test_build_path_map_class() -> None:
    compounds = [
        Compound(refid="class_Foo", kind="class", name="juce::Foo",
                 qualified_name="juce::Foo"),
    ]
    pm = build_path_map(compounds)
    target = pm.compounds["class_Foo"]
    assert target.path == "reference/types/juce/Foo.md"
    assert target.anchor is None


def test_build_path_map_namespace() -> None:
    compounds = [
        Compound(refid="namespace_juce_dsp", kind="namespace",
                 name="juce::dsp", qualified_name="juce::dsp"),
    ]
    pm = build_path_map(compounds)
    target = pm.compounds["namespace_juce_dsp"]
    assert "reference/namespaces" in target.path
    assert "dsp.md" in target.path


def test_build_path_map_group() -> None:
    compounds = [
        Compound(refid="group_juce_audio_basics", kind="group",
                 name="juce_audio_basics",
                 qualified_name="juce_audio_basics"),
    ]
    pm = build_path_map(compounds)
    target = pm.compounds["group_juce_audio_basics"]
    assert "reference/modules" in target.path


def test_case_insensitive_collision_resolved() -> None:
    compounds = [
        Compound(refid="ref_aaa", kind="class", name="Foo",
                 qualified_name="Foo"),
        Compound(refid="ref_bbb", kind="class", name="Foo",
                 qualified_name="Foo"),
    ]
    pm = build_path_map(compounds)
    paths = [pm.compounds[r].path for r in ("ref_aaa", "ref_bbb")]
    assert len(set(paths)) == 2, f"Collision not resolved: {paths}"
    # One of them should have the disambiguator hash.
    assert any("--" in p for p in paths)


def test_member_anchor_preserved() -> None:
    compounds = [
        Compound(
            refid="class_Foo", kind="class", name="Foo", qualified_name="Foo",
            members=(
                Member(refid="member_123", kind="function", name="bar",
                       qualified_name="Foo::bar"),
                Member(refid="member_456", kind="function", name="bar",
                       qualified_name="Foo::bar"),
            ),
        ),
    ]
    pm = build_path_map(compounds)
    assert pm.members["member_123"].anchor != pm.members["member_456"].anchor
