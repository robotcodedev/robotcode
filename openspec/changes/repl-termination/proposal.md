# Proposal

## Why

`robotcode repl-server` doesn't end when its session ends with an error: an invalid `robot.toml` prints a raw `TimeoutError` traceback instead of the error, and the process keeps running. And `repl`, `repl-server` and `robot-debug` ignore SIGTERM while they wait for input, for a client or at a stop, so `kill <pid>` or a CI timeout that sends SIGTERM first never ends them; only SIGKILL does. Found while re-measuring the exit codes of [#666](https://github.com/robotcodedev/robotcode/issues/666).

## What Changes

- `robotcode repl-server` shuts its server down when the session ends, also after an error. An invalid `robot.toml` is reported as `Error: Invalid TOML file …`, the process exits with 252 like the other commands that run Robot Framework, and it doesn't keep running.
- SIGTERM ends a `repl` or `repl-server` session, also while it waits for input or a client. A keyword that runs is interrupted first, the session ends as at the end of the input, its output files are written, and the process exits with 253 (Robot Framework's "Execution stopped by user").
- SIGTERM at a `robot-debug` stop ends the run as Robot Framework ends a run on SIGTERM: the debugger stops pausing, the current test fails with "Execution terminated by signal", the remaining tests don't run, and the output files are written.
- A second SIGTERM ends the process at once with 253, as in Robot Framework.
- SIGINT keeps its behavior: it interrupts a keyword that runs, and the session goes on.

## Capabilities

### New Capabilities

- `session-termination`: how `repl`, `repl-server` and `robot-debug` end when they receive SIGTERM.

### Modified Capabilities

- `cli-exit-codes`: the requirement "Own errors exit with 252" gets a scenario for `repl-server`, which today shows a traceback and keeps running instead.

## Impact

- `packages/jsonrpc2` (`server.py`): the stdio reader runs in a daemon thread, so a blocked read can't keep a process alive; this also applies to the language server and the debug launcher.
- `packages/repl_server` (`cli.py`, `interpreter.py`): closing the server and waiting for its thread without hiding the session's error; ending the session on SIGTERM; the exit code.
- `packages/repl` (`base_interpreter.py`, `console_interpreter.py`, `prompt_toolkit_interpreter.py`, `cli.py`, `_debug/controller.py`): the patched stop-signal monitor tells SIGTERM apart from SIGINT; ending the session and its exit code; ending a `robot-debug` run at a stop.
- Docs: the "Exit code and session status" section of the REPL guide and the robot-debug guide.
- Tests in `tests/robotcode/repl/`, `tests/robotcode/repl_server/` and `tests/robotcode/jsonrpc/`.
- Not breaking: SIGTERM ended none of these sessions before; SIGINT is unchanged.
