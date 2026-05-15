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


def test_summary_failures_flag_lists_failures(json_result: JsonRunner, basic_output: Path) -> None:
    """`--failures` populates the `failures` array with one entry."""
    data = json_result("summary", "--failures", output_path=basic_output)
    failures = data.get("failures")
    assert isinstance(failures, list)
    assert len(failures) == 1
    failure = failures[0]
    assert get_field(failure, "fullName", "full_name").endswith("Failing Test")
    assert "Boom" in get_field(failure, "message", default="")


def test_summary_no_failures_field_by_default(json_result: JsonRunner, basic_output: Path) -> None:
    """Without `--failures`, the field is omitted (CamelSnakeMixin removes defaults)."""
    data = json_result("summary", output_path=basic_output)
    assert "failures" not in data


def test_summary_text_output_contains_counts(text_result: CliRunner, basic_output: Path) -> None:
    """A trivial sanity check on the TEXT renderer — no snapshot, just smoke."""
    result = text_result("summary", output_path=basic_output)
    plain = strip_ansi(result.stdout)
    # Counts are rendered as a line containing the totals
    assert "5" in plain  # total
    assert "FAIL" in plain  # overall status
