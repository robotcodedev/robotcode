import os
import shlex
import subprocess
import sys
from typing import TYPE_CHECKING, Any, Optional, Sequence

import click

if TYPE_CHECKING:
    from robotcode.plugin import Application

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

    The re-execution happens when the command loads its configuration with
    `load_robot_profile` or `handle_robot_options` of `robotcode.runner.cli.robot`,
    so a marked command must do that first, before it starts a server, an
    interpreter or a debugger. A marked command that loads its configuration in
    another way runs without the wrapper.
    """
    setattr(cmd, _WRAPPABLE_ATTR, True)
    return cmd


def is_wrappable(cmd: click.Command) -> bool:
    """Return whether `cmd` was marked with :func:`wrappable`."""
    return bool(getattr(cmd, _WRAPPABLE_ATTR, False))


def invoked_command_is_wrappable(ctx: click.Context) -> bool:
    """Return whether the command that the root group invokes is marked with :func:`wrappable`.

    A command that such a command runs itself, such as `robot` in `debug`, belongs to it.
    """
    root = ctx.find_root()
    sub_name = root.invoked_subcommand
    if not sub_name or not isinstance(root.command, click.Group):
        return False
    # Aliases resolve to the same command object, so this is alias-safe and needs
    # no central name list.
    sub_cmd = root.command.get_command(root, sub_name)
    return sub_cmd is not None and is_wrappable(sub_cmd)


def run_under_wrapper(app: "Application", profile_wrapper: Optional[Sequence[Any]]) -> None:
    """Re-execute this process through the configured ``wrapper`` command.

    A wrappable command calls this once it has loaded its configuration, before it
    starts anything. ``--wrapper`` overrides the ``wrapper`` of the profile
    (``profile_wrapper``); ``--no-wrapper`` disables wrapping for this run. The
    guard env var prevents infinite recursion and lets an outer layer suppress the
    re-exec by setting it itself. Returns when no wrapper applies or for a dry run.
    """
    if app.config.no_wrapper or os.environ.get(WRAPPER_APPLIED_ENV):
        return

    # `--wrapper` overrides the profile's `wrapper`. The evaluated profile turns
    # StringExpression entries into plain strings.
    if app.config.wrapper:
        wrapper = shlex.split(app.config.wrapper)
    elif profile_wrapper:
        wrapper = [str(w) for w in profile_wrapper]
    else:
        return

    # A dry run must not start the wrapper: it would set up and tear down the
    # real environment. Show it instead; the command itself then prints its own
    # dry-run output.
    if app.config.dry:
        app.echo(f"Dry run, not executing the wrapper. Would run robotcode under: {' '.join(wrapper)}")
        return

    # Rebuild the invocation the way this process was actually started, so the
    # re-exec finds robotcode even when it runs from a bundled path (VS Code) and
    # is not installed in the interpreter. `launcher_script` is set only when we
    # were started through a bundled entry (its `__main__` sets it) or an explicit
    # `--launcher-script`; otherwise robotcode is importable directly and
    # `-m robotcode.cli` is correct. We deliberately do NOT consult the
    # ROBOTCODE_BUNDLED_ROBOTCODE_MAIN env var: VS Code sets it in every terminal,
    # so a directly started robotcode would be diverted to the bundled copy.
    # Mirrors the debug launcher's `debugger_script` handling.
    entry = [str(app.config.launcher_script)] if app.config.launcher_script else ["-m", "robotcode.cli"]
    command = [*wrapper, sys.executable, *entry, *sys.argv[1:]]
    app.verbose(lambda: "Running under wrapper: " + " ".join(command))

    # Run robotcode again under the wrapper; the guard env stops the spawned
    # robotcode from wrapping a second time. On POSIX we replace this process with
    # execvp (no extra process); Windows has no such exec, so there we spawn the
    # command, wait, and forward its exit code.
    os.environ[WRAPPER_APPLIED_ENV] = "1"
    try:
        if sys.platform == "win32":
            sys.exit(subprocess.run(command).returncode)
        os.execvp(command[0], command)
    except OSError as e:
        raise click.ClickException(f"Failed to execute wrapper command {wrapper!r}: {e}") from e
