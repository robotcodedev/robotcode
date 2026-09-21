"""Tests for test-level `[Metadata]` and `${TEST_METADATA}` (Robot Framework 7.5)."""

from typing import Callable

import pytest
from robot.model.metadata import Metadata as RobotMetadata

from robotcode.core.lsp.types import Location, Position, Range
from robotcode.robot.diagnostics.analyzer_result import AnalyzerResult
from robotcode.robot.utils import RF_VERSION
from robotcode.robot.utils.match import normalize_metadata_name

SUITE = """\
*** Test Cases ***
With Metadata
    [Metadata]    Issue    4409
    Log    ${TEST_METADATA}
"""

SUITE_AND_TEST_METADATA = """\
*** Settings ***
Metadata    A    1

*** Test Cases ***
With Metadata
    [Metadata]    B    2
    No Operation
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


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="test-level [Metadata] needs Robot Framework 7.5")
def test_test_metadata_is_indexed_separately_from_suite_metadata(
    analyzer_factory: Callable[..., AnalyzerResult],
) -> None:
    result = analyzer_factory(SUITE_AND_TEST_METADATA)

    # the keys are normalized, see the spelling tests below
    assert result.metadata_references == {
        "a": {Location("file:///test.robot", Range(Position(1, 12), Position(1, 13)))},
    }
    assert result.testcase_metadata_references == {
        "b": {Location("file:///test.robot", Range(Position(5, 18), Position(5, 19)))},
    }


def test_suite_metadata_never_lands_in_the_test_metadata_index(
    analyzer_factory: Callable[..., AnalyzerResult],
) -> None:
    result = analyzer_factory(SUITE_AND_TEST_METADATA)

    assert set(result.metadata_references) == {"a"}
    assert "a" not in result.testcase_metadata_references
    assert "b" not in result.metadata_references


SPELLINGS_OF_ONE_SUITE_METADATA_NAME = """\
*** Settings ***
Metadata    Owner Team    core
Metadata    owner_team    platform
Metadata    OWNERTEAM    all
Metadata    Issue    4409
"""


def test_spellings_of_a_suite_metadata_name_share_one_index_entry(
    analyzer_factory: Callable[..., AnalyzerResult],
) -> None:
    """Robot Framework treats metadata names case, space and underscore
    insensitively, so every spelling is a reference to the same name."""
    result = analyzer_factory(SPELLINGS_OF_ONE_SUITE_METADATA_NAME)

    assert set(result.metadata_references) == {"ownerteam", "issue"}
    assert sorted(loc.range.start.line for loc in result.metadata_references["ownerteam"]) == [1, 2, 3]
    assert [loc.range.start.line for loc in result.metadata_references["issue"]] == [4]


SPELLINGS_OF_ONE_TEST_METADATA_NAME = """\
*** Test Cases ***
First
    [Metadata]    Issue    4409
    [Metadata]    issue    4410
    No Operation

Second
    [Metadata]    IS_SUE    4411
    No Operation
"""


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="test-level [Metadata] needs Robot Framework 7.5")
def test_spellings_of_a_test_metadata_name_share_one_index_entry(
    analyzer_factory: Callable[..., AnalyzerResult],
) -> None:
    result = analyzer_factory(SPELLINGS_OF_ONE_TEST_METADATA_NAME)

    assert set(result.testcase_metadata_references) == {"issue"}
    assert sorted(loc.range.start.line for loc in result.testcase_metadata_references["issue"]) == [2, 3, 7]
    assert result.metadata_references == {}


# a no-break space and the German sharp s: what counts as the same name is Robot Framework's
# decision, and it differs between Robot Framework versions (`lower()` before 7.0, `casefold()` since)
SPECIAL_SPELLINGS = ["Owner Team", "Owner\u00a0Team", "owner_team", "Größe", "GRÖSSE"]


def test_index_has_one_entry_per_name_robot_framework_knows(
    analyzer_factory: Callable[..., AnalyzerResult],
) -> None:
    suite = "*** Settings ***\n" + "".join(f"Metadata    {name}    value\n" for name in SPECIAL_SPELLINGS)

    result = analyzer_factory(suite)

    robot_metadata = RobotMetadata((name, "value") for name in SPECIAL_SPELLINGS)
    assert len(result.metadata_references) == len(robot_metadata)
    assert sum(len(locations) for locations in result.metadata_references.values()) == len(SPECIAL_SPELLINGS)
    # the three spellings of `Owner Team` are one name on every Robot Framework version
    assert len(result.metadata_references[normalize_metadata_name("Owner Team")]) == 3


def test_metadata_setting_without_a_name_is_not_indexed(
    analyzer_factory: Callable[..., AnalyzerResult],
) -> None:
    """A `Metadata` setting with nothing after it is no metadata."""
    result = analyzer_factory(
        "*** Settings ***\nMetadata\n\n*** Test Cases ***\nA Test\n    [Metadata]\n    No Operation\n"
    )

    assert not result.metadata_references
    assert not result.testcase_metadata_references
