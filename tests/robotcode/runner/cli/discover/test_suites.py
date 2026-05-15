"""Acceptance tests for `robotcode discover suites`."""

from pathlib import Path
from typing import Any

from .conftest import CliRunner, JsonRunner


def _names(items: list[Any]) -> set[str]:
    return {i["name"] for i in items}


def test_suites_returns_suite_items_only(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("suites", suite_path=flat_suite)
    assert all(item["type"] == "suite" for item in data["items"])


def test_suites_includes_nested_hierarchy(json_discover: JsonRunner, nested_suite: Path) -> None:
    """A 3-level tree → multiple suite entries (parents + leaves)."""
    data = json_discover("suites", suite_path=nested_suite)
    names = _names(data["items"])
    assert {"Nested", "Child", "A", "B"}.issubset(names)


def test_suites_text_lists_longnames_and_paths(robotcode_cli: CliRunner, nested_suite: Path) -> None:
    result = robotcode_cli(["discover", "suites", str(nested_suite)])
    assert "Nested" in result.stdout
    assert "Child" in result.stdout
    # Suite output ends with `(path)` per line.
    assert ".robot" in result.stdout or "nested" in result.stdout


def test_suites_text_full_paths(robotcode_cli: CliRunner, flat_suite: Path) -> None:
    abs_str = str(flat_suite.resolve())
    full = robotcode_cli(["discover", "suites", "--full-paths", str(flat_suite)])
    short = robotcode_cli(["discover", "suites", str(flat_suite)])
    assert abs_str in full.stdout
    assert abs_str not in short.stdout


def test_suites_include_tag_filter_prunes_leaf_suites(json_discover: JsonRunner, nested_suite: Path) -> None:
    """`--include no-such-tag` filters out every test → empty leaf
    suites disappear; only the root container survives."""
    data = json_discover("suites", "--include", "no-such-tag", suite_path=nested_suite)
    names = _names(data["items"])
    # Sub-suites (Child, A, B) get pruned because they have no surviving tests.
    assert "A" not in names
    assert "B" not in names
    assert "Child" not in names


def test_suites_search_keeps_ancestor_suites(json_discover: JsonRunner, nested_suite: Path) -> None:
    """`--search` is leaf-driven; surviving suite chain stays visible."""
    data = json_discover("suites", "--search", "In B One", suite_path=nested_suite)
    surviving = _names(data["items"])
    # Only the chain Root → Child → B survives, but as flat list of suite items.
    assert "B" in surviving
    assert "A" not in surviving


def test_suites_carry_source_field(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("suites", suite_path=flat_suite)
    # The Flat suite has source pointing at the file.
    flat = [s for s in data["items"] if s["name"] == "Flat"]
    assert flat, "expected the Flat suite item"
    assert Path(flat[0]["source"]).name == "flat.robot"
