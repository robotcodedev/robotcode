"""Shared Robot-Framework-version skip markers for the `runner/cli` tests.

Single source of truth so sibling packages (`results`, `discover`, ...)
don't each redefine the same `skipif` condition.
"""

import pytest

from robotcode.robot.utils import RF_VERSION

needs_rf_70 = pytest.mark.skipif(
    RF_VERSION < (7, 0),
    reason="requires Robot Framework 7.0+ (VAR, JSON output, attribute renames, "
    "singular-header deprecation warning, arg-spec parse diagnostics)",
)
needs_rf_72 = pytest.mark.skipif(
    RF_VERSION < (7, 2),
    reason="requires Robot Framework 7.2+ (GROUP block)",
)
