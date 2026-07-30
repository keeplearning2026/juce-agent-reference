"""Unified exception hierarchy for the JUCE reference generator.

Every error carries a stable exit code so the CLI can report it
without scattering magic numbers across the codebase.
"""

from __future__ import annotations


class JuceReferenceError(Exception):
    """Base for all generator exceptions."""

    exit_code: int = 1

    def __init__(
        self,
        message: str,
        *,
        phase: str | None = None,
        command: str | None = None,
        file_path: str | None = None,
        xml_tag: str | None = None,
        compound_refid: str | None = None,
        member_refid: str | None = None,
        symbol: str | None = None,
        original: BaseException | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message)
        self.phase = phase
        self.command = command
        self.file_path = file_path
        self.xml_tag = xml_tag
        self.compound_refid = compound_refid
        self.member_refid = member_refid
        self.symbol = symbol
        self.original = original
        self.suggestion = suggestion


class CliUsageError(JuceReferenceError):
    """Invalid command-line arguments or input."""

    exit_code = 2


class EnvironmentCheckError(JuceReferenceError):
    """Required tool, package, or env setting missing."""

    exit_code = 3


class JuceSourceError(JuceReferenceError):
    """JUCE checkout validation failed."""

    exit_code = 4


class DoxygenExecutionError(JuceReferenceError):
    """Doxygen invocation failed."""

    exit_code = 5


class XmlValidationError(JuceReferenceError):
    """Doxygen XML failed schema or integrity checks."""

    exit_code = 6


class ConversionError(JuceReferenceError):
    """XML → canonical IR conversion failed."""

    exit_code = 7


class GenerationError(JuceReferenceError):
    """Markdown or index generation failed."""

    exit_code = 8


class OutputValidationError(JuceReferenceError):
    """Generated output failed validation."""

    exit_code = 9


class SmokeTestError(JuceReferenceError):
    """Real-JUCE smoke test failed."""

    exit_code = 10


class SearchQualityError(JuceReferenceError):
    """Search-quality thresholds not met."""

    exit_code = 11


class DeterminismError(JuceReferenceError):
    """Deterministic-output test failed."""

    exit_code = 12


class PublishError(JuceReferenceError):
    """Atomic publish failed."""

    exit_code = 13


class VersionVerificationError(JuceReferenceError):
    """Version / commit verification failed."""

    exit_code = 14


class RepositoryStateError(JuceReferenceError):
    """Git working tree or repository state is unacceptable."""

    exit_code = 15


class ExternalBlockerError(JuceReferenceError):
    """Unrecoverable external condition — only for true blockers."""

    exit_code = 20


class UnsupportedSemanticNodeError(ConversionError):
    """A Doxygen XML node carries semantic content we cannot yet handle."""

    exit_code = 7
