"""Tests for the unified exception hierarchy."""


import pytest

from juce_reference.errors import (
    CliUsageError,
    ConversionError,
    DeterminismError,
    DoxygenExecutionError,
    EnvironmentCheckError,
    ExternalBlockerError,
    GenerationError,
    JuceReferenceError,
    JuceSourceError,
    OutputValidationError,
    PublishError,
    RepositoryStateError,
    SearchQualityError,
    SmokeTestError,
    UnsupportedSemanticNodeError,
    VersionVerificationError,
    XmlValidationError,
)


def test_base_error_carries_context() -> None:
    err = JuceReferenceError(
        "something went wrong",
        phase="doxygen",
        command='doxygen --version',
        file_path="/tmp/test.xml",
        xml_tag="parameterlist",
        compound_refid="class_foo",
        member_refid="class_foo_1a2b3c",
        symbol="juce::Foo::bar",
        suggestion="Check Doxygen version",
    )
    assert err.exit_code == 1
    assert err.phase == "doxygen"
    assert err.symbol == "juce::Foo::bar"


@pytest.mark.parametrize(
    "exc_cls,expected_code",
    [
        (CliUsageError, 2),
        (EnvironmentCheckError, 3),
        (JuceSourceError, 4),
        (DoxygenExecutionError, 5),
        (XmlValidationError, 6),
        (ConversionError, 7),
        (GenerationError, 8),
        (OutputValidationError, 9),
        (SmokeTestError, 10),
        (SearchQualityError, 11),
        (DeterminismError, 12),
        (PublishError, 13),
        (VersionVerificationError, 14),
        (RepositoryStateError, 15),
        (ExternalBlockerError, 20),
    ],
)
def test_exit_codes(exc_cls: type[JuceReferenceError], expected_code: int) -> None:
    assert exc_cls.exit_code == expected_code


def test_unsupported_semantic_node_is_conversion_error() -> None:
    err = UnsupportedSemanticNodeError(
        "unrecognised node <foo>",
        xml_tag="foo",
        compound_refid="class_Bar",
    )
    assert isinstance(err, ConversionError)
    assert err.exit_code == 7
    assert err.xml_tag == "foo"
