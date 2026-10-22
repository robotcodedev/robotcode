# Proposal

## Why

On Windows a name in the environment refers to the same variable in any case: `Path`, `PATH` and `path` are one variable. RobotCode merges a run's environment itself in two places, though, and treats the names as case-sensitive there:
- the run terminal's script, for the console value `robotcodeTerminal`;
- the debug launcher, for `internalConsole`.

When a run's `env` sets a variable that already exists in another spelling, from the launch configuration or `robotcode.robot.env`, the run gets the old value, or two values. Measured on Windows 11 by merging as each place does and starting a Python child and `cmd`:

| Merge | Run sets `PATH` | Run sets `Path` | Run sets `path` |
|---|---|---|---|
| Node.js, inherited `Path` | new value | new value | old value for both |
| Node.js, inherited `PATH` | new value | old value for both | old value for both |
| Python 3.10 | new value | Python child new, `cmd` old | Python child new, `cmd` old |
| Python 3.11 and newer | new value | new value | new value |

Python 3.10 passes both spellings on, and a native program finds the first, the old one. Python 3.11 and newer remove duplicates themselves. VS Code's terminals merge without regard to case on Windows, and so does RobotCode's extension for the processes it starts (`mergeEnvironment` in `pythonmanger.ts`). Only the run terminal and `internalConsole` lose the value.

## What Changes

- On Windows, a variable that a run's environment sets replaces an inherited variable whose name differs only in case. This holds in the run terminal's script and in the debug launcher for `internalConsole`, with every supported Python version, and for programs the run starts as well as for the run itself.
- Other platforms stay as they are.

This change builds on `vscode-run-terminal-python`, which turns the run terminal's script into a Python script; it is applied after that change.

## Capabilities

### New Capabilities

### Modified Capabilities
- `vscode-run-terminal`: the environment of a run on Windows, with `robotcodeTerminal` and with `internalConsole`.

## Impact

- **Code:** `bundled/tool/utils/run_terminal.py` (from `vscode-run-terminal-python`), `packages/debugger/src/robotcode/debugger/launcher/server.py`.
- **Tests:** `tests/bundled/test_run_terminal.py`, `tests/robotcode/debugger/test_launcher.py`.
- **Not touched:** `integratedTerminal` and the extension's own processes, which VS Code and `mergeEnvironment` already merge correctly. Not checked: `externalTerminal`, and the analyzer's environment for `%{VAR}` in `imports_manager.py`, which builds its own dictionary from `os.environ`.
