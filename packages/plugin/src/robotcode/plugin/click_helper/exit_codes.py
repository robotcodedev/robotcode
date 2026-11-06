from typing import TypeVar

import click

_C = TypeVar("_C", bound=click.Command)

_ROBOT_EXIT_CODES_ATTR = "__robotcode_robot_exit_codes__"


def robot_exit_codes(cmd: click.Command) -> click.Command:
    """Mark a CLI command that passes on the exit code of a Robot Framework tool.

    Such a command answers with Robot Framework's exit codes, like the `wrappable`
    commands that run Robot Framework, so an error robotcode reports itself for it
    exits with Robot Framework's 252 instead of Click's 1 or 2. Mark the commands
    that pass on a tool's exit code without running tests - rebot, libdoc,
    testdoc; `wrappable` commands are covered already.
    """
    setattr(cmd, _ROBOT_EXIT_CODES_ATTR, True)
    return cmd


def has_robot_exit_codes(cmd: click.Command) -> bool:
    """Return whether `cmd` was marked with :func:`robot_exit_codes`."""
    return bool(getattr(cmd, _ROBOT_EXIT_CODES_ATTR, False))


_ERRORS_EXIT_WITH_128_ATTR = "__robotcode_errors_exit_with_128__"


def errors_exit_with_128(cmd: _C) -> _C:
    """Mark a CLI command whose errors exit with 128.

    Such a command uses its lower exit codes for what it found, as `results diff`
    does with `--exit-code`, so every error that stops it - Click's 1 or 2, or an
    unexpected exception - exits with 128 instead, which no finding uses. Marking
    a group covers its subcommands.
    """
    setattr(cmd, _ERRORS_EXIT_WITH_128_ATTR, True)
    return cmd


def has_errors_exit_with_128(cmd: click.Command) -> bool:
    """Return whether `cmd` was marked with :func:`errors_exit_with_128`."""
    return bool(getattr(cmd, _ERRORS_EXIT_WITH_128_ATTR, False))
