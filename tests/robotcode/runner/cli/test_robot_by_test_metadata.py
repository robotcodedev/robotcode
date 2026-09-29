"""`robotcode robot` with `--by-test-metadata` (Robot Framework 7.5+).

Runs RobotCode in a subprocess on a copy of the discover metadata fixture,
so the repository's own `robot.toml` does not apply.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

from robot.api import ExecutionResult

from .rf_markers import needs_rf_75

_FIXTURE = Path(__file__).parent / "discover" / "suites" / "metadata.robot"


def _run(tmp_path: Path, *options: str) -> "subprocess.CompletedProcess[str]":
    suite = tmp_path / "metadata.robot"
    shutil.copyfile(_FIXTURE, suite)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "robotcode.cli",
            "--root",
            str(tmp_path),
            "robot",
            *options,
            "--output",
            str(tmp_path / "output.xml"),
            "--report",
            "NONE",
            "--log",
            "NONE",
            str(suite),
        ],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=120,
    )


def _executed(tmp_path: Path) -> List[str]:
    return [test.name for test in ExecutionResult(str(tmp_path / "output.xml")).suite.tests]


@needs_rf_75
def test_runs_only_matching_tests(tmp_path: Path) -> None:
    process = _run(tmp_path, "--by-test-metadata", "Issue:4409")
    assert process.returncode == 0, process.stdout + process.stderr
    assert _executed(tmp_path) == ["Single Line"]


@needs_rf_75
def test_excludes_matching_tests(tmp_path: Path) -> None:
    process = _run(tmp_path, "-ebtm", "Issue:*", "-ebtm", "Description:*")
    assert process.returncode == 0, process.stdout + process.stderr
    assert _executed(tmp_path) == ["No Metadata", "Empty Setting"]


@needs_rf_75
def test_invalid_pattern_runs_nothing(tmp_path: Path) -> None:
    process = _run(tmp_path, "--by-test-metadata", "Issue")
    assert process.returncode == 252, process.stdout + process.stderr
    assert "Invalid metadata pattern 'Issue'" in process.stdout + process.stderr
    assert not (tmp_path / "output.xml").exists()
