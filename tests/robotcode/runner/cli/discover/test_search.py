"""Acceptance tests for `--search` / `--search-regex` on `discover`.

The flag pair filters via a `SearchModifier` SuiteVisitor wired into the
same `prerunmodifier` slot as `ByLongName` / `ExcludedByLongName`, so the
search lives upstream of the collector — `Statistics`, JSON `items` and
the tag aggregate all reflect the filtered set automatically.
"""

from pathlib import Path
from typing import Any, Dict, Iterable, List

import pytest

from .conftest import CliRunner, JsonRunner


def _names(items: Iterable[Dict[str, Any]]) -> List[str]:
    return [i["name"] for i in items]


def _walk_test_names(item: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    if item.get("type") in ("test", "task"):
        out.append(item["name"])
    for child in item.get("children") or []:
        out.extend(_walk_test_names(child))
    return out


# ---------------------------------------------------------------------------
# Substring search
# ---------------------------------------------------------------------------


def test_search_filters_tests_by_name(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("tests", "--search", "Login", suite_path=flat_suite)
    assert sorted(_names(data["items"])) == ["Login Regression", "Login Smoke"]


def test_search_is_case_insensitive(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("tests", "--search", "login", suite_path=flat_suite)
    assert sorted(_names(data["items"])) == ["Login Regression", "Login Smoke"]


def test_search_against_tags_is_normalisation_aware(json_discover: JsonRunner, flat_suite: Path) -> None:
    """`bug 1` matches tests tagged `bug 1`, `bug_1` and `BUG1`."""
    data = json_discover("tests", "--search", "bug 1", suite_path=flat_suite)
    assert sorted(_names(data["items"])) == ["Login Regression", "Login Smoke", "Reporting Summary"]


def test_search_finds_keyword_argument_in_test_body(json_discover: JsonRunner, flat_suite: Path) -> None:
    """A substring inside a keyword argument finds the test that calls it."""
    data = json_discover("tests", "--search", "UNIQUE_BODY_TOKEN_xyz", suite_path=flat_suite)
    assert _names(data["items"]) == ["Body Probe"]


def test_search_finds_keyword_name_in_test_body(json_discover: JsonRunner, flat_suite: Path) -> None:
    """A keyword name not in any test's title still finds the calling test."""
    data = json_discover("tests", "--search", "Set Test Variable", suite_path=flat_suite)
    assert _names(data["items"]) == ["Body Probe"]


def test_search_finds_for_loop_value(json_discover: JsonRunner, flat_suite: Path) -> None:
    """Values inside a FOR loop are reachable through the body walker."""
    data = json_discover("tests", "--search", "fizz", suite_path=flat_suite)
    assert _names(data["items"]) == ["Body Probe"]


def test_search_finds_test_documentation(json_discover: JsonRunner, flat_suite: Path) -> None:
    """`[Documentation]` text on a test is part of the search target set."""
    data = json_discover("tests", "--search", "DOC_PROBE_TOKEN", suite_path=flat_suite)
    assert _names(data["items"]) == ["Documented Probe"]


def test_search_filters_files_by_path_substring(robotcode_cli: CliRunner, flat_suite: Path) -> None:
    """`discover files` filters the file list by path substring."""
    flat_match = robotcode_cli(["discover", "files", "--search", "flat", str(flat_suite.parent)])
    assert "flat.robot" in flat_match.stdout
    assert "child" not in flat_match.stdout

    no_match = robotcode_cli(["discover", "files", "--search", "no-such-thing", str(flat_suite.parent)])
    assert "flat.robot" not in no_match.stdout


def test_search_no_match_yields_empty_items(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("tests", "--search", "no-such-thing", suite_path=flat_suite)
    assert data["items"] == []


# ---------------------------------------------------------------------------
# Regex search
# ---------------------------------------------------------------------------


def test_search_regex_is_case_sensitive_by_default(json_discover: JsonRunner, flat_suite: Path) -> None:
    upper = json_discover("tests", "--search-regex", "Login", suite_path=flat_suite)
    assert {n for n in _names(upper["items"])} == {"Login Smoke", "Login Regression"}

    lower = json_discover("tests", "--search-regex", "^login", suite_path=flat_suite)
    assert lower["items"] == []


def test_search_regex_inline_case_insensitive(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("tests", "--search-regex", "(?i)^login", suite_path=flat_suite)
    assert sorted(_names(data["items"])) == ["Login Regression", "Login Smoke"]


# ---------------------------------------------------------------------------
# Tree pruning in `discover all`
# ---------------------------------------------------------------------------


def test_search_in_all_prunes_tree_and_keeps_ancestors(json_discover: JsonRunner, nested_suite: Path) -> None:
    """A single test match leaves only its full ancestor chain in the tree."""
    data = json_discover("all", "--search", "In B One", suite_path=nested_suite)

    root_items = data["items"]
    assert len(root_items) == 1
    workspace = root_items[0]

    # The full path: workspace -> Nested -> Child -> B -> Test In B One.
    # No other branches survive.
    leaf_names = _walk_test_names(workspace)
    assert leaf_names == ["Test In B One"]


def test_search_in_all_empty_when_no_match(json_discover: JsonRunner, nested_suite: Path) -> None:
    data = json_discover("all", "--search", "no-such-name", suite_path=nested_suite)
    workspace = data["items"][0]
    assert _walk_test_names(workspace) == []


# ---------------------------------------------------------------------------
# `discover tags` reflects the filtered suite
# ---------------------------------------------------------------------------


def test_search_filters_tags_via_underlying_tests(json_discover: JsonRunner, flat_suite: Path) -> None:
    """Searching `Login` keeps only tags that survive on at least one matching test."""
    data = json_discover("tags", "--search", "Login", suite_path=flat_suite)
    # Login Smoke -> smoke, bug1.  Login Regression -> regression, bug1.
    # `slow` belongs only to `Plain Other`, which doesn't match.
    assert sorted(data["tags"].keys()) == ["bug1", "regression", "smoke"]


# ---------------------------------------------------------------------------
# UsageError paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subcommand", ["all", "tests", "tasks", "suites", "tags"])
def test_search_and_search_regex_are_mutually_exclusive(
    subcommand: str, robotcode_cli: CliRunner, flat_suite: Path
) -> None:
    result = robotcode_cli(
        ["discover", subcommand, "--search", "x", "--search-regex", "y", str(flat_suite)],
        expect_ok=False,
    )
    assert result.returncode != 0
    assert "mutually exclusive" in result.stderr.lower()


@pytest.mark.parametrize("subcommand", ["all", "tests", "tasks", "suites", "tags"])
def test_invalid_regex_yields_usage_error(subcommand: str, robotcode_cli: CliRunner, flat_suite: Path) -> None:
    result = robotcode_cli(
        ["discover", subcommand, "--search-regex", "[unclosed", str(flat_suite)],
        expect_ok=False,
    )
    assert result.returncode != 0
    assert "search-regex" in result.stderr.lower() or "invalid" in result.stderr.lower()


# ---------------------------------------------------------------------------
# JSON filtersApplied echo
# ---------------------------------------------------------------------------


def test_filters_applied_substring_echoed_in_json(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("tests", "--search", "Login", suite_path=flat_suite)
    assert data.get("filtersApplied") == {"search": "Login"}


def test_filters_applied_regex_echoed_in_json(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("tests", "--search-regex", "^Login", suite_path=flat_suite)
    assert data.get("filtersApplied") == {"search-regex": "^Login"}


def test_no_filters_applied_when_search_absent(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("tests", suite_path=flat_suite)
    assert "filtersApplied" not in data
