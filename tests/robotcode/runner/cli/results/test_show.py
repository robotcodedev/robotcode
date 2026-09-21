"""Acceptance tests for `robotcode results show`."""

from pathlib import Path

import pytest

from robotcode.robot.utils import RF_VERSION

from ..rf_markers import needs_rf_75
from ._helpers import TEST_METADATA_EXPECTED, find_test, get_field, strip_ansi
from .conftest import CliRunner, JsonRunner

# ---------------------------------------------------------------------------
# Basic listing
# ---------------------------------------------------------------------------


def test_show_lists_all_tests_default_order(json_result: JsonRunner, basic_output: Path) -> None:
    """Default order = execution order (which is source order for our fixture)."""
    data = json_result("show", output_path=basic_output)
    names = [t["name"] for t in data["tests"]]
    assert names == [
        "Passing Test One",
        "Passing Test Two",
        "Passing Test Three",
        "Failing Test",
        "Skipped Test",
    ]


def test_show_top_n_truncates(json_result: JsonRunner, basic_output: Path) -> None:
    """`--top 2` keeps 2 entries and reports the rest in `truncated`."""
    data = json_result("show", "--top", "2", output_path=basic_output)
    assert len(data["tests"]) == 2
    assert data["truncated"] == 3


def test_show_message_chars_truncates(json_result: JsonRunner, basic_output: Path) -> None:
    """`--message-chars 5` truncates the failure message."""
    data = json_result("show", "--message-chars", "5", output_path=basic_output)
    failing = find_test(data["tests"], "Basic.Failing Test")
    assert failing is not None
    msg = failing["message"]
    # Short truncation → no longer the literal "Boom: deliberate failure"
    assert len(msg) <= 10  # margin for an ellipsis character
    assert msg != "Boom: deliberate failure"


def test_show_tags_always_present_in_json(json_result: JsonRunner, basic_output: Path) -> None:
    """JSON output always carries `tags`; `--show-tags` only affects TEXT rendering."""
    data = json_result("show", output_path=basic_output)
    smoke_test = find_test(data["tests"], "Basic.Passing Test One")
    assert smoke_test is not None
    assert smoke_test.get("tags") == ["smoke"]


def test_show_tags_emitted_in_normalised_form(json_result: JsonRunner, tagged_output: Path) -> None:
    """Tags in `tests[].tags` come out normalised (`bug 1` -> `bug1`)."""
    data = json_result("show", output_path=tagged_output)
    norm_tests = [t for t in data["tests"] if t["name"].startswith("Tag Norm Variant")]
    assert len(norm_tests) == 3
    # All three Norm-Variant tests carry the same single tag, normalised.
    for t in norm_tests:
        assert t["tags"] == ["normtag"]


def test_show_text_tags_flag_controls_visibility(text_result: CliRunner, basic_output: Path) -> None:
    """In TEXT mode the `smoke` tag appears only when `--show-tags` is set."""
    without = strip_ansi(text_result("show", output_path=basic_output).stdout)
    with_tags = strip_ansi(text_result("show", "--show-tags", output_path=basic_output).stdout)
    assert "smoke" not in without
    assert "smoke" in with_tags


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------


def test_show_sort_name(json_result: JsonRunner, basic_output: Path) -> None:
    """`--sort name` orders tests lexicographically by full name."""
    data = json_result("show", "--sort", "name", output_path=basic_output)
    full_names = [t["fullName"] for t in data["tests"]]
    assert full_names == sorted(full_names, key=str.lower)


def test_show_sort_status(json_result: JsonRunner, basic_output: Path) -> None:
    """`--sort status` orders FAIL → SKIP → PASS → NOT RUN."""
    data = json_result("show", "--sort", "status", output_path=basic_output)
    statuses = [t["status"] for t in data["tests"]]
    rank = {"FAIL": 0, "SKIP": 1, "PASS": 2, "NOT RUN": 3}
    assert statuses == sorted(statuses, key=lambda s: rank.get(s, 99))


