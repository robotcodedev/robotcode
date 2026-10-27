# Design: cli-error-format

## Context

See proposal.md - Why. On `main`:

- `Application.error` (`packages/plugin/src/robotcode/plugin/__init__.py`) writes `[ ERROR ] <message>` to standard error, `ERROR` in red, with colour as `Application.color_for` decides: `--color/--no-color`, then `FORCE_COLOR`/`NO_COLOR`, then whether the stream is a terminal; the root command turns colour off in AI-agent sessions when no flag is given. Its default is `ColoredOutput.AUTO`.
- Commands stop with a `click.ClickException`. Click's `main` writes it with `show()` as `Error: <message>` without colour; a `UsageError` writes the usage line and the hint `Try '<command> --help' for help.` first (Click 8.5.0). `RobotCodeGroup.invoke` wraps such an error of a command that passes on Robot Framework's exit codes in `RobotDataError` (exit code 252), whose `show()` calls the wrapped error's `show()`. Errors of the root command's own options come from `make_context`, before `invoke`.
- `run_debugger` (`packages/debugger/src/robotcode/debugger/run.py`) writes an error that stops the run with `show()` while the session lasts, wrapping a foreign exception in `UnknownError`, and raises `_ShownError` so that it is not written twice.
- Robot Framework writes its own errors as `[ ERROR ] <message>` too (`robotcode run --nonsense tests`).

## Goals / Non-Goals

**Goals:**

- One form for robotcode's errors, whether they stop the command or not.

**Non-Goals:**

- Robot Framework's own output, warnings, and the tracebacks of unexpected exceptions.
- Exit codes.
- Messages that the IDEs build from robotcode's error output; they show the new line as it is.

## Decisions

### D1: One function writes a Click error in the form of `Application.error`

A function in `robotcode.plugin` takes a `click.ClickException` and an `Application`: for a `UsageError` with a context it writes the usage line and the hint as Click does, then it writes `format_message()` through `Application.error`. Using `Application.error` keeps the form and the colour rules in one place. An error whose class has a `show` of its own is written by it: Click's help for a group called without arguments (`NoArgsIsHelpError`) stays the help, and the debugger's error that was already shown (D3) stays silent.

- **Alternative:** change the text through Click's translation of `Error: {message}`. It gives no colour and changes every Click program in the process; rejected.

### D2: `RobotCodeGroup` writes all errors of its commands

`RobotCodeGroup` wraps every `click.ClickException` that leaves `invoke` or its own `make_context` in an error whose `show()` calls the function of D1 with the context's `Application`, and that keeps the exit code: `RobotDataError` for 252, the code of the wrapped error otherwise. Click's `main` still decides when to show it and how to exit.

An error can come before the root command has set up its `Application`: a command name that does not exist or is missing (Click resolves it before it calls the root command), or an invalid option of robotcode itself (Click stops reading the command line before it takes any value). The error then gets an `Application` set up from robotcode's own options as the root command sets it up, colours and AI-agent sessions included: from the options Click has read, or, for an invalid option, from the command line read again by Click's parser in its lenient mode (`resilient_parsing`, unknown options passed over), which runs no callbacks.

- **Alternative:** override `main` and handle the errors there. It would repeat Click's handling of `Abort`, `Exit`, closed pipes and the standalone mode; rejected.

### D3: The debugger uses the same function

`run_debugger` writes its error with the function of D1 instead of `show()`, so that a debug session shows the same line as the command line.

## Risks / Trade-offs

- [Scripts or tools that look for `Error: ` in robotcode's error output] → The exit codes stay; the specs and tests name the new line.
- [D1 repeats Click's usage line and hint] → The test of an invalid option shows them, so a Click update that changes them shows there.
