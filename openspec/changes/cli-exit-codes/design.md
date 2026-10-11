# Design

## Context

- robotcode reports its own errors as Click exceptions. A `ClickException` exits with 1: the wrapper start error in `_maybe_reexec_under_wrapper`, and the `robot.toml` errors that `handle_robot_options` (`robot`, `repl`, `robot-debug`, `discover`, `doc`) and `rebot`, `libdoc` and `testdoc` wrap in `ClickException(str(e))`. Option errors are `UsageError`/`BadParameter` with exit code 2. `UnknownError` is a `ClickException` with exit code 255, used by `config`, `profiles`, `debug` and the debug launcher.
- Robot Framework's own codes reach the process as `SystemExit` through `app.exit()`, never as Click exceptions.
- `@wrappable` already marks the commands that run Robot Framework: `robot`, `debug`, `repl`, `robot-debug`, `repl-server`.
- The root group is a `click.group(cls=AliasedGroup)`. Click's `Group.invoke` sets `ctx.invoked_subcommand` before it runs the group callback (where the wrapper re-exec happens) and before it parses the subcommand's arguments, so errors from the wrapper, from option parsing and from the command itself all pass through it.
- `debug` wraps its run in `except Exception: raise UnknownError(str(e))`, so a broken `robot.toml` ends with 255 there.

## Goals / Non-Goals

**Goals:**
- One place decides the exit code; the places that raise errors stay as they are.
- Robot Framework's exit codes and deliberately chosen codes (255) stay untouched.

**Non-Goals:**
- Errors in robotcode's global options (`robotcode --bogus robot`): Click reports them before the command is known, so they keep exit code 2.
- The unknown `robot.toml` key that is silently ignored and the unknown profile (`-p nope`) that doesn't stop the run.
- `repl-server` reports an invalid `robot.toml` as a traceback and keeps running. That is a separate fix; the rule applies once it reports the error as the other commands do.
- The exit codes of `analyze`, `discover`, `results`, `config`, `profiles` and the other commands.

## Decisions

### Map the exit code in the root group

A subclass of `AliasedGroup` for the root group overrides `invoke`. When a `click.ClickException` with exit code 1 or 2 leaves the invocation of a covered command, it is raised again as a `ClickException` subclass with exit code 252 that shows the original error unchanged, usage hint included. Click declares `exit_code` as a class variable, so the code comes from a subclass, as `UnknownError` does with 255, instead of being set on the caught exception. Only 1 and 2 are mapped, so `UnknownError`'s 255 stays.

All of robotcode's own errors for these commands already are Click exceptions and Robot Framework's codes never are, so one place covers the wrapper, configuration and option errors.

Alternative: a `ConfigurationError(ClickException)` with exit code 252, raised at every place that reports such an error. It is explicit, but it misses the option errors that Click raises itself, and every new error site would have to remember it.

### Covered commands: `@wrappable` plus a marker

`@wrappable` commands are covered without further marking: they run Robot Framework, which is what that marker already states. A second marker in `click_helper`, next to `wrappable`, covers the commands that pass on a Robot Framework tool's exit code without running tests: `rebot`, `libdoc`, `testdoc`.

Alternatives: one marker on all eight commands, which puts a second marker for the same fact on every wrappable command; or a list of command names in the root group, which breaks with aliases and with commands from plugins. That is also why `@wrappable` is a marker.

### `debug` lets Click exceptions through

`debug` re-raises `click.ClickException` before its catch-all, so configuration errors reach the root group and end with 252. Every other exception stays `UnknownError` with 255.

### `analyze code` stays out

Its exit code is a bitmask (1 errors, 2 warnings, 4 infos, 8 hints). 252 has no errors bit, so a CI check like `exit & 1` would let a broken setup pass. The current 1 sets that bit.

## Risks / Trade-offs

- [A Click exception inside a covered command that isn't about the setup] → It also ends with 252. That still means "the run didn't happen as asked", and Robot Framework's codes can't be affected.
- [A new command runs Robot Framework without being marked] → It keeps Click's codes. A test lists the covered commands, as `test_execution_commands_are_marked_wrappable` does for `@wrappable`, and the marker's docstring states the rule.
- [Scripts that expect 1 for a broken configuration] → Unlikely; the code stays non-zero, so checks for success or failure behave as before.
- [Windows starts the wrapper as a child process] → A missing wrapper raises the same `OSError` and the same `ClickException`, so the mapping is the same.
