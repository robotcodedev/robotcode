# Proposal

## Why

Since VS Code 1.131 the Python Environments extension manages the Python environments, and in its default activation mode it types an activation command such as `source <env>/bin/activate` into every new visible terminal. RobotCode runs tests in the integrated terminal by default: the debug launcher asks VS Code with DAP `runInTerminal`, and VS Code types the run's command into a shell of a terminal it creates itself. Measured on 2026-10-21 (Python 2026.10.0, Python Environments 1.40.0): the run's command came first, the activation text landed in the running Robot Framework process, and the shell ran it after the run. The first run in a new terminal ran without the activated environment, the second run in the reused terminal with it, so a test that calls a program from the environment can fail in the first run and pass in the next. RobotCode cannot prevent the typing, since VS Code creates that terminal.

The maintainer wants a terminal of RobotCode's own instead, which behaves like the terminal of a VS Code build task: it keeps the output of a run, says that it will be reused, and closes on a key.

## What Changes

- **New console value `robotcodeTerminal`** for `console` in RobotCode's launch configurations and for the setting `robotcode.debug.defaultConsole`, and the new default of both. `internalConsole`, `integratedTerminal` and `externalTerminal` stay as they are.
- **Runs start in a terminal of RobotCode.** With `robotcodeTerminal`, a run or debug session, from the Test Explorer, the editor or a launch configuration, runs as the process of a terminal that RobotCode creates, without a shell. No activation text reaches the run, and every run gets the same environment: the interpreter that RobotCode uses for the workspace folder, as today. The run keeps the terminal as its input and output, so colors, Robot Framework's progress line and Ctrl+C work as in a shell.
- **The terminal is reused.** After a run, the terminal says that RobotCode will reuse it and that a key closes it. The next run with the same name in the same workspace folder runs in it; a run that starts while it is busy gets a terminal of its own. VS Code does not restore it after a restart.
- **Stop** in the debug toolbar ends a run as today.
- **Behavior change** for users without their own setting: after a run, its terminal no longer holds a shell. `integratedTerminal` keeps today's behavior.
- Not in this change: activating the environment for runs. The Python Environments API's `activatedRun` is the plain interpreter for venv and conda environments in 1.40.0, so it would change nothing; the question stays open in idea 27 of `playground/vscode-extension-review-ideen.md`.

## Capabilities

### New Capabilities

- `vscode-run-terminal`: where RobotCode's VS Code extension runs tests and debug sessions: the console values, RobotCode's run terminal, its reuse and closing, and the environment of a run in it.

### Modified Capabilities

- `vscode-user-guide`: the page Running and debugging also explains where the output of a run appears and which console values there are.

## Impact

- **VS Code extension:** `vscode-client/extension/debugmanager.ts` (the launcher's start event, the run terminals), a new terminal script built by `esbuild.mjs` into `out/`, `package.json` (enum, default and descriptions of `console` and `robotcode.debug.defaultConsole`), the generated settings reference (`hatch run create-vscode-settings-docs`).
- **Debugger:** `packages/debugger/src/robotcode/debugger/launcher/server.py`, the `console` value and the start of the run.
- **Docs:** `docs/src/content/docs/guides/vscode/running-and-debugging.mdx`.
- **Tests:** `tests/robotcode/debugger/test_launcher.py`, the extension tests in `vscode-client/test/`.
- **Not touched:** the PyCharm plugin, which does not use the launcher's console; the behavior of `internalConsole`, `integratedTerminal` and `externalTerminal`.
