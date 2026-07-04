"""Tests for the debug launcher building the `robotcode … debug` command line.

Covers how a wrapper from the launch request (VS Code
`robotcode.debug.launchWrapper`) is forwarded: the launcher does not apply it
itself, it hands it to robotcode as `--wrapper` and lets robotcode apply it.
"""

import shlex

from robotcode.debugger.launcher.server import _build_robotcode_run_args


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
