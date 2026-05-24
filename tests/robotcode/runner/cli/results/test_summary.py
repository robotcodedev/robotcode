"""Smoke-level acceptance tests for `robotcode results summary`."""

from pathlib import Path

from ._helpers import assert_counts, get_field, strip_ansi
from .conftest import CliRunner, JsonRunner


def test_summary_basic_json_shape(json_result: JsonRunner, basic_output: Path) -> None:
    """The JSON output exposes the expected top-level schema."""
    data = json_result("summary", output_path=basic_output)
    assert isinstance(data, dict)
    # Required top-level fields
    assert "file" in data
    assert "status" in data
    assert "counts" in data
    # `file` carries the source path
    assert get_field(data["file"], "source") is not None


def test_summary_basic_counts(json_result: JsonRunner, basic_output: Path) -> None:
    """basic.robot has 3 pass / 1 fail / 1 skip / 0 not-run = 5 total."""
    data = json_result("summary", output_path=basic_output)
    assert_counts(data["counts"], total=5, passed=3, failed=1, skipped=1, not_run=0)


def test_summary_overall_status_is_fail(json_result: JsonRunner, basic_output: Path) -> None:
    """A run that contains failures must report FAIL overall."""
    data = json_result("summary", output_path=basic_output)
    assert data["status"] == "FAIL"


def test_summary_failed_flag_lists_failed(json_result: JsonRunner, basic_output: Path) -> None:
    """`--failed` populates the `failed` array with one entry."""
    data = json_result("summary", "--failed", output_path=basic_output)
    failed = data.get("failed")
    assert isinstance(failed, list)
    assert len(failed) == 1
    failure = failed[0]
    assert get_field(failure, "fullName", "full_name").endswith("Failing Test")
    assert "Boom" in get_field(failure, "message", default="")


def test_summary_no_failed_field_by_default(json_result: JsonRunner, basic_output: Path) -> None:
    """Without `--failed`, the field is omitted (CamelSnakeMixin removes defaults)."""
    data = json_result("summary", output_path=basic_output)
    assert "failed" not in data


def test_summary_text_output_contains_counts(text_result: CliRunner, basic_output: Path) -> None:
    """A trivial sanity check on the TEXT renderer — no snapshot, just smoke."""
    result = text_result("summary", output_path=basic_output)
    plain = strip_ansi(result.stdout)
    # Counts are rendered as a line containing the totals
    assert "5" in plain  # total
    assert "FAIL" in plain  # overall status


def test_summary_text_output_is_markdown(text_result: CliRunner, basic_output: Path) -> None:
    """The TEXT output is markdown — H1 heading, italic-label bullets
    for the summary fields, and the status field paints both an icon
    and the bold word."""
    plain = strip_ansi(text_result("summary", output_path=basic_output).stdout)
    assert plain.startswith("# Summary")
    # Status bullet carries the icon + bold word in the value column.
    assert "- _Status:_" in plain
    assert "❌" in plain
    assert "**FAIL**" in plain
    # Other summary metrics also come through as italic-label bullets.
    assert "- _Total:_" in plain
    assert "- _Passed:_" in plain


# ---------------------------------------------------------------------------
# --full-paths
# ---------------------------------------------------------------------------


def test_summary_full_paths_keeps_rel_source(json_result: JsonRunner, basic_output: Path) -> None:
    """`--full-paths` is a TEXT-rendering hint; JSON always carries
    both `source` (absolute) and `relSource` so consumers like the
    VS Code extension can rely on the schema being stable across the
    flag."""
    data = json_result("summary", "--failed", "--full-paths", output_path=basic_output)
    failed = data["failed"]
    assert failed, "expected at least one failure"
    failure = failed[0]
    src = get_field(failure, "source")
    assert src is not None
    assert Path(src).is_absolute()
    # rel_source is *still* present (it would have been omitted under
    # the old behaviour where `--full-paths` cleared it).
    assert get_field(failure, "relSource", "rel_source") is not None


def test_summary_default_includes_rel_source(json_result: JsonRunner, basic_output: Path) -> None:
    data = json_result("summary", "--failed", output_path=basic_output)
    failed = data["failed"]
    assert failed
    assert get_field(failed[0], "relSource", "rel_source") is not None
