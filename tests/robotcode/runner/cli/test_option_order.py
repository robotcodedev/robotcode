"""The options shared by `robot`, `robot-debug` and the `discover` commands keep
their order in `--help` (and so in the generated CLI reference)."""

from typing import List

import pytest
from click.testing import CliRunner

from robotcode.cli import robotcode


@pytest.mark.parametrize(
    "command",
    [
        ["robot"],
        ["robot-debug"],
        ["discover", "all"],
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
    assert [flag for flag in flags if flag in ("-bl", "-ebl", "--version")] == ["-bl", "-ebl", "--version"]
