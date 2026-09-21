"""Acceptance tests for test/task `[Metadata]` in `robotcode discover`.

Robot Framework 7.5 added `[Metadata]` to tests and tasks. `discover`
carries it as a `metadata` object on test/task items, prints it with
`--show-metadata` in TEXT mode and matches it with `--search`. On older Robot
Framework versions no item has the key.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from pytest_mock import MockerFixture
from robot import running

from robotcode.robot.utils import RF_VERSION

from ..rf_markers import needs_rf_75
from .conftest import SUITES_DIR, CliRunner, JsonRunner, walk_test_items

_TESTS_SUITE = "metadata.robot"
_TASKS_SUITE = "metadata_tasks.robot"

# `Spaced Key` declares `Owner Team` before `Issue`; the expected order is
# Robot's (sorted by normalised name), not the author's.
_EXPECTED: Dict[str, Dict[str, Optional[Dict[str, str]]]] = {
    _TESTS_SUITE: {
        "Single Line": {"Issue": "4409"},
        "Spaced Key": {"Issue": "4410", "Owner Team": "core"},
        "Multi Line": {"Description": "first line\nsecond line"},
        "No Metadata": None,
        # a `[Metadata]` setting with nothing after it is no metadata
        "Empty Setting": None,
    },
    _TASKS_SUITE: {
        "Process Invoices": {"Issue": "4409", "Owner Team": "core"},
        "Sync Inventory": None,
    },
}

_COMMANDS = [
    pytest.param("all", _TESTS_SUITE, id="all-tests"),
    pytest.param("tests", _TESTS_SUITE, id="tests"),
    pytest.param("all", _TASKS_SUITE, id="all-tasks"),
    pytest.param("tasks", _TASKS_SUITE, id="tasks"),
]


def _leaves(subcommand: str, data: Any) -> List[Dict[str, Any]]:
    """`discover all` returns a tree, `tests`/`tasks` a flat list."""
    if subcommand == "all":
        return walk_test_items(data["items"][0])
    return list(data["items"])


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


@needs_rf_75
@pytest.mark.parametrize(("subcommand", "suite"), _COMMANDS)
def test_metadata_in_json(subcommand: str, suite: str, json_discover: JsonRunner) -> None:
    """Names keep the author's spelling, multi-line values are joined with
    `\\n`, and an item without metadata has no `metadata` key at all."""
    leaves = _leaves(subcommand, json_discover(subcommand, suite_path=SUITES_DIR / suite))

    expected = _EXPECTED[suite]
    assert {leaf["name"] for leaf in leaves} == set(expected)
    for leaf in leaves:
        wanted = expected[leaf["name"]]
        if wanted is None:
            assert "metadata" not in leaf
        else:
            assert list(leaf["metadata"].items()) == list(wanted.items())


@needs_rf_75
def test_metadata_tasks_are_task_items(json_discover: JsonRunner, metadata_tasks_suite: Path) -> None:
    data = json_discover("tasks", suite_path=metadata_tasks_suite)
    assert {item["type"] for item in data["items"]} == {"task"}


@pytest.mark.skipif(RF_VERSION >= (7, 5), reason="Robot Framework < 7.5 has no test metadata")
@pytest.mark.parametrize(("subcommand", "suite"), _COMMANDS)
def test_no_metadata_key_on_older_robot(subcommand: str, suite: str, json_discover: JsonRunner) -> None:
    leaves = _leaves(subcommand, json_discover(subcommand, suite_path=SUITES_DIR / suite))

    assert {leaf["name"] for leaf in leaves} == set(_EXPECTED[suite])
    assert all("metadata" not in leaf for leaf in leaves)


@pytest.mark.parametrize(("subcommand", "suite"), _COMMANDS)
def test_metadata_flag_does_not_change_json(subcommand: str, suite: str, json_discover: JsonRunner) -> None:
    """`--show-metadata` is a TEXT renderer hint; JSON always carries the data.

    Runs on every Robot Framework version: before 7.5 the flag is hidden
    from the help but still accepted."""
    default = json_discover(subcommand, suite_path=SUITES_DIR / suite)
    with_flag = json_discover(subcommand, "--show-metadata", suite_path=SUITES_DIR / suite)
    without_flag = json_discover(subcommand, "--no-show-metadata", suite_path=SUITES_DIR / suite)
    assert default == with_flag == without_flag


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subcommand", ["all", "tests", "tasks"])
def test_help_offers_the_metadata_flag_only_where_test_metadata_exists(
    subcommand: str, robotcode_cli: CliRunner
) -> None:
    out = robotcode_cli(["discover", subcommand, "--help"]).stdout

    assert "--show-tags / --no-show-tags" in out
    assert "--tags" not in out
    assert "--no-tags" not in out
    assert ("--show-metadata / --no-show-metadata" in out) == (RF_VERSION >= (7, 5))


@pytest.mark.parametrize(
    "option",
    [["--metadata", "Version:1.2"], ["--metadata=Version:1.2"]],
    ids=["separate", "joined"],
)
@pytest.mark.parametrize(("subcommand", "suite"), _COMMANDS)
def test_metadata_option_of_robot_is_passed_through(
    subcommand: str, suite: str, option: List[str], json_discover: JsonRunner, mocker: MockerFixture
) -> None:
    """`--metadata name:value` is Robot's own option for the metadata of the
    top level suite. The flag that shows the test metadata has another name
    so that Robot still gets it."""
    configure = mocker.spy(running.TestSuite, "configure")

    default = json_discover(subcommand, suite_path=SUITES_DIR / suite)
    with_robot_option = json_discover(subcommand, *option, suite_path=SUITES_DIR / suite)

    assert with_robot_option == default
    assert configure.call_args.kwargs["metadata"] == {"Version": "1.2"}


# ---------------------------------------------------------------------------
# TEXT
# ---------------------------------------------------------------------------


@needs_rf_75
@pytest.mark.parametrize(
    ("subcommand", "suite", "expected_line"),
    [
        pytest.param("all", _TESTS_SUITE, "    - _Metadata:_ Issue: 4410, Owner Team: core", id="all-tests"),
        pytest.param("tests", _TESTS_SUITE, "  - _Metadata:_ Issue: 4410, Owner Team: core", id="tests"),
        pytest.param("all", _TASKS_SUITE, "    - _Metadata:_ Issue: 4409, Owner Team: core", id="all-tasks"),
        pytest.param("tasks", _TASKS_SUITE, "  - _Metadata:_ Issue: 4409, Owner Team: core", id="tasks"),
    ],
)
def test_text_metadata_line_follows_the_flag(
    subcommand: str, suite: str, expected_line: str, text_discover: CliRunner
) -> None:
    """The default is the one of `--show-tags`: on for `all`, off for `tests` and `tasks`."""
    with_flag = text_discover(subcommand, "--show-metadata", suite_path=SUITES_DIR / suite)
    default = text_discover(subcommand, suite_path=SUITES_DIR / suite)
    without_flag = text_discover(subcommand, "--no-show-metadata", suite_path=SUITES_DIR / suite)

    assert expected_line in with_flag.stdout.splitlines()
    assert "_Metadata:_" not in without_flag.stdout
    if subcommand == "all":
        assert default.stdout == with_flag.stdout
    else:
        assert default.stdout == without_flag.stdout


@needs_rf_75
def test_text_metadata_line_count_matches_items_with_metadata(text_discover: CliRunner, metadata_suite: Path) -> None:
    """The test without metadata gets no `_Metadata:_` bullet."""
    out = text_discover("tests", "--show-metadata", suite_path=metadata_suite).stdout
    assert out.count("_Metadata:_") == 3


@needs_rf_75
def test_text_multi_line_value_stays_on_one_line(text_discover: CliRunner, metadata_suite: Path) -> None:
    out = text_discover("tests", "--show-metadata", suite_path=metadata_suite).stdout
    assert "  - _Metadata:_ Description: first line second line" in out.splitlines()


# ---------------------------------------------------------------------------
# --search
# ---------------------------------------------------------------------------


@needs_rf_75
def test_search_highlights_metadata_in_text(text_discover: CliRunner, metadata_suite: Path) -> None:
    out = text_discover("tests", "--show-metadata", "--search", "4409", suite_path=metadata_suite).stdout
    assert "  - _Metadata:_ Issue: `4409`" in out.splitlines()


@needs_rf_75
def test_search_matches_metadata_value(json_discover: JsonRunner, metadata_suite: Path) -> None:
    data = json_discover("tests", "--search", "4409", suite_path=metadata_suite)
    assert [item["name"] for item in data["items"]] == ["Single Line"]


@needs_rf_75
def test_search_matches_metadata_name(json_discover: JsonRunner, metadata_suite: Path) -> None:
    """Names match literally and case-insensitively, without Robot's
    metadata-key normalisation."""
    data = json_discover("tests", "--search", "owner team", suite_path=metadata_suite)
    assert [item["name"] for item in data["items"]] == ["Spaced Key"]

    data = json_discover("tests", "--search", "ownerteam", suite_path=metadata_suite)
    assert data["items"] == []


@needs_rf_75
def test_search_regex_matches_metadata_value(json_discover: JsonRunner, metadata_suite: Path) -> None:
    data = json_discover("tests", "--search-regex", r"first line\nsecond line$", suite_path=metadata_suite)
    assert [item["name"] for item in data["items"]] == ["Multi Line"]


@needs_rf_75
def test_search_matches_task_metadata(json_discover: JsonRunner, metadata_tasks_suite: Path) -> None:
    data = json_discover("tasks", "--search", "4409", suite_path=metadata_tasks_suite)
    assert [item["name"] for item in data["items"]] == ["Process Invoices"]
