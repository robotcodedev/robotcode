"""The test-metadata options and `discover metadata` are only offered with
Robot Framework 7.5+: hidden from `--help` before, and without a version note
where they are shown."""

import re
from typing import List

import pytest
from click.testing import CliRunner

from robotcode.cli import robotcode
from robotcode.robot.utils import RF_VERSION


def _help(command: List[str]) -> str:
    result = CliRunner().invoke(robotcode, [*command, "--help"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    # click wraps long help texts; compare with single spaces
    return " ".join(result.output.split())


@pytest.mark.parametrize(
    "command",
    [["robot"], ["robot-debug"], ["discover", "tests"], ["results", "show"]],
    ids=" ".join,
)
def test_metadata_options_only_listed_on_rf_75(command: List[str]) -> None:
    output = _help(command)
    for option in ("--by-test-metadata", "--exclude-by-test-metadata"):
        assert (option in output) is (RF_VERSION >= (7, 5))


def test_metadata_command_only_listed_on_rf_75() -> None:
    result = CliRunner().invoke(robotcode, ["discover", "--help"], catch_exceptions=False)
    listed = [line.split()[0] for line in result.output.splitlines() if line.startswith("  ") and line.split()]
    assert ("metadata" in listed) is (RF_VERSION >= (7, 5))


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="the help is only shown with Robot Framework 7.5+")
@pytest.mark.parametrize(
    "command",
    [["robot"], ["discover", "metadata"], ["discover", "tests"], ["results", "show"]],
    ids=" ".join,
)
def test_help_has_no_version_note(command: List[str]) -> None:
    """`--help` only shows these where the version is right; the generated CLI
    reference marks them instead (`tests/scripts/test_create_cmdline_doc.py`)."""
    assert re.search(r"Robot Framework \d", _help(command)) is None
