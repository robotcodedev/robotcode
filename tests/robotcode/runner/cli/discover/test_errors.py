"""Acceptance tests for error and edge-case paths in `robotcode discover`.

Search-related errors (mutex, invalid regex) live in `test_search.py`.
These cover non-existent paths, parse warnings, missing arguments and
format errors.
"""

import json
from pathlib import Path

from .conftest import CliRunner


def test_discover_tests_nonexistent_path(robotcode_cli: CliRunner, tmp_path: Path) -> None:
    """A path that doesn't exist on disk yields a non-zero exit."""
    missing = tmp_path / "no-such-dir-discover-tests"
    result = robotcode_cli(["discover", "tests", str(missing)], expect_ok=False)
    assert result.returncode != 0


def test_discover_files_without_argument_errors(robotcode_cli: CliRunner, tmp_path: Path) -> None:
    """`discover files` without PATHS argument and no default_paths config → UsageError."""
    result = robotcode_cli(["--root", str(tmp_path), "discover", "files"], expect_ok=False)
    assert result.returncode != 0
    assert "argument" in (result.stderr or result.stdout).lower()


def test_invalid_global_format_errors(robotcode_cli: CliRunner) -> None:
    """`robotcode -f bogus discover tests` → Click format-choice error."""
    result = robotcode_cli(["--format", "bogus", "discover", "tests"], expect_ok=False)
    assert result.returncode != 0


def test_info_takes_no_extra_arguments(robotcode_cli: CliRunner) -> None:
    """`discover info` doesn't accept positional arguments."""
    result = robotcode_cli(["discover", "info", "unexpected_extra_arg"], expect_ok=False)
    assert result.returncode != 0


def test_parse_warnings_dont_fail_the_command(robotcode_cli: CliRunner, parse_error_suite: Path) -> None:
    """Robot parse warnings (duplicate test name, deprecated section)
    produce diagnostics but the command still exits zero."""
    result = robotcode_cli(
        [
            "--root",
            str(parse_error_suite.parent),
            "--format",
            "json",
            "discover",
            "--no-diagnostics",
            "all",
            str(parse_error_suite),
        ]
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    # JSON `diagnostics` reflects what would otherwise appear on stderr.
    assert data.get("diagnostics"), "expected non-empty diagnostics"


def test_text_default_shows_diagnostics_summary_only(text_discover: CliRunner, parse_error_suite: Path) -> None:
    """By default a compact `## Diagnostics` counts section follows the
    statistics (a separate block, not folded into them) plus a pointer to
    `--diagnostics`, while the full message listing stays hidden."""
    result = text_discover("all", suite_path=parse_error_suite)
    assert result.returncode == 0
    # Its own section, after (not inside) the statistics ...
    assert "## Diagnostics" in result.stdout
    assert result.stdout.index("## Statistics") < result.stdout.index("## Diagnostics")
    assert "_Warnings:_ 2" in result.stdout
    # ... with a pointer to the full listing, which itself stays hidden.
    assert "--diagnostics" in result.stdout
    assert "deprecated" not in result.stdout


def test_text_clean_suite_has_no_diagnostics_section(text_discover: CliRunner, flat_suite: Path) -> None:
    """A suite without parse issues renders neither the `## Diagnostics`
    section nor the `--diagnostics` pointer."""
    result = text_discover("all", suite_path=flat_suite)
    assert result.returncode == 0
    assert "## Diagnostics" not in result.stdout
    assert "--diagnostics" not in result.stdout


def test_text_diagnostics_flag_shows_full_block_before_listing(
    text_discover: CliRunner, parse_error_suite: Path
) -> None:
    """With `--diagnostics` the full `## Diagnostics` block with the actual
    messages is rendered before the statistics (and the discovered
    listing), and the compact counts/pointer summary is gone."""
    result = text_discover("--diagnostics", "all", suite_path=parse_error_suite)
    assert result.returncode == 0
    assert "## Diagnostics" in result.stdout
    assert result.stdout.index("## Diagnostics") < result.stdout.index("## Statistics")
    assert "deprecated" in result.stdout  # an actual message, only in the full block
    assert "to list the messages" not in result.stdout
    # diagnostics paths use the same project-root-relative form as the tree,
    # not the absolute path.
    assert "`parse_error.robot:" in result.stdout
    assert str(parse_error_suite) not in result.stdout


def test_text_error_severity_in_diagnostics(robotcode_cli: CliRunner, tmp_path: Path) -> None:
    """An error-level parse problem (here an invalid argument spec) shows an
    `Errors` row in the counts section and an `_(error)_` label in the full
    listing — the error counterpart of the warning paths above."""
    suite = tmp_path / "badargs.robot"
    suite.write_text(
        "*** Test Cases ***\nT\n    Log    x\n\n"
        "*** Keywords ***\nKw\n    [Arguments]    ${a}    ${b}=1    ${c}\n    No Operation\n"
    )

    summary = robotcode_cli(["--root", str(tmp_path), "discover", "all", str(suite)])
    assert summary.returncode == 0
    assert "## Diagnostics" in summary.stdout
    assert "_Errors:_ 1" in summary.stdout

    full = robotcode_cli(["--root", str(tmp_path), "discover", "--diagnostics", "all", str(suite)])
    assert full.returncode == 0
    assert "_(error)_" in full.stdout
