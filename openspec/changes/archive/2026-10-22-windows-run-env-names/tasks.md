# Tasks

Applied after `vscode-run-terminal-python`.

## 1. The merge (D1, D2)

- [x] 1.1 In `packages/debugger/src/robotcode/debugger/launcher/server.py`, build the `internalConsole` run's environment with `merged_environment(os.environ, env, sys.platform == "win32")` (D1). Unit tests in `tests/robotcode/debugger/test_launcher.py` with `windows=True` and `windows=False` (D2). Verify that the tests pass with the fix and, with the fix reverted once, fail. Then run `hatch run test:test tests/robotcode/debugger/test_launcher.py` and `hatch run lint:all`.
- [x] 1.2 In `bundled/tool/utils/run_terminal.py`, build each run's environment with the script's own `merged_environment` (D1). Unit tests in `tests/bundled/test_run_terminal.py` with the same cases (D2). Verify that the tests pass with the fix and, with the fix reverted once, fail. Then run `hatch run test:test tests/bundled/test_run_terminal.py` and `hatch run lint:all`.

## 2. Windows

- [x] 2.1 On the Windows VM, with Python 3.10 and 3.14 as the run's interpreter, run a test that logs `%{PATH}` and starts `cmd /c echo %PATH%`, with `path` set in `robotcode.robot.env` and once with `Path` in the launch configuration's `env`. Run it with `robotcodeTerminal` and with `internalConsole`. Check that the run and `cmd` both see the new value, and that before the fix at least one of them saw the old one.

## Workflow follow-up

- Archive the change with its delta spec synced into `openspec/specs/vscode-run-terminal/spec.md`.
