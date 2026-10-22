# Proposal

## Why

The process of RobotCode's run terminal is a script of the extension that runs with VS Code's own runtime. On Windows that runtime is `Code.exe`, a GUI program, and VS Code's terminal gives a console only to console programs: the terminal shows nothing, neither the script's lines nor the run's output, the run gets no console, and no key reaches the script. The extension tests of the run terminal fail on Windows for this reason, 5 of 7 with the minimum and the stable VS Code. The nightly build skips every dev build while main is red.

Measured on a Windows 11 machine with VS Code's own node-pty, in both ConPTY variants:
- Starting the script through `cmd.exe`, with or without a batch file, gives it a console, but Ctrl+C in a run ends `cmd` and the terminal, or makes `cmd` ask "Terminate batch job (Y/N)?".
- VS Code's task terminal runs fine there, but it cannot show RobotCode's own line before a run with the shortened command line, nor RobotCode's icon, so the maintainer rejected it.
- The same script in Python, run by `python.exe`, a console program, does everything: a real console for the run, the line before the run with all shell integration sequences, Ctrl+C once and twice, dropping a line sent at once, and closing on a key.

The prototype of that Python script also passed the checks with real runs in the Linux harness.

## What Changes

- The run terminal's process becomes a Python script of the extension, using only the standard library, run with the Python interpreter that RobotCode uses for the workspace folder, as the debug launcher. The Node.js script and its build go.
- The extension and the script talk over TCP on `127.0.0.1` instead of a Unix socket or a named pipe; the extension accepts only connections that name a run terminal's key.
- The extension sends the script the text that the terminal shows before a run, so the command line `robotcode …`, its quoting and the shell integration sequences stay in the extension's TypeScript.
- What users see stays the same, on Linux and macOS as today: the lines, the decoration, the robot icon, the reuse and closing on a key. On Windows the run terminal now works.
- The extension tests need a Python interpreter; the CI's extension test job gets one.

## Capabilities

### New Capabilities

### Modified Capabilities
- `vscode-run-terminal`: the run terminal is the run's input and output on Windows too, and a second Ctrl+C ends a run that Robot Framework is stopping.

## Impact

- **Code:**
  - a new `bundled/tool/utils/run_terminal.py`, next to `check_robot_version.py`, which the extension also runs with the folder's interpreter;
  - `vscode-client/extension/runTerminals.ts` (terminal creation, TCP server, text before a run) and `debugmanager.ts` (the folder's interpreter);
  - `vscode-client/runTerminal/`: the script `index.ts` and its project in `esbuild.mjs` go, and `commandLine.ts` and `shellIntegration.ts` move into `vscode-client/extension/`.
- **Tests:**
  - `vscode-client/test/runTerminals.test.ts` runs the terminals with a Python interpreter;
  - unit tests for the script under `tests/`;
  - `.github/workflows/build-test-package.yml` sets up Python for `test-vscode`;
  - `CONTRIBUTING.md` says that `npm test` needs Python.
- **Debugger:** unchanged.
- **Docs:** unchanged; the guide describes the run terminal as it stays.
