"""Tests for the debug launcher building the `robotcode … debug` command line.

Covers how a wrapper from the launch request (VS Code
`robotcode.debug.launchWrapper`) is forwarded: the launcher does not apply it
itself, it hands it to robotcode as `--wrapper` and lets robotcode apply it.

Also covers which console a run uses: RobotCode's own run terminal only for
VS Code, the integrated terminal for any other client.
"""

import shlex
from typing import Optional

import pytest

from robotcode.debugger.launcher.server import Console, _build_robotcode_run_args, _console_for_client


def test_forwards_wrapper_as_a_cli_option() -> None:
    args = _build_robotcode_run_args("python", ["-m", "robotcode.cli"], ["ci"], None, ["xvfb-run", "-a"], None)

    assert args[-1] == "debug"
    assert "--wrapper" in args
    i = args.index("--wrapper")
    assert args[i + 1] == "xvfb-run -a"  # the list is shlex-joined into a single arg
    assert i < args.index("debug")  # a group option, before the subcommand


def test_no_wrapper_option_without_a_wrapper() -> None:
    args = _build_robotcode_run_args("python", ["-m", "robotcode.cli"], ["ci"], None, None, None)

    assert "--wrapper" not in args
    assert args[-1] == "debug"


def test_wrapper_round_trips_through_shlex() -> None:
    # A path with spaces must survive the join → robotcode's shlex.split.
    args = _build_robotcode_run_args("python", ["-m", "robotcode.cli"], None, None, ["./x 11.sh", "-a"], None)

    joined = args[args.index("--wrapper") + 1]
    assert shlex.split(joined) == ["./x 11.sh", "-a"]


def test_robotcode_terminal_for_vscode() -> None:
    assert _console_for_client("robotcodeTerminal", "vscode") == "robotcodeTerminal"


@pytest.mark.parametrize("client_id", ["neovim", None])
def test_integrated_terminal_instead_of_robotcode_terminal_for_other_clients(client_id: Optional[str]) -> None:
    assert _console_for_client("robotcodeTerminal", client_id) == "integratedTerminal"


@pytest.mark.parametrize("console", ["internalConsole", "integratedTerminal", "externalTerminal", None])
@pytest.mark.parametrize("client_id", ["vscode", "neovim", None])
def test_other_consoles_stay(console: Optional[Console], client_id: Optional[str]) -> None:
    assert _console_for_client(console, client_id) == console
