"""Central logging configuration for the JUCE reference generator."""

from __future__ import annotations

import logging
import sys

LOGGER = logging.getLogger("juce_reference")


def setup_logging(
    verbose: bool = False,
    no_color: bool = False,
) -> None:
    """Configure the root logger for the generator.

    Args:
        verbose: Enable DEBUG level output.
        no_color: Strip ANSI codes from output (for CI).
    """
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    fmt = "%(levelname)s: %(message)s" if verbose else "%(message)s"
    if not no_color:
        fmt = fmt  # rich handles colour; plain handler is just text

    handler.setFormatter(logging.Formatter(fmt))
    LOGGER.handlers.clear()
    LOGGER.addHandler(handler)
    LOGGER.setLevel(level)
