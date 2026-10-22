# Design

## Context

The launcher starts an `internalConsole` run with `dict(os.environ)` updated with the run's `env` ([server.py](../../../packages/debugger/src/robotcode/debugger/launcher/server.py)). For `robotcodeTerminal`, it sends the run's `env` to the extension, and the run terminal's script merges it over its own environment. After `vscode-run-terminal-python`, that script is `bundled/tool/utils/run_terminal.py`, with `{**os.environ, **env}`.

Python's `os.environ` keeps Windows names in upper case, so the run's `Path` or `path` ends up next to `PATH`:
- CPython 3.11 and newer sort such duplicates without regard to case when starting a process and keep the last one (`normalize_environment` in `_winapi.c`).
- CPython 3.10 passes both spellings. A Python child then sees the last, while Windows itself, and with it every native program and the search for programs, finds the first.

The extension already merges without regard to case for its own processes (`mergeEnvironment` in `pythonmanger.ts`), and VS Code does for its terminals (`mergeEnvironments` in `terminalEnvironment.ts`).

## Goals / Non-Goals

**Goals:**
- One rule in both places, independent of the Python version: a name from the run's `env` replaces an inherited variable of any case on Windows.

**Non-Goals:**
- No change on Linux and macOS, where names are case-sensitive.
- No change to `integratedTerminal`, which VS Code merges itself.
- `externalTerminal` and the analyzer's environment for `%{VAR}` stay as they are; they were not measured.

## Decisions

### D1: The same small merge in both places

Each place gets a function `merged_environment(base, env, windows)`. On Windows it drops every variable of `base` whose name, in upper case, is also a name of `env`, then adds `env`; elsewhere it adds `env` to `base`. It keeps the spelling of `env`, as `mergeEnvironment` does. Of two names in `env` that differ only in case, for example `path` from `robotcode.robot.env` and `Path` from a launch configuration, it keeps the last: the extension puts a launch configuration's variables after those of `robotcode.robot.env`, so that they win.

- The launcher calls it for `internalConsole` with `os.environ`.
- The script calls it for each run with its own environment.

The function exists twice, once in the launcher and once in the script, because the script runs with `-I` and imports nothing from RobotCode's packages.

- **Alternative: keep the inherited spelling, as VS Code does.** Either spelling names the same variable on Windows. `mergeEnvironment` already keeps the run's, so RobotCode stays consistent with itself.
- **Alternative: require Python 3.11.** RobotCode supports 3.10, and the Node.js case had no Python at all.

### D2: Tested without Windows

The functions take `windows` as a parameter, so the unit tests run on every platform:
- the launcher's in `tests/robotcode/debugger/test_launcher.py`;
- the script's in `tests/bundled/test_run_terminal.py`.

Cases:
- the run's `path` replaces `Path`, and the run's `Path` replaces `PATH`;
- other names stay;
- of two spellings in `env`, the last one stays;
- with `windows=False`, both names stay.

The real check runs on the Windows VM with Python 3.10 and 3.14, `Path` set as `path`, and a run that starts `cmd`.

## Risks / Trade-offs

- [Two copies of the same rule.] → Both are small and tested with the same cases.
- [This change depends on `vscode-run-terminal-python`.] → It is applied after that change. Applied before, the Node.js script would need the same rule.
