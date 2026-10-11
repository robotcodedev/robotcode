import click

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
