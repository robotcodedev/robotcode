"""Tests for test-level `[Metadata]` and `${TEST_METADATA}` (Robot Framework 7.5)."""

from typing import Callable

from robotcode.robot.diagnostics.analyzer_result import AnalyzerResult
from robotcode.robot.utils import RF_VERSION

SUITE = """\
*** Test Cases ***
With Metadata
    [Metadata]    Issue    4409
    Log    ${TEST_METADATA}
"""


def test_test_metadata_diagnostics_follow_the_robot_framework_version(
    analyzer_factory: Callable[..., AnalyzerResult],
) -> None:
    result = analyzer_factory(SUITE)

    if RF_VERSION >= (7, 5):
        assert result.diagnostics == []
    else:
        assert sorted(str(d.code) for d in result.diagnostics) == ["TokenError", "VariableNotFound"]

        setting_error = next(d for d in result.diagnostics if str(d.code) == "TokenError")
        assert setting_error.message.startswith("Setting 'Metadata' is not allowed")
        assert setting_error.range.start.line == 2

        variable_error = next(d for d in result.diagnostics if str(d.code) == "VariableNotFound")
        assert variable_error.message == "Variable '${TEST_METADATA}' not found."
        assert variable_error.range.start.line == 3
