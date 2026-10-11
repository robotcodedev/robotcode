# Tasks

## 1. Commands that run Robot Framework

- [x] 1.1 Give the root group in `src/robotcode/cli/__init__.py` a subclass of `AliasedGroup` whose `invoke` turns a `click.ClickException` with exit code 1 or 2 into 252 while a `@wrappable` command is invoked; verify with subprocess tests in a new `tests/robotcode/cli/test_exit_codes.py`: a missing wrapper exits with 252 (also with `--nostatusrc`), an invalid `robot.toml` for `robot` exits with 252, `repl --no-such-option` exits with 252, a suite with one failing test exits with 1, `robot --nosuchoption` exits with 252, and an invalid `robot.toml` for `analyze code` and `discover tests` still exits with 1.
- [x] 1.2 Let `debug` re-raise `click.ClickException` before its catch-all in `packages/debugger/src/robotcode/debugger/cli.py`; verify with a test that `robotcode --dry debug` with an invalid `robot.toml` exits with 252 (255 before).
- [x] 1.3 Document the 252 in `docs/src/content/docs/guides/wrapper.md` (wrapper that can't be started) and after the exit code table in the "Exit code and session status" section of `docs/src/content/docs/guides/repl.md` (invalid configuration, unknown option, wrapper); verify with `npm run docs:build`.
- [x] 1.4 Add an "Exit codes" section to the hand-written part of `docs/src/content/docs/reference/cli.md`, outside the generated `<!-- START -->`/`<!-- END -->` region, that groups the commands that run Robot Framework (`robot`, `rebot`, `libdoc`, `testdoc`, `debug`, `robot-debug`, `repl`, `repl-server`), lists Robot Framework's exit codes with RobotCode's own errors under 252, and links the exit codes of `repl`, `analyze code` and `doc`; verify with `npm run docs:build`.

## 2. Robot Framework tools that pass on their exit code

- [x] 2.1 Add a marker next to `wrappable` in `packages/plugin/src/robotcode/plugin/click_helper/`, include it in the root group's check from 1.1, and mark `rebot`, `libdoc` and `testdoc`; verify with tests that an invalid `robot.toml` makes each of them exit with 252, and with a test that lists the covered commands, as `test_execution_commands_are_marked_wrappable` does for `@wrappable`.

## 3. Integration

- [x] 3.1 Run `hatch run lint:all` and `hatch run test:test`, and verify both pass on the full Robot Framework matrix.

## Workflow follow-up

- Comment on and close #666 once the change is committed and pushed.
- Archive the change after review.
