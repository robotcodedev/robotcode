"""Acceptance tests for `robotcode discover tags`."""

from pathlib import Path

from .conftest import CliRunner, JsonRunner


def test_tags_returns_dict(json_discover: JsonRunner, tagged_suite: Path) -> None:
    """JSON shape: `{"tags": {tag_name: [TestItem, ...]}}`."""
    data = json_discover("tags", suite_path=tagged_suite)
    assert isinstance(data["tags"], dict)
    assert all(isinstance(v, list) for v in data["tags"].values())


def test_tags_normalized_keys_default(json_discover: JsonRunner, tagged_suite: Path) -> None:
    """`bug 1` / `bug_1` / `BUG1` collapse to a single `bug1` entry."""
    data = json_discover("tags", suite_path=tagged_suite)
    keys = set(data["tags"].keys())
    # `bug1` is the normalised form for all three variants in tagged.robot.
    assert "bug1" in keys
    assert "bug 1" not in keys
    assert "bug_1" not in keys
    assert "BUG1" not in keys


def test_tags_not_normalized_keeps_originals(json_discover: JsonRunner, tagged_suite: Path) -> None:
    data = json_discover("tags", "--not-normalized", suite_path=tagged_suite)
    keys = set(data["tags"].keys())
    # Now the original forms come through unchanged.
    assert {"bug-1", "bug_1", "BUG1", "bug 1"}.issubset(keys)


def test_tags_text_default_lists_only_tag_names(robotcode_cli: CliRunner, tagged_suite: Path) -> None:
    """Without `--tests`/`--tasks`, TEXT just lists tag names."""
    result = robotcode_cli(["discover", "tags", str(tagged_suite)])
    assert "smoke" in result.stdout
    # No `Test: ...` indentation expected.
    assert "    Test:" not in result.stdout


def test_tags_text_tests_flag_expands_children(robotcode_cli: CliRunner, tagged_suite: Path) -> None:
    """`--tests` adds indented `Test: ...` lines under each tag."""
    result = robotcode_cli(["discover", "tags", "--tests", str(tagged_suite)])
    assert "    Test:" in result.stdout


def test_tags_text_tasks_flag_expands_tasks(robotcode_cli: CliRunner, tasks_suite: Path) -> None:
    """Need --root to escape the project's robot.toml `rpa=false`,
    otherwise Robot's auto-detect of `*** Tasks ***` is suppressed."""
    result = robotcode_cli(["--root", str(tasks_suite.parent), "discover", "tags", "--tasks", str(tasks_suite)])
    assert "    Task:" in result.stdout


def test_tags_filter_chain_applies_before_aggregation(json_discover: JsonRunner, tagged_suite: Path) -> None:
    """`--include smoke` narrows the underlying test set; the resulting
    tag dict only contains tags present on at least one surviving test."""
    data = json_discover("tags", "--include", "smoke", suite_path=tagged_suite)
    keys = set(data["tags"].keys())
    # `slow` (only on `Slow Path`) is not in the smoke-tagged subset.
    assert "slow" not in keys


def test_tags_dict_values_are_testitems(json_discover: JsonRunner, tagged_suite: Path) -> None:
    """Each entry is a list of TestItem dicts (type, longname, source, …)."""
    data = json_discover("tags", suite_path=tagged_suite)
    for items in data["tags"].values():
        for item in items:
            assert "type" in item
            assert "longname" in item
            assert "source" in item
