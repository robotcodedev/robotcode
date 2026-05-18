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
