"""Acceptance tests for `robotcode discover tests`."""

from pathlib import Path
from typing import Any

from .conftest import CliRunner, JsonRunner


def _names(items: list[Any]) -> set[str]:
    return {i["name"] for i in items}


# ---------------------------------------------------------------------------
# JSON structure
# ---------------------------------------------------------------------------


def test_tests_returns_flat_test_list(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("tests", suite_path=flat_suite)
    assert isinstance(data["items"], list)
    assert all(item["type"] == "test" for item in data["items"])


def test_tests_excludes_suite_items(json_discover: JsonRunner, nested_suite: Path) -> None:
    data = json_discover("tests", suite_path=nested_suite)
    types = {item["type"] for item in data["items"]}
    assert types == {"test"}


def test_tests_empty_on_tasks_only_suite(json_discover: JsonRunner, tasks_suite: Path) -> None:
    """A file with only `*** Tasks ***` produces no test items."""
    data = json_discover("tests", suite_path=tasks_suite)
    assert data["items"] == []


def test_tests_in_mixed_dir_returns_only_tests(json_discover: JsonRunner, mixed_suite: Path) -> None:
    """When a workspace mixes Tests and Tasks files, `tests` shows only tests."""
    data = json_discover("tests", suite_path=mixed_suite)
    assert _names(data["items"]) == {"Test One", "Test Two"}


# ---------------------------------------------------------------------------
# --tags
# ---------------------------------------------------------------------------


def test_tests_tags_field_present_when_test_has_tags(json_discover: JsonRunner, flat_suite: Path) -> None:
    """Tag data is always carried in JSON (the `--tags` flag is a TEXT renderer hint)."""
    data = json_discover("tests", suite_path=flat_suite)
    tagged = [t for t in data["items"] if t.get("tags")]
    assert tagged, "flat.robot has tagged tests"


def test_tests_text_tags_flag_shows_tag_line(robotcode_cli: CliRunner, flat_suite: Path) -> None:
    with_tags = robotcode_cli(["discover", "tests", "--tags", str(flat_suite)])
    without = robotcode_cli(["discover", "tests", str(flat_suite)])
    assert "Tags:" in with_tags.stdout
    assert "Tags:" not in without.stdout


# ---------------------------------------------------------------------------
# --full-paths
# ---------------------------------------------------------------------------


def test_tests_text_full_paths_uses_absolute(robotcode_cli: CliRunner, flat_suite: Path) -> None:
    abs_str = str(flat_suite.resolve())
    full = robotcode_cli(["discover", "tests", "--full-paths", str(flat_suite)])
    short = robotcode_cli(["discover", "tests", str(flat_suite)])
    assert abs_str in full.stdout
    assert abs_str not in short.stdout


# ---------------------------------------------------------------------------
# Robot-native filters
# ---------------------------------------------------------------------------


def test_tests_include_tag_filter(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("tests", "--include", "smoke", suite_path=flat_suite)
    assert _names(data["items"]) == {"Login Smoke", "Reporting Summary"}


def test_tests_exclude_tag_filter(json_discover: JsonRunner, flat_suite: Path) -> None:
    """`--exclude smoke` removes the two smoke-tagged tests."""
    data = json_discover("tests", "--exclude", "smoke", suite_path=flat_suite)
    survivors = _names(data["items"])
    assert "Login Smoke" not in survivors
    assert "Reporting Summary" not in survivors


def test_tests_suite_glob_filter(json_discover: JsonRunner, nested_suite: Path) -> None:
    """`--suite "*.A"` selects only the leaf suite `A`'s tests."""
    data = json_discover("tests", "--suite", "*.A", suite_path=nested_suite)
    assert _names(data["items"]) == {"Test In A One", "Test In A Two"}


# ---------------------------------------------------------------------------
# TEXT smoke
# ---------------------------------------------------------------------------


def test_tests_text_lists_names_and_paths(robotcode_cli: CliRunner, flat_suite: Path) -> None:
    """TEXT output: H1 heading, bullets per test, `## Statistics` table footer."""
    result = robotcode_cli(["discover", "tests", str(flat_suite)])
    assert "# Tests" in result.stdout
    assert "Login Smoke" in result.stdout
    assert "## Statistics" in result.stdout


def test_tests_text_tags_emit_italic_label_sub_bullet(robotcode_cli: CliRunner, flat_suite: Path) -> None:
    """`discover tests --tags` adds `- _Tags:_` italic-label sub-bullets
    beneath each test bullet (style convention: bold names, italic labels)."""
    out = robotcode_cli(["discover", "tests", "--tags", str(flat_suite)]).stdout
    assert "- _Tags:_" in out
    # Tag values are inline-code-spanned tokens.
    assert "`smoke`" in out
