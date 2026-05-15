"""Acceptance tests for `robotcode results stats`."""

from pathlib import Path
from typing import Any, Dict

from ._helpers import strip_ansi
from .conftest import CliRunner, JsonRunner


def _section(data: Dict[str, Any], dimension: str) -> Dict[str, Any]:
    for s in data["sections"]:
        if s["dimension"] == dimension:
            return s  # type: ignore[no-any-return]
    raise AssertionError(f"section {dimension!r} not found in {[s['dimension'] for s in data['sections']]}")


def _groups_by_name(section: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {g["name"]: g for g in section["groups"]}


# ---------------------------------------------------------------------------
# Default dimension (status)
# ---------------------------------------------------------------------------


def test_stats_by_status_default(json_result: JsonRunner, tagged_output: Path) -> None:
    """Without --by, stats groups by status."""
    data = json_result("stats", output_path=tagged_output)
    assert len(data["sections"]) == 1
    section = data["sections"][0]
    assert section["dimension"] == "status"
    groups = _groups_by_name(section)
    # tagged.robot: 5 pass, 2 fail, 1 skip
    assert groups["PASS"]["counts"]["total"] == 5
    assert groups["FAIL"]["counts"]["total"] == 2
    assert groups["SKIP"]["counts"]["total"] == 1


# ---------------------------------------------------------------------------
# --by tag
# ---------------------------------------------------------------------------


def test_stats_by_tag_groups_per_tag(json_result: JsonRunner, tagged_output: Path) -> None:
    """A test with N tags counts in N buckets; untagged tests are dropped."""
    data = json_result("stats", "--by", "tag", output_path=tagged_output)
    section = _section(data, "tag")
    groups = _groups_by_name(section)
    assert groups["smoke"]["counts"]["total"] == 3
    assert groups["regression"]["counts"]["total"] == 3
    assert groups["slow"]["counts"]["total"] == 2
    assert groups["bug-123"]["counts"]["total"] == 2
    # No "(untagged)" bucket — untagged tests fall out
    assert "(untagged)" not in groups


def test_stats_by_tag_failed_first_by_default(json_result: JsonRunner, tagged_output: Path) -> None:
    """Default sort orders groups by `failed` descending."""
    data = json_result("stats", "--by", "tag", output_path=tagged_output)
    failed_counts = [g["counts"]["failed"] for g in _section(data, "tag")["groups"]]
    assert failed_counts == sorted(failed_counts, reverse=True)


# ---------------------------------------------------------------------------
# --by suite
# ---------------------------------------------------------------------------


def test_stats_by_suite_uses_full_longname(json_result: JsonRunner, nested_output: Path) -> None:
    """Suite groups are keyed by full longname, not just the leaf."""
    data = json_result("stats", "--by", "suite", output_path=nested_output)
    groups = _groups_by_name(_section(data, "suite"))
    assert "Nested.Child.A" in groups
    assert "Nested.Child.B" in groups


# ---------------------------------------------------------------------------
# Multiple dimensions
# ---------------------------------------------------------------------------


def test_stats_multiple_dimensions_preserve_order(json_result: JsonRunner, tagged_output: Path) -> None:
    """`--by tag --by status` produces sections in the requested order."""
    data = json_result("stats", "--by", "tag", "--by", "status", output_path=tagged_output)
    dimensions = [s["dimension"] for s in data["sections"]]
    assert dimensions == ["tag", "status"]


# ---------------------------------------------------------------------------
# Sort and top
# ---------------------------------------------------------------------------


def test_stats_sort_name_alphabetical(json_result: JsonRunner, tagged_output: Path) -> None:
    data = json_result("stats", "--by", "tag", "--sort", "name", output_path=tagged_output)
    names = [g["name"] for g in _section(data, "tag")["groups"]]
    assert names == sorted(names)


def test_stats_sort_total_desc(json_result: JsonRunner, tagged_output: Path) -> None:
    data = json_result("stats", "--by", "tag", "--sort", "total", output_path=tagged_output)
    totals = [g["counts"]["total"] for g in _section(data, "tag")["groups"]]
    assert totals == sorted(totals, reverse=True)


def test_stats_top_n_truncates(json_result: JsonRunner, tagged_output: Path) -> None:
    data = json_result("stats", "--by", "tag", "--top", "2", output_path=tagged_output)
    section = _section(data, "tag")
    assert len(section["groups"]) == 2
    assert section["truncated"] == 2  # 4 tags - 2 shown


# ---------------------------------------------------------------------------
# Filters and search
# ---------------------------------------------------------------------------


def test_stats_filter_applied_before_aggregation(json_result: JsonRunner, tagged_output: Path) -> None:
    """`--status pass` shrinks the per-tag counts to only passing tests."""
    data = json_result("stats", "--by", "tag", "--status", "pass", output_path=tagged_output)
    groups = _groups_by_name(_section(data, "tag"))
    # smoke has 3 passes, regression has 2 passes
    assert groups["smoke"]["counts"]["total"] == 3
    assert groups["regression"]["counts"]["total"] == 2


def test_stats_search_reduces_groups(json_result: JsonRunner, tagged_output: Path) -> None:
    """`--search` filters before grouping; the matched tag groups shrink."""
    data = json_result("stats", "--by", "tag", "--search", "Bug", output_path=tagged_output)
    groups = _groups_by_name(_section(data, "tag"))
    # Only the two `Tagged Bug *` tests match; both have bug-123
    assert groups["bug-123"]["counts"]["total"] == 2


# ---------------------------------------------------------------------------
# TEXT smoke
# ---------------------------------------------------------------------------


def test_stats_text_smoke(text_result: CliRunner, tagged_output: Path) -> None:
    plain = strip_ansi(text_result("stats", "--by", "tag", output_path=tagged_output).stdout)
    for tag in ("smoke", "regression", "slow", "bug-123"):
        assert tag in plain
