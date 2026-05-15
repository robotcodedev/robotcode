"""Acceptance tests for `robotcode results` error-handling paths.

These all assert that a misuse (bad flag, missing file, unparseable
regex, wrong format) is reported as a non-zero exit code with a useful
message on stderr — not a stack trace and not a silent zero.
"""

from pathlib import Path

import pytest

from .conftest import CliRunner


def test_missing_output_file_is_a_clear_error(robotcode_cli: CliRunner, tmp_path: Path) -> None:
    """`--output /nonexistent.xml` reports the missing file by path."""
    missing = tmp_path / "no_such.xml"
    result = robotcode_cli(
        ["results", "summary", "--output", str(missing)],
        expect_ok=False,
    )
    assert result.returncode != 0
    combined = (result.stderr + result.stdout).lower()
    assert "not found" in combined or "no such" in combined


def test_output_dir_without_xml_reports_no_result_file(robotcode_cli: CliRunner, tmp_path: Path) -> None:
    """Pointing `--output` at an empty directory yields a discovery error."""
    empty_dir = tmp_path / "empty_results_dir"
    empty_dir.mkdir()
    result = robotcode_cli(
        ["results", "summary", "--output", str(empty_dir)],
        expect_ok=False,
    )
    assert result.returncode != 0
    combined = (result.stderr + result.stdout).lower()
    # Error wording: either "no result file" (auto-discovery) or just "not found"
    assert "result file" in combined or "no " in combined


def test_unknown_global_format_is_rejected(robotcode_cli: CliRunner, basic_output: Path) -> None:
    """`-f bogus` is a Click-level rejection of an enum value."""
    result = robotcode_cli(
        ["--format", "bogus", "results", "summary", "--output", str(basic_output)],
        expect_ok=False,
    )
    assert result.returncode != 0
    # Click's invalid-choice error mentions either the offending value or 'invalid'
    assert b"bogus" in result.stderr.lower().encode() or "invalid" in result.stderr.lower()


def test_unknown_subcommand_is_rejected(robotcode_cli: CliRunner) -> None:
    """Click rejects an unknown subcommand of `results`."""
    result = robotcode_cli(
        ["results", "does-not-exist"],
        expect_ok=False,
    )
    assert result.returncode != 0
    assert "no such" in result.stderr.lower() or "usage" in result.stderr.lower()


@pytest.mark.parametrize("subcommand", ["summary", "show", "log", "stats"])
def test_invalid_search_regex_is_rejected_uniformly(
    subcommand: str, robotcode_cli: CliRunner, basic_output: Path
) -> None:
    """Every search-aware subcommand rejects an unparseable regex."""
    result = robotcode_cli(
        ["results", subcommand, "--search-regex", "[abc", "--output", str(basic_output)],
        expect_ok=False,
    )
    assert result.returncode != 0
    assert "search-regex" in result.stderr.lower() or "invalid" in result.stderr.lower()
