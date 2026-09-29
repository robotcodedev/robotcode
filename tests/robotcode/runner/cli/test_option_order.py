"""The options shared by `robot`, `robot-debug` and the `discover` commands keep
their order in `--help` (and so in the generated CLI reference)."""

from typing import List

import pytest
from click.testing import CliRunner

from robotcode.cli import robotcode
from robotcode.robot.utils import RF_VERSION

# `--by-test-metadata`/`--exclude-by-test-metadata` are hidden before Robot Framework 7.5.
_SHARED = ["-bl", "-ebl", "-btm", "-ebtm", "--version"] if RF_VERSION >= (7, 5) else ["-bl", "-ebl", "--version"]


@pytest.mark.parametrize(
    "command",
    [
        ["robot"],
        ["robot-debug"],
        ["discover", "all"],
        # hidden before Robot Framework 7.5, but its `--help` works everywhere
        ["discover", "metadata"],
        ["discover", "suites"],
        ["discover", "tags"],
        ["discover", "tasks"],
        ["discover", "tests"],
    ],
    ids=" ".join,
)
def test_shared_robot_options_keep_their_order(command: List[str]) -> None:
    result = CliRunner().invoke(robotcode, [*command, "--help"], catch_exceptions=False)
    assert result.exit_code == 0, result.output

    flags = [line.split()[0].rstrip(",") for line in result.output.splitlines() if line.lstrip().startswith("-")]
    assert [flag for flag in flags if flag in ("-bl", "-ebl", "-btm", "-ebtm", "--version")] == _SHARED
