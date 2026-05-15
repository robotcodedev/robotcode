"""Cross-subcommand acceptance tests for the shared Robot-native filters.

These tests parametrize each filter over the discover subcommands that
support it, ensuring `--include`/`--exclude`/`--suite`/`-bl`/`-ebl` all
narrow the result set consistently regardless of which subcommand is
filtering.
"""

from pathlib import Path
from typing import Any, Dict

import pytest

from .conftest import JsonRunner, walk_test_items


def _effective_test_count(subcommand: str, data: Dict[str, Any]) -> int:
    """Return the number of surviving leaf items for a given subcommand's JSON."""
    if subcommand == "all":
        return len(walk_test_items(data["items"][0]))
    if subcommand in ("tests", "tasks"):
        return len(data.get("items", []))
    if subcommand == "suites":
        # Suites are intermediate nodes; for "non-empty" counts we sum the
        # surviving leaves under each suite. But suites itself doesn't
        # expose test counts in its JSON, so the cross-cutting filter
        # tests use `tests`/`all` for leaf counts and `suites` separately.
        return len(data.get("items", []))
    if subcommand == "tags":
        return sum(len(v) for v in data.get("tags", {}).values())
    raise AssertionError(f"unhandled subcommand {subcommand!r}")


# ---------------------------------------------------------------------------
# --include / --exclude
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subcommand", ["all", "tests"])
def test_include_tag_filter_uniform(subcommand: str, json_discover: JsonRunner, flat_suite: Path) -> None:
    """`--include smoke` keeps exactly the two smoke-tagged tests in flat.robot."""
    data = json_discover(subcommand, "--include", "smoke", suite_path=flat_suite)
    assert _effective_test_count(subcommand, data) == 2


@pytest.mark.parametrize("subcommand", ["all", "tests"])
def test_exclude_tag_filter_uniform(subcommand: str, json_discover: JsonRunner, flat_suite: Path) -> None:
    """`--exclude smoke` removes the two smoke-tagged tests; 4 remain from 6 total."""
    data = json_discover(subcommand, "--exclude", "smoke", suite_path=flat_suite)
    assert _effective_test_count(subcommand, data) == 4


@pytest.mark.parametrize("subcommand", ["all", "tests"])
def test_no_filter_match_yields_empty(subcommand: str, json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover(subcommand, "--include", "no-such-tag", suite_path=flat_suite)
    assert _effective_test_count(subcommand, data) == 0


# ---------------------------------------------------------------------------
# --suite / --test (Robot-native globs on names)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subcommand", ["all", "tests"])
def test_suite_glob_filter_uniform(subcommand: str, json_discover: JsonRunner, nested_suite: Path) -> None:
    """`--suite *.A` selects only the leaf suite `A` (2 tests in nested_suite)."""
    data = json_discover(subcommand, "--suite", "*.A", suite_path=nested_suite)
    assert _effective_test_count(subcommand, data) == 2


@pytest.mark.parametrize("subcommand", ["all", "tests"])
def test_test_glob_filter_uniform(subcommand: str, json_discover: JsonRunner, flat_suite: Path) -> None:
    """`--test Login*` picks the two Login-named tests."""
    data = json_discover(subcommand, "--test", "Login*", suite_path=flat_suite)
    assert _effective_test_count(subcommand, data) == 2


# ---------------------------------------------------------------------------
# -bl / -ebl (longname-based)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subcommand", ["all", "tests"])
def test_by_longname_picks_single_test(subcommand: str, json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover(subcommand, "-bl", "Flat.Login Smoke", suite_path=flat_suite)
    assert _effective_test_count(subcommand, data) == 1


@pytest.mark.parametrize("subcommand", ["all", "tests"])
def test_exclude_by_longname_removes_single_test(subcommand: str, json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover(subcommand, "-ebl", "Flat.Login Smoke", suite_path=flat_suite)
    assert _effective_test_count(subcommand, data) == 5


# ---------------------------------------------------------------------------
# Filter chain intersection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subcommand", ["all", "tests"])
def test_filter_chain_intersects_include_and_exclude(
    subcommand: str, json_discover: JsonRunner, flat_suite: Path
) -> None:
    """`-i smoke -e bug1` keeps smoke-tagged tests that aren't tagged bug1."""
    data = json_discover(subcommand, "--include", "smoke", "--exclude", "bug1", suite_path=flat_suite)
    # Login Smoke has smoke + bug 1 → excluded. Reporting Summary has smoke + BUG1
    # → also excluded. So 0 surviving tests.
    assert _effective_test_count(subcommand, data) == 0
