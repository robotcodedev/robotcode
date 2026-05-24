"""Acceptance tests for `robotcode discover all`.

`all` is the broadest discover subcommand: it returns the complete
workspace tree (workspace → suites → tests/tasks), and is the only
subcommand whose JSON output is a nested `ResultItem` tree rather than
a flat list.
"""

from pathlib import Path

from .conftest import (
    CliRunner,
    JsonRunner,
    walk_suite_items,
    walk_test_items,
)

# ---------------------------------------------------------------------------
# JSON structure
# ---------------------------------------------------------------------------


def test_all_returns_workspace_root(json_discover: JsonRunner, flat_suite: Path) -> None:
    """The top-level `items` always contains one workspace TestItem."""
    data = json_discover("all", suite_path=flat_suite)
    assert len(data["items"]) == 1
    assert data["items"][0]["type"] == "workspace"


def test_all_tree_contains_all_tests(json_discover: JsonRunner, nested_suite: Path) -> None:
    """nested_suite has 4 tests across two leaf suites — they all show up."""
    data = json_discover("all", suite_path=nested_suite)
    leaves = walk_test_items(data["items"][0])
    assert {leaf["name"] for leaf in leaves} == {
        "Test In A One",
        "Test In A Two",
        "Test In B One",
        "Test In B Two",
    }


def test_all_test_items_carry_lineno(json_discover: JsonRunner, flat_suite: Path) -> None:
    leaves = walk_test_items(json_discover("all", suite_path=flat_suite)["items"][0])
    assert leaves, "expected at least one test leaf in the tree"
    assert all(leaf.get("lineno") is not None for leaf in leaves)


def test_all_workspace_id_is_an_absolute_path(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("all", suite_path=flat_suite)
    workspace_id = data["items"][0]["id"]
    assert Path(workspace_id).is_absolute()


# ---------------------------------------------------------------------------
# --tags / --no-tags
# ---------------------------------------------------------------------------


def test_all_json_includes_tag_field_for_tagged_tests(json_discover: JsonRunner, flat_suite: Path) -> None:
    """JSON always carries the `tags` field on tests; `--tags` only
    affects the TEXT renderer."""
    data = json_discover("all", suite_path=flat_suite)
    tests_with_tags = [t for t in walk_test_items(data["items"][0]) if t.get("tags")]
    assert tests_with_tags, "expected at least one tagged test in flat.robot"


def test_all_text_tags_flag_controls_tag_display(robotcode_cli: CliRunner, flat_suite: Path) -> None:
    """`--tags` (default) prints a `Tags:` line per test; `--no-tags` doesn't."""
    with_tags = robotcode_cli(["discover", "all", str(flat_suite)])
    no_tags = robotcode_cli(["discover", "all", "--no-tags", str(flat_suite)])
    assert "Tags:" in with_tags.stdout
    assert "Tags:" not in no_tags.stdout


# ---------------------------------------------------------------------------
# --full-paths
# ---------------------------------------------------------------------------


def test_all_json_source_is_always_absolute(json_discover: JsonRunner, flat_suite: Path) -> None:
    """`source` (absolute) and `relSource` (relative) coexist in JSON;
    `--full-paths` is a TEXT-rendering hint, not a JSON-schema change."""
    data = json_discover("all", suite_path=flat_suite)
    leaves = walk_test_items(data["items"][0])
    assert leaves, "expected leaves"
    for leaf in leaves:
        assert Path(leaf["source"]).is_absolute()
        assert not leaf["relSource"].startswith("/")


def test_all_text_full_paths_uses_absolute(robotcode_cli: CliRunner, flat_suite: Path) -> None:
    """`--full-paths` in TEXT mode prints the absolute path; the default
    prints the relative one."""
    abs_str = str(flat_suite.resolve())
    full = robotcode_cli(["discover", "all", "--full-paths", str(flat_suite)])
    short = robotcode_cli(["discover", "all", str(flat_suite)])
    assert abs_str in full.stdout
    assert abs_str not in short.stdout


# ---------------------------------------------------------------------------
# Hierarchy and counts
# ---------------------------------------------------------------------------


def test_all_nested_suites_appear_in_tree(json_discover: JsonRunner, nested_suite: Path) -> None:
    """A 3-level hierarchy should surface multiple suite entries."""
    data = json_discover("all", suite_path=nested_suite)
    suites = walk_suite_items(data["items"][0])
    suite_names = {s["name"] for s in suites}
    assert {"Nested", "Child", "A", "B"}.issubset(suite_names)


# ---------------------------------------------------------------------------
# TEXT output
# ---------------------------------------------------------------------------


def test_all_text_lists_suites_tests_and_statistics(robotcode_cli: CliRunner, flat_suite: Path) -> None:
    """TEXT output is a nested markdown list with a `## Statistics`
    bullet-list footer (italic-label convention)."""
    result = robotcode_cli(["discover", "all", str(flat_suite)])
    # H1 heading + bullets for suite and tests
    assert "# All" in result.stdout
    assert "- **Flat**" in result.stdout  # suite as bullet
    assert "  - **Flat." in result.stdout  # tests indented under suite
    # Statistics renders as an H2 with italic-label bullets underneath.
    assert "## Statistics" in result.stdout
    assert "- _Tests:_" in result.stdout


def test_all_text_nests_beyond_two_levels(robotcode_cli: CliRunner, nested_suite: Path) -> None:
    """A nested suite tree produces a markdown list that goes deeper
    than two levels — the workspace bullet at column 0, intermediate
    suites at columns 2 and 4, leaf tests at column 6+. Guards against
    a regression to a flat layout when the tree has real depth."""
    out = robotcode_cli(["discover", "all", str(nested_suite)]).stdout
    # At least one bullet at indentation 4 (third level: workspace → outer → inner).
    assert "\n    - **" in out


# ---------------------------------------------------------------------------
# Filter interactions
# ---------------------------------------------------------------------------


def test_all_filter_chain_combines_with_search(json_discover: JsonRunner, flat_suite: Path) -> None:
    """`--include smoke --search Login` → intersection (smoke + Login-named)."""
    data = json_discover("all", "--include", "smoke", "--search", "Login", suite_path=flat_suite)
    leaves = walk_test_items(data["items"][0])
    # Login Smoke has tag smoke. Reporting Summary has tag smoke but no
    # "Login" in its name. Only "Login Smoke" passes both filters.
    assert {leaf["name"] for leaf in leaves} == {"Login Smoke"}


def test_all_empty_when_filter_excludes_everything(json_discover: JsonRunner, flat_suite: Path) -> None:
    data = json_discover("all", "--include", "no-such-tag", suite_path=flat_suite)
    assert walk_test_items(data["items"][0]) == []


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def test_all_diagnostics_populated_on_parse_warnings(json_discover: JsonRunner, parse_error_suite: Path) -> None:
    """Parse warnings (duplicate test name, deprecated section header)
    surface in the `diagnostics` field, keyed by file URI."""
    data = json_discover("all", suite_path=parse_error_suite)
    diagnostics = data.get("diagnostics") or {}
    flattened = [d for diags in diagnostics.values() for d in diags]
    messages = [d.get("message", "") for d in flattened]
    assert any("Duplicate Test" in m or "Multiple tests" in m for m in messages), (
        f"expected a duplicate-test warning; got {messages!r}"
    )
