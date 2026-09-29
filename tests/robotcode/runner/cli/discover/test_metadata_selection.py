"""Acceptance tests for `--by-test-metadata` / `--exclude-by-test-metadata` in
`robotcode discover` (Robot Framework 7.5+).

The pattern rules themselves are unit-tested in
`tests/robotcode/modifiers/test_metadata_modifiers.py`; these tests check
that every discover command applies them to the discovered tests.
"""

import json
import shutil
from pathlib import Path
from typing import Any, List

import pytest
from robot.errors import DATA_ERROR

from robotcode.robot.utils import RF_VERSION

from ..rf_markers import needs_rf_75
from .conftest import SUITES_DIR, CliRunner, JsonRunner, walk_suite_items, walk_test_items

_SUITE = SUITES_DIR / "metadata_selection.robot"
_DIR = SUITES_DIR / "metadata_dir"


def _test_names(json_discover: JsonRunner, *options: str) -> List[str]:
    data = json_discover("tests", *options, suite_path=_SUITE)
    return [item["name"] for item in data["items"]]


@needs_rf_75
@pytest.mark.parametrize(
    ("options", "expected"),
    [
        pytest.param(("-btm", "Issue:4409"), ["Issue 4409 Smoke", "Issue 4409"], id="include"),
        pytest.param(
            ("-btm", "Issue:4409", "-btm", "Issue:4410"),
            ["Issue 4409 Smoke", "Issue 4409", "Issue 4410"],
            id="several-patterns",
        ),
        pytest.param(
            ("--exclude-by-test-metadata", "Issue:*"),
            ["Requirement 4409", "Norbert", "Rock And Roll", "Owner Without Value", "Build", "No Metadata"],
            id="exclude",
        ),
        pytest.param(("--include", "smoke", "-btm", "Issue:4409"), ["Issue 4409 Smoke"], id="with-tag-selection"),
        pytest.param(
            ("-bl", "Metadata Selection.Issue 4409", "-btm", "Issue:4409"), ["Issue 4409"], id="with-longname"
        ),
        pytest.param(("-bl", "Metadata Selection.Issue 4410", "-btm", "Issue:4409"), [], id="with-other-longname"),
        pytest.param(("--search", "Smoke", "-btm", "Issue:4409"), ["Issue 4409 Smoke"], id="with-search"),
        pytest.param(("-btm", "Issue:5769"), ["Two Lines"], id="first-line"),
        pytest.param(("-btm", "Issue:5770"), ["Two Lines"], id="second-line"),
        pytest.param(("-btm", "Issue:5771"), [], id="cells-not-split"),
        pytest.param(("-btm", "Issue:5771*"), ["Two Cells"], id="cells-with-glob"),
        pytest.param(("-btm", "Owner:*"), ["Owner Without Value"], id="value-less"),
        pytest.param(("-btm", "Owner:core"), [], id="suite-metadata-not-matched"),
        pytest.param(("-btm", "Build:${BUILD}"), ["Build"], id="unresolved-variable"),
        pytest.param(("-btm", "Issue:4409 AND Author:Hans*"), ["Issue 4409 Smoke", "Issue 4409"], id="terms-with-and"),
        pytest.param(("-btm", "Author:Hans* NOT Reviewer:*"), ["Issue 4409"], id="missing-with-not"),
        pytest.param(("-btm", "*:4409"), ["Issue 4409 Smoke", "Issue 4409", "Requirement 4409"], id="any-name"),
        pytest.param(("-btm", "Issue:CORE-123"), ["Core Issue"], id="upper-case-issue"),
        pytest.param(("-btm", "Author:NORBERT"), ["Norbert"], id="upper-case-name"),
        pytest.param(("-btm", "Title:rock and roll"), ["Rock And Roll"], id="operator-word-in-value"),
        pytest.param(("-btm", "ISSUE:4411"), ["Lower Case Name"], id="name-spelling"),
    ],
)
def test_discover_tests_by_metadata(json_discover: JsonRunner, options: Any, expected: List[str]) -> None:
    assert _test_names(json_discover, *options) == expected