def test_show_sort_elapsed_does_not_crash(json_result: JsonRunner, basic_output: Path) -> None:
    """`--sort elapsed` returns all entries (durations may all be near-zero)."""
    data = json_result("show", "--sort", "elapsed", output_path=basic_output)
    assert len(data["tests"]) == 5
    elapsed = [t.get("elapsedSeconds") or 0 for t in data["tests"]]
    # Descending: each entry is >= the next.
    assert all(elapsed[i] >= elapsed[i + 1] for i in range(len(elapsed) - 1))


def test_show_sort_reverse_flips_elapsed(json_result: JsonRunner, basic_output: Path) -> None:
    """`--sort elapsed --reverse` inverts the natural (desc) order."""
    data = json_result("show", "--sort", "elapsed", "--reverse", output_path=basic_output)
    elapsed = [t.get("elapsedSeconds") or 0 for t in data["tests"]]
    assert all(elapsed[i] <= elapsed[i + 1] for i in range(len(elapsed) - 1))


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def test_show_filter_status_pass(json_result: JsonRunner, basic_output: Path) -> None:
    """`--status pass` keeps only passing tests."""
    data = json_result("show", "--status", "pass", output_path=basic_output)
    statuses = {t["status"] for t in data["tests"]}
    assert statuses == {"PASS"}
    assert len(data["tests"]) == 3


def test_show_filter_chain_intersects(json_result: JsonRunner, tagged_output: Path) -> None:
    """`--include smoke --status pass` is an AND chain."""
    data = json_result(
        "show",
        "--include",
        "smoke",
        "--status",
        "pass",
        "--show-tags",
        output_path=tagged_output,
    )
    assert all("smoke" in (t.get("tags") or []) for t in data["tests"])
    assert all(t["status"] == "PASS" for t in data["tests"])
    assert {t["name"] for t in data["tests"]} == {
        "Tagged Smoke Pass",
        "Tagged Smoke Regression Pass",
        "Tagged Bug Smoke Pass",
    }


def test_show_filter_no_match_returns_empty(json_result: JsonRunner, basic_output: Path) -> None:
    """A filter that excludes everything yields an empty list."""
    data = json_result("show", "--include", "nonexistent-tag", output_path=basic_output)
    assert data["tests"] == []
    assert data["truncated"] == 0


def test_show_filters_applied_reflected_in_json(json_result: JsonRunner, tagged_output: Path) -> None:
    """`filters_applied` captures the filters that were actually used."""
    data = json_result("show", "--include", "smoke", "--status", "pass", output_path=tagged_output)
    applied = data.get("filtersApplied")
    assert isinstance(applied, dict)
    # Keys are camelCased and present
    assert "include" in applied
    assert "status" in applied


# ---------------------------------------------------------------------------
# Status shortcuts (--failed / --passed / --skipped)
# ---------------------------------------------------------------------------


def test_show_failed_shortcut_keeps_only_failed(json_result: JsonRunner, basic_output: Path) -> None:
    """`--failed` is shorthand for `--status fail`."""
    data = json_result("show", "--failed", output_path=basic_output)
    statuses = {t["status"] for t in data["tests"]}
    assert statuses == {"FAIL"}


def test_show_passed_shortcut_keeps_only_passed(json_result: JsonRunner, basic_output: Path) -> None:
    """`--passed` is shorthand for `--status pass`."""
    data = json_result("show", "--passed", output_path=basic_output)
    statuses = {t["status"] for t in data["tests"]}
    assert statuses == {"PASS"}


def test_show_skipped_shortcut_keeps_only_skipped(json_result: JsonRunner, basic_output: Path) -> None:
    """`--skipped` is shorthand for `--status skip`."""
    data = json_result("show", "--skipped", output_path=basic_output)
    statuses = {t["status"] for t in data["tests"]}
    assert statuses == {"SKIP"}


