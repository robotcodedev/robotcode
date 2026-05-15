"""Acceptance tests for `robotcode results show`."""

from pathlib import Path

from ._helpers import find_test, get_field, strip_ansi
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
    """JSON output always carries `tags`; `--tags` only affects TEXT rendering."""
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
    """In TEXT mode the `smoke` tag appears only when `--tags` is set."""
    without = strip_ansi(text_result("show", output_path=basic_output).stdout)
    with_tags = strip_ansi(text_result("show", "--tags", output_path=basic_output).stdout)
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
        "--tags",
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
    """The TEXT renderer highlights the matched substring (ANSI markers present)."""
    raw = text_result("show", "--search", "Failing", output_path=basic_output).stdout
    # Highlight uses click.style — there must be ANSI escapes around the match.
    assert "\x1b[" in raw or "Failing" in strip_ansi(raw)
    # The strip-ANSI version still contains the literal match
    assert "Failing" in strip_ansi(raw)


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
