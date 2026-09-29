"""Unit tests for selecting tests by their metadata (`robotcode.modifiers`).

The entries and patterns are plain functions of a name → value mapping and
run on every Robot Framework version; the modifiers need test-level
`[Metadata]` and therefore Robot Framework 7.5.
"""

import subprocess
import sys
import warnings
from pathlib import Path
from typing import Dict, List

import pytest
from robot import running
from robot.api import ExecutionResult
from robot.errors import DataError

from robotcode.modifiers import ByTestMetadata, ExcludedByTestMetadata
from robotcode.modifiers.metadata_modifiers import MetadataPattern, metadata_entries
from robotcode.robot.utils import RF_VERSION

needs_rf_75 = pytest.mark.skipif(RF_VERSION < (7, 5), reason="requires Robot Framework 7.5+ (test-level `[Metadata]`)")
before_rf_75 = pytest.mark.skipif(RF_VERSION >= (7, 5), reason="checks Robot Framework versions without test metadata")


# ---------------------------------------------------------------------------
# Entries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        pytest.param({"Issue": "4409"}, [("Issue", "4409")], id="single-line"),
        pytest.param({"Issue": "4409\n5769"}, [("Issue", "4409"), ("Issue", "5769")], id="multi-line"),
        pytest.param({"Issue": "4409    5769"}, [("Issue", "4409    5769")], id="multi-cell"),
        pytest.param({"Owner": ""}, [("Owner", "")], id="empty-value"),
        pytest.param({"Note": "first\n\nthird"}, [("Note", "first"), ("Note", "third")], id="empty-line"),
        pytest.param({"": ""}, [], id="unnamed"),
    ],
)
def test_metadata_entries(metadata: Dict[str, str], expected: List[object]) -> None:
    assert metadata_entries(metadata) == expected


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_HANS = {"Issue": "4409", "Author": "Hans Müller"}


@pytest.mark.parametrize(
    ("pattern", "metadata", "expected"),
    [
        pytest.param("Issue:4409", {"Issue": "4409\n5769"}, True, id="first-line"),
        pytest.param("Issue:5769", {"Issue": "4409\n5769"}, True, id="second-line"),
        pytest.param("Issue:4409", {"Issue": "4409    5769"}, False, id="cells-not-split"),
        pytest.param("Issue:4409*", {"Issue": "4409    5769"}, True, id="cells-with-glob"),
        pytest.param("Owner:*", {"Owner": ""}, True, id="value-less"),
        pytest.param("Issue:4409 AND Author:Hans*", _HANS, True, id="and"),
        pytest.param("Issue:4409 AND Author:Eva*", _HANS, False, id="and-not-all"),
        pytest.param("Author:Hans* NOT Reviewer:*", _HANS, True, id="not-without-reviewer"),
        pytest.param(
            "Author:Hans* NOT Reviewer:*", {**_HANS, "Reviewer": "Eva Schmidt"}, False, id="not-with-reviewer"
        ),
        pytest.param("NOT Reviewer:*", _HANS, True, id="leading-not"),
        pytest.param("NOT Reviewer:*", {"Reviewer": "Eva Schmidt"}, False, id="leading-not-excludes"),
        pytest.param("Issue:1 NOT Issue:2 NOT Issue:3", {"Issue": "1\n3"}, False, id="not-parts-are-or-ed"),
        pytest.param("*:4409", {"Requirement": "4409"}, True, id="any-name"),
        pytest.param("owner_team:core", {"Owner Team": "core"}, True, id="name-underscore"),
        pytest.param("OWNERTEAM:Core", {"Owner Team": "core"}, True, id="name-case-and-spaces"),
        pytest.param("Title:rock and roll", {"Title": "Rock AND Roll"}, True, id="lower-case-operator-word"),
        pytest.param("Title:a[[]b", {"Title": "a[b"}, True, id="literal-bracket"),
        pytest.param("Issue:1 OR Issue:2 AND Author:Eva", {"Issue": "1"}, True, id="precedence-a"),
        pytest.param("Issue:1 OR Issue:2 AND Author:Eva", {"Issue": "2", "Author": "Eva"}, True, id="precedence-b"),
        pytest.param("Issue:1 OR Issue:2 AND Author:Eva", {"Issue": "2", "Author": "Hans"}, False, id="precedence-c"),
        pytest.param("Build:${BUILD}", {"Build": "${BUILD}"}, True, id="unresolved-variable"),
        pytest.param("Issue:*", {}, False, id="no-metadata"),
    ],
)
def test_pattern_matches(pattern: str, metadata: Dict[str, str], expected: bool) -> None:
    assert MetadataPattern(pattern).match(metadata) is expected