def test_show_shortcuts_stack_additively(json_result: JsonRunner, basic_output: Path) -> None:
    """`--failed --skipped` is `--status fail --status skip` (OR semantics)."""
    data = json_result("show", "--failed", "--skipped", output_path=basic_output)
    statuses = {t["status"] for t in data["tests"]}
    assert statuses == {"FAIL", "SKIP"}


def test_show_failed_with_explicit_status_is_idempotent(json_result: JsonRunner, basic_output: Path) -> None:
    """`--failed --status fail` doesn't duplicate the filter — same result as `--failed`."""
    data = json_result("show", "--failed", "--status", "fail", output_path=basic_output)
    statuses = {t["status"] for t in data["tests"]}
    assert statuses == {"FAIL"}
    applied = data.get("filtersApplied") or {}
    assert applied.get("status") == ["fail"]


def test_show_failed_combines_with_explicit_status(json_result: JsonRunner, basic_output: Path) -> None:
    """`--failed --status skip` is `--status fail --status skip` (additive OR)."""
    data = json_result("show", "--failed", "--status", "skip", output_path=basic_output)
    statuses = {t["status"] for t in data["tests"]}
    assert statuses == {"FAIL", "SKIP"}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def test_show_search_substring_matches_name(json_result: JsonRunner, basic_output: Path) -> None:
    """Case-insensitive substring against the test name."""
    data = json_result("show", "--search", "failing", output_path=basic_output)
    assert len(data["tests"]) == 1
    assert data["tests"][0]["name"] == "Failing Test"


def test_show_search_no_match(json_result: JsonRunner, basic_output: Path) -> None:
    """Search that matches nothing yields an empty result, not an error."""
    data = json_result("show", "--search", "no-such-text-anywhere", output_path=basic_output)
    assert data["tests"] == []


def test_show_search_highlight_visible_in_text(text_result: CliRunner, basic_output: Path) -> None:
    """The TEXT renderer marks search matches by wrapping them in
    markdown inline-code spans (`` `match` ``). `rich` themes the span;
    raw-markdown output keeps the backticks as visible markers."""
    plain = strip_ansi(text_result("show", "--search", "Failing", output_path=basic_output).stdout)
    # The literal match is in the output.
    assert "Failing" in plain
    # The match is wrapped in an inline-code span — the markdown highlight form.
    assert "`Failing`" in plain


# ---------------------------------------------------------------------------
# Test metadata (Robot Framework 7.5+)
# ---------------------------------------------------------------------------


@needs_rf_75
def test_show_metadata_in_json(json_result: JsonRunner, metadata_output: Path) -> None:
    """Names keep the author's spelling, multi-line values are joined with
    `\\n`, and a test without metadata has no `metadata` key at all."""
    data = json_result("show", output_path=metadata_output)

    assert [t["name"] for t in data["tests"]] == list(TEST_METADATA_EXPECTED)
    for t in data["tests"]:
        wanted = TEST_METADATA_EXPECTED[t["name"]]
        if wanted is None:
            assert "metadata" not in t
        else:
            assert list(t["metadata"].items()) == list(wanted.items())


@pytest.mark.skipif(RF_VERSION >= (7, 5), reason="Robot Framework < 7.5 has no test metadata")
def test_show_no_metadata_key_on_older_robot(json_result: JsonRunner, metadata_output: Path) -> None:
    data = json_result("show", output_path=metadata_output)

    assert [t["name"] for t in data["tests"]] == list(TEST_METADATA_EXPECTED)
    assert all("metadata" not in t for t in data["tests"])


def test_show_help_offers_the_metadata_flag_only_where_test_metadata_exists(robotcode_cli: CliRunner) -> None:
    out = robotcode_cli(["results", "show", "--help"]).stdout

    assert "--show-tags / --no-show-tags" in out
    assert "--tags" not in out
    assert "--no-tags" not in out
    assert ("--show-metadata / --no-show-metadata" in out) == (RF_VERSION >= (7, 5))


