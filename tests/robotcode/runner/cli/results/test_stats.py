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
    # tagged.robot: 8 pass, 2 fail, 1 skip
    assert groups["PASS"]["counts"]["total"] == 8
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


def test_stats_by_tag_merges_equivalent_tags(json_result: JsonRunner, tagged_output: Path) -> None:
    """Tags that differ only in case/whitespace/underscore merge into one bucket.

    `tagged.robot` has three tests tagged `norm tag`, `norm_tag`, and
    `NormTag` — semantically the same tag under Robot's normalization rules.
    They must aggregate to a single group, named in normalised form.
    """
    data = json_result("stats", "--by", "tag", output_path=tagged_output)
    groups = _groups_by_name(_section(data, "tag"))
    # All three variants land in one bucket whose label is the normalised
    # form: lowercase, no whitespace, no underscores.
    assert "normtag" in groups
    assert groups["normtag"]["counts"]["total"] == 3
    # And no un-normalised variants leaked through as separate buckets.
    for variant in ("norm tag", "norm_tag", "NormTag"):
        assert variant not in groups


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
    assert section["truncated"] == 3  # 5 distinct tags (after normalisation) - 2 shown


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


def test_stats_failed_shortcut_equivalent_to_status_fail(json_result: JsonRunner, tagged_output: Path) -> None:
    """`stats --by tag --failed` is `--by tag --status fail`."""
    via_shortcut = json_result("stats", "--by", "tag", "--failed", output_path=tagged_output)
    via_status = json_result("stats", "--by", "tag", "--status", "fail", output_path=tagged_output)
    assert _groups_by_name(_section(via_shortcut, "tag")) == _groups_by_name(_section(via_status, "tag"))


def test_stats_passed_shortcut_equivalent_to_status_pass(json_result: JsonRunner, tagged_output: Path) -> None:
    """`stats --by tag --passed` is `--by tag --status pass`."""
    via_shortcut = json_result("stats", "--by", "tag", "--passed", output_path=tagged_output)
    via_status = json_result("stats", "--by", "tag", "--status", "pass", output_path=tagged_output)
    assert _groups_by_name(_section(via_shortcut, "tag")) == _groups_by_name(_section(via_status, "tag"))


# ---------------------------------------------------------------------------
# TEXT smoke
# ---------------------------------------------------------------------------


def test_stats_text_smoke(text_result: CliRunner, tagged_output: Path) -> None:
    plain = strip_ansi(text_result("stats", "--by", "tag", output_path=tagged_output).stdout)
    for tag in ("smoke", "regression", "slow", "bug-123"):
        assert tag in plain


def test_stats_by_status_table_has_status_icons(text_result: CliRunner, tagged_output: Path) -> None:
    """The `By Status` table renders each row's name as ``<icon> **STATUS**``
    so the status is scannable both as colour-on-render and as bold text."""
    plain = strip_ansi(text_result("stats", "--by", "status", output_path=tagged_output).stdout)
    assert "❌ **FAIL**" in plain
    assert "✅ **PASS**" in plain
    assert "⏭ **SKIP**" in plain


def test_stats_status_table_aligns_with_emoji_padding(text_result: CliRunner, tagged_output: Path) -> None:
    """Status icons (✅ ❌ ⏭ ⚪) are double-width emoji; the markdown
    table padder must account for that so header, separator, and all
    data rows have the same display width. Guards against a regression
    where ⏭ / ⏸ were missed by the double-width heuristic and shifted
    the SKIP / NOT RUN rows by one cell."""
    # Emoji set matching the renderer's `_DOUBLE_WIDTH_ICONS`.
    double_wide = {"✅", "❌", "⏭", "⏸", "⚪"}

    def display_width(s: str) -> int:
        return len(s) + sum(1 for ch in s if ch in double_wide)

    plain = strip_ansi(text_result("stats", "--by", "status", output_path=tagged_output).stdout)
    table_rows = [line for line in plain.splitlines() if line.startswith("|")]
    assert table_rows, "expected a markdown table in `stats --by status` output"
    widths = {display_width(row) for row in table_rows}
    assert len(widths) == 1, f"table rows have differing display widths: {widths}\n" + "\n".join(table_rows)