@needs_rf_75
def test_discover_all_by_metadata(json_discover: JsonRunner) -> None:
    data = json_discover("all", "-btm", "Issue:4410", suite_path=_SUITE)
    assert [item["name"] for item in walk_test_items(data["items"][0])] == ["Issue 4410"]


@needs_rf_75
def test_discover_tags_by_metadata(json_discover: JsonRunner) -> None:
    """The tag index is built from the selected tests only."""
    assert set(json_discover("tags", "-btm", "Issue:4409", suite_path=_SUITE)["tags"]) == {"smoke"}
    assert json_discover("tags", "-btm", "Issue:4410", suite_path=_SUITE)["tags"] == {}


@needs_rf_75
def test_discover_suites_drops_suites_without_selected_tests(json_discover: JsonRunner) -> None:
    data = json_discover("suites", "-btm", "Issue:4409", suite_path=_DIR)
    assert [item["name"] for item in data["items"]] == ["Metadata Dir", "First"]

    data = json_discover("all", "-ebtm", "Issue:4409", suite_path=_DIR)
    assert [item["name"] for item in walk_suite_items(data["items"][0])] == ["Metadata Dir", "Second"]


@needs_rf_75
def test_invalid_pattern_fails(robotcode_cli: CliRunner) -> None:
    result = robotcode_cli(
        ["--root", str(SUITES_DIR), "discover", "tests", "--by-test-metadata", "Issue", str(_SUITE)],
        expect_ok=False,
    )
    assert result.returncode == DATA_ERROR
    assert "Invalid metadata pattern 'Issue'" in result.stdout + result.stderr
    assert "Issue 4409" not in result.stdout


_PROFILES = """\
[profiles.issue]
pre-run-modifiers = { "robotcode.modifiers.ByTestMetadata" = ["Issue:4409"] }

[profiles.invalid]
pre-run-modifiers = { "robotcode.modifiers.ByTestMetadata" = ["Issue"] }
"""


@needs_rf_75
@pytest.mark.parametrize(("profile", "expected"), [("issue", ["Single Line"]), ("invalid", [])])
def test_profile_with_the_pre_run_modifier(
    robotcode_cli: CliRunner, tmp_path: Path, profile: str, expected: List[str]
) -> None:
    """`robot.toml` passes the pattern as `ByTestMetadata;Issue:4409`, since it contains `:`."""
    (tmp_path / "robot.toml").write_text(_PROFILES, encoding="utf-8")
    suite = tmp_path / "metadata.robot"
    shutil.copyfile(SUITES_DIR / "metadata.robot", suite)

    result = robotcode_cli(
        ["--root", str(tmp_path), "--profile", profile, "--format", "json", "discover", "tests", str(suite)]
    )
    data = json.loads(result.stdout)
    assert [item["name"] for item in data["items"]] == expected

    messages = [d["message"] for diagnostics in (data.get("diagnostics") or {}).values() for d in diagnostics]
    if profile == "invalid":
        assert any("Invalid metadata pattern 'Issue'" in message for message in messages), messages
    else:
        assert not any("metadata pattern" in message for message in messages), messages


_BEFORE_RF_75 = pytest.mark.skipif(RF_VERSION >= (7, 5), reason="checks Robot Framework versions without test metadata")


@_BEFORE_RF_75
def test_options_are_accepted_before_rf_75(json_discover: JsonRunner, flat_suite: Path) -> None:
    """No test has metadata there: including selects nothing, excluding removes nothing."""
    everything = json_discover("tests", suite_path=flat_suite)["items"]
    assert json_discover("tests", "-ebtm", "*:*", suite_path=flat_suite)["items"] == everything
    assert json_discover("tests", "-btm", "*:*", suite_path=flat_suite).get("items", []) == []


@_BEFORE_RF_75
def test_metadata_index_before_rf_75_lists_only_suite_metadata(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("metadata", "--values", suite_path=flat_suite)
    assert data["metadata"] == {}
    assert list(data["suiteMetadata"]) == ["OwnerProbe"]