@pytest.mark.parametrize(
    ("pattern", "metadata"),
    [
        ("Issue:CORE-123", {"Issue": "CORE-123"}),
        ("Issue:ANDROID-5", {"Issue": "ANDROID-5"}),
        ("Author:NORBERT", {"Author": "NORBERT"}),
    ],
)
def test_upper_case_values_are_literal(pattern: str, metadata: Dict[str, str]) -> None:
    """Robot's tag patterns would read these as `C OR E-123` etc. and warn."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert MetadataPattern(pattern).match(metadata)
    assert caught == []


@pytest.mark.parametrize(
    "pattern",
    [
        "Issue",
        "Title:Rock AND Roll",
        "Issue:4409 AND",
        "AND Issue:4409",
        "Issue:1 AND AND Issue:2",
        "Issue:1 NOT",
        "NOT",
        "",
        "   ",
    ],
)
def test_invalid_pattern_names_the_pattern(pattern: str) -> None:
    with pytest.raises(DataError, match="Invalid metadata pattern") as error:
        MetadataPattern(pattern)
    assert f"'{pattern}'" in str(error.value)


# ---------------------------------------------------------------------------
# Modifiers
# ---------------------------------------------------------------------------


def _suite() -> running.TestSuite:
    """Root with two tests and a child suite with one test; metadata on RF 7.5 only."""
    with_metadata = RF_VERSION >= (7, 5)
    suite = running.TestSuite(name="Root")
    for name, metadata in [("A", {"Issue": "4409"}), ("B", {"Issue": "4410", "Owner": "core"})]:
        suite.tests.create(name=name, **({"metadata": metadata} if with_metadata else {}))
    child = suite.suites.create(name="Child")
    child.tests.create(name="C", **({"metadata": {"Owner": "core"}} if with_metadata else {}))
    return suite


def _names(suite: running.TestSuite) -> List[str]:
    # `TestSuite.all_tests` does not exist on every supported Robot Framework version.
    return [test.name for test in suite.tests] + [name for child in suite.suites for name in _names(child)]


@needs_rf_75
def test_include_keeps_tests_matching_any_pattern() -> None:
    suite = _suite()
    suite.visit(ByTestMetadata("Issue:4409", "Issue:4410"))
    assert _names(suite) == ["A", "B"]
    assert [s.name for s in suite.suites] == []


@needs_rf_75
def test_exclude_removes_tests_matching_any_pattern() -> None:
    suite = _suite()
    suite.visit(ExcludedByTestMetadata("Owner:core"))
    assert _names(suite) == ["A"]


@needs_rf_75
def test_parsed_patterns_are_accepted() -> None:
    suite = _suite()
    suite.visit(ByTestMetadata(MetadataPattern("Owner:core NOT Issue:*")))
    assert _names(suite) == ["C"]


@needs_rf_75
@pytest.mark.parametrize("modifier", [ByTestMetadata, ExcludedByTestMetadata])
def test_invalid_pattern_fails_closed(modifier: type) -> None:
    """Robot would skip a modifier whose constructor fails and run every test."""
    instance = modifier("Issue")
    suite = _suite()
    with pytest.raises(DataError, match="Invalid metadata pattern 'Issue'"):
        suite.visit(instance)
    assert _names(suite) == []


@before_rf_75
def test_without_test_metadata_include_selects_nothing() -> None:
    suite = _suite()
    suite.visit(ByTestMetadata("Issue:*"))
    assert _names(suite) == []


@before_rf_75
def test_without_test_metadata_exclude_removes_nothing() -> None:
    suite = _suite()
    suite.visit(ExcludedByTestMetadata("Issue:*"))
    assert _names(suite) == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# Stand-alone use with plain `robot`
# ---------------------------------------------------------------------------

_SUITE = Path(__file__).parent / "suites" / "metadata_selection.robot"


def _run_robot(modifier: str, output_dir: Path) -> "subprocess.CompletedProcess[str]":
    # `;` separates the arguments from the name, because patterns contain `:`.
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "robot",
            "--prerunmodifier",
            modifier,
            "--output",
            str(output_dir / "output.xml"),
            "--report",
            "NONE",
            "--log",
            "NONE",
            str(_SUITE),
        ],
        cwd=str(output_dir),
        capture_output=True,
        text=True,
        timeout=120,
    )


@needs_rf_75
def test_plain_robot_runs_only_matching_tests(tmp_path: Path) -> None:
    process = _run_robot("robotcode.modifiers.ByTestMetadata;Issue:4409", tmp_path)
    assert process.returncode == 0, process.stdout + process.stderr

    result = ExecutionResult(str(tmp_path / "output.xml"))
    assert [test.name for test in result.suite.tests] == ["Issue 4409"]


@needs_rf_75
def test_plain_robot_stops_on_an_invalid_pattern(tmp_path: Path) -> None:
    process = _run_robot("robotcode.modifiers.ExcludedByTestMetadata;Issue", tmp_path)
    assert process.returncode == 252, process.stdout + process.stderr
    assert "Invalid metadata pattern 'Issue'" in process.stdout + process.stderr
    assert not (tmp_path / "output.xml").exists()
