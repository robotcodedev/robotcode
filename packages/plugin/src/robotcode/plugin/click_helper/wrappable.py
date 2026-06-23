import click

# Set in the environment once a wrapper has been applied to the process tree.
# Prevents infinite re-exec recursion and lets an outer layer (e.g. the VS Code
# debug launcher applying its own wrapper) suppress the CLI/profile re-exec.
WRAPPER_APPLIED_ENV = "ROBOTCODE_WRAPPER_APPLIED"

_WRAPPABLE_ATTR = "__robotcode_wrappable__"


def wrappable(cmd: click.Command) -> click.Command:
    """Mark a CLI command as *wrappable*.

    When a `wrapper` (session) command is configured, a wrappable command is
    re-executed through it, because it executes Robot Framework (and may, for
    example, need to run inside a specific X11/Wayland session). Commands that
    do not execute Robot Framework - language server, discovery, libdoc, … -
    must NOT be marked.
    """
    setattr(cmd, _WRAPPABLE_ATTR, True)
    return cmd


def is_wrappable(cmd: click.Command) -> bool:
    """Return whether `cmd` was marked with :func:`wrappable`."""
    return bool(getattr(cmd, _WRAPPABLE_ATTR, False))
