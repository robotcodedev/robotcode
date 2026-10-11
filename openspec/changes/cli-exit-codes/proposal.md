# Proposal

## Why

Commands such as `robotcode robot` pass on Robot Framework's exit code, where 1–250 is the number of failed tests and 252 means invalid data or command line options. When robotcode itself reports an error for such a command — a wrapper that doesn't start, a broken `robot.toml`, an invalid option — it exits with Click's 1 or 2, so a CI job can't tell a broken setup from one or two failed tests ([#666](https://github.com/robotcodedev/robotcode/issues/666)).

## What Changes

- Commands that run Robot Framework or pass on the exit code of a Robot Framework tool exit with 252 when robotcode itself reports an error for them, instead of 1 or 2. These are the commands that run Robot Framework (`robot`, `debug`, `repl`, `robot-debug`, `repl-server`) and the ones that pass on a Robot Framework tool's exit code (`rebot`, `libdoc`, `testdoc`).
- Robot Framework's own exit codes pass through unchanged, and so do unexpected errors, which already exit with 255.
- `debug` reports such errors with 252 too; today it turns every error into 255.
- All other commands (`analyze`, `discover`, `results`, `config`, `profiles`, …) keep their exit codes. `analyze code` in particular keeps 1: its exit code is a bitmask, and 252 lacks the errors bit.

## Capabilities

### New Capabilities

- `cli-exit-codes`: the exit codes of robotcode commands that run Robot Framework or pass on a Robot Framework tool's exit code, for robotcode's own errors.

### Modified Capabilities

None.

## Impact

- `src/robotcode/cli/__init__.py`: the root command group maps the exit code; the wrapper start error is one of the errors it covers.
- `packages/plugin` (`click_helper`): a marker for the commands that pass on a Robot Framework tool's exit code, next to `@wrappable`.
- `packages/runner` (`rebot`, `libdoc`, `testdoc`): carry the new marker.
- `packages/debugger` (`debug`): lets Click errors through instead of turning them into 255.
- Tests under `tests/robotcode/cli/`; a sentence in the wrapper guide and in the REPL guide's exit code section.
- Not breaking: only the exit codes of error cases change, and they stay non-zero.
