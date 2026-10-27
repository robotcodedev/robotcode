# Proposal: cli-error-format

## Why

robotcode writes its errors in two forms. An error it reports and goes on after, such as a name in `default-profiles` that selects no profile, appears as `[ ERROR ] No profile matches 'typo'.`, with `ERROR` in red on a colour terminal (`Application.error`), the form Robot Framework uses for its own errors. An error that stops a command, such as the same name given with `-p`, appears as `Error: No profile matches 'typo'.` without colour: Click writes it for the `click.ClickException` the command raises. In `robotcode run`, a mistyped Robot Framework option gives `[ ERROR ] option --nonsense not recognized` (Robot Framework), while a mistyped profile gives `Error: …` (Click). No spec or design chose the second form; the specs only name it in scenarios where it appears.

## What Changes

- An error that stops a robotcode command is written as `[ ERROR ] <message>`, exactly as robotcode writes the errors it reports, with `ERROR` in the colour of errors when colours are on (`--color/--no-color`, `NO_COLOR`, `FORCE_COLOR`, the terminal, AI-agent sessions).
- For an invalid option or argument of robotcode, the usage line and the hint to `--help` stay above it.
- A debug session that stops before Robot Framework runs shows its error in the same form.
- Exit codes do not change.

## Capabilities

### New Capabilities

- `cli-error-output`: how robotcode writes an error that stops a command.

### Modified Capabilities

- `vscode-run-terminal`: the Debug Console shows `[ ERROR ] No profile matches 'typo'.` (requirement "An error before the run reaches the run's output").
- `cli-wrapper`: the debug and REPL servers show `[ ERROR ] No profile matches 'typo'.` (requirement "Debug and REPL servers report an error of the configuration after they start").
- `intellij-test-results`: the "Terminal" tab shows `[ ERROR ] No profile matches 'typo'.` (requirement "Debug sessions show the "Terminal" tab").

## Impact

- `packages/plugin/src/robotcode/plugin/`: one function that writes a `click.ClickException` in the form of `Application.error`.
- `src/robotcode/cli/__init__.py`: `RobotCodeGroup` writes the errors of its commands and of its own options with it; `RobotDataError` keeps its exit code 252.
- `packages/debugger/src/robotcode/debugger/run.py`: the error shown before the session ends.
- Tests that expect `Error: …`: `tests/robotcode/debugger/test_error_before_the_run.py`, `tests/robotcode/repl_server/test_configuration_errors.py`, `tests/robotcode/repl_server/test_session_end.py`; new tests in `tests/robotcode/cli/`.
- IDEs show the first lines of robotcode's error output in some messages (PyCharm's profile list and test discovery, VS Code's RobotCode output); those lines read `[ ERROR ] …` then, without colour codes, since the output is a pipe.