def test_show_metadata_flag_does_not_change_json(json_result: JsonRunner, metadata_output: Path) -> None:
    """`--show-metadata` is a TEXT renderer hint; JSON always carries the data.

    Runs on every Robot Framework version: before 7.5 the flag is hidden
    from the help but still accepted."""
    default = json_result("show", output_path=metadata_output)
    with_flag = json_result("show", "--show-metadata", output_path=metadata_output)
    without_flag = json_result("show", "--no-show-metadata", output_path=metadata_output)
    assert default == with_flag == without_flag


@needs_rf_75
def test_show_text_metadata_flag_controls_visibility(text_result: CliRunner, metadata_output: Path) -> None:
    """In TEXT mode the `_Metadata:_` bullet appears only with `--show-metadata`,
    and only under tests that have metadata."""
    with_flag = strip_ansi(text_result("show", "--show-metadata", output_path=metadata_output).stdout)
    default = strip_ansi(text_result("show", output_path=metadata_output).stdout)
    without_flag = strip_ansi(text_result("show", "--no-show-metadata", output_path=metadata_output).stdout)

    lines = with_flag.splitlines()
    assert "  - _Metadata:_ Issue: 4410, Owner Team: core" in lines
    # A multi-line value stays on the one bullet line.
    assert "  - _Metadata:_ Description: first line second line" in lines
    assert with_flag.count("_Metadata:_") == 4
    assert "_Metadata:_" not in default
    assert "_Metadata:_" not in without_flag


@needs_rf_75
def test_show_search_matches_metadata_value(json_result: JsonRunner, metadata_output: Path) -> None:
    data = json_result("show", "--search", "4409", output_path=metadata_output)
    assert [t["name"] for t in data["tests"]] == ["Single Line"]


@needs_rf_75
def test_show_search_matches_metadata_name(json_result: JsonRunner, metadata_output: Path) -> None:
    """Names match literally and case-insensitively, without Robot's
    metadata-key normalisation."""
    data = json_result("show", "--search", "owner team", output_path=metadata_output)
    assert [t["name"] for t in data["tests"]] == ["Spaced Key"]

    data = json_result("show", "--search", "ownerteam", output_path=metadata_output)
    assert data["tests"] == []


@needs_rf_75
def test_show_search_highlights_metadata_in_text(text_result: CliRunner, metadata_output: Path) -> None:
    plain = strip_ansi(text_result("show", "--show-metadata", "--search", "4409", output_path=metadata_output).stdout)
    assert "  - _Metadata:_ Issue: `4409`" in plain.splitlines()


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def test_show_full_paths_keeps_both_source_fields(json_result: JsonRunner, basic_output: Path) -> None:
    """`--full-paths` only affects TEXT rendering. JSON always carries
    both `source` (absolute) and `relSource` (relative-to-cwd or omitted
    when not anchored) so consumers like the VS Code extension can
    consistently rely on the schema."""
    data = json_result("show", "--full-paths", output_path=basic_output)
    for t in data["tests"]:
        src = t.get("source")
        assert src is not None
        assert Path(src).is_absolute()


def test_show_default_includes_rel_source(json_result: JsonRunner, basic_output: Path) -> None:
    """Without the flag, JSON has both fields (relSource present when
    the source is anchored under cwd)."""
    data = json_result("show", output_path=basic_output)
    for t in data["tests"]:
        assert get_field(t, "source", "relSource") is not None


# ---------------------------------------------------------------------------
# TEXT smoke
# ---------------------------------------------------------------------------


def test_show_text_smoke(text_result: CliRunner, basic_output: Path) -> None:
    """TEXT output for `show` mentions every test name."""
    plain = strip_ansi(text_result("show", output_path=basic_output).stdout)
    for name in (
        "Passing Test One",
        "Passing Test Two",
        "Passing Test Three",
        "Failing Test",
        "Skipped Test",
    ):
        assert name in plain
