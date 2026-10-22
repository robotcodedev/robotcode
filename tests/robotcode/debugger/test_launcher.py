"""Tests for the debug launcher building the `robotcode … debug` command line.

Covers how a wrapper from the launch request (VS Code
`robotcode.debug.launchWrapper`) is forwarded: the launcher does not apply it
itself, it hands it to robotcode as `--wrapper` and lets robotcode apply it.

Also covers which console a run uses: RobotCode's own run terminal only for
VS Code, the integrated terminal for any other client.

And the environment of a run in the internal console: on Windows, a variable
of the run replaces an inherited one whose name differs only in case.
"""

import shlex
from typing import Optional

import pytest

from robotcode.debugger.launcher.server import (
    Console,
    _build_robotcode_run_args,
    _console_for_client,
    _merged_environment,
)


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


def test_run_variable_replaces_another_spelling_on_windows() -> None:
    assert _merged_environment({"Path": r"C:\Windows"}, {"path": r"C:\tools"}, windows=True) == {"path": r"C:\tools"}
    assert _merged_environment({"PATH": r"C:\Windows"}, {"Path": r"C:\tools"}, windows=True) == {"Path": r"C:\tools"}


def test_run_variables_keep_other_variables_on_windows() -> None:
    base = {"PATH": r"C:\Windows", "TEMP": r"C:\Temp"}

    assert _merged_environment(base, {"Path": r"C:\tools", "ROBOT_OPTIONS": "-L DEBUG"}, windows=True) == {
        "TEMP": r"C:\Temp",
        "Path": r"C:\tools",
        "ROBOT_OPTIONS": "-L DEBUG",
    }


def test_run_variable_keeps_another_spelling_on_other_platforms() -> None:
    assert _merged_environment({"PATH": "/usr/bin"}, {"path": "/opt/bin"}, windows=False) == {
        "PATH": "/usr/bin",
        "path": "/opt/bin",
    }


def test_last_of_two_spellings_of_the_run_stays_on_windows() -> None:
    env = {"path": r"C:\from-robot-env", "Path": r"C:\from-launch-config"}

    assert _merged_environment({"PATH": r"C:\Windows"}, env, windows=True) == {"Path": r"C:\from-launch-config"}
