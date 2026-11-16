# Proposal: session-under-wrapper

## Why

`robotcode session start repl` and `robotcode session start debug` fail when the selected profiles set a `wrapper` (#690). The session process gets the read end of its output pipe as an inherited file descriptor, a handle on Windows, and finds it by the number on its command line. A wrapper that starts its command with the defaults of Python's `subprocess` doesn't pass that handle on. On Windows, RobotCode starts the wrapper that way itself, so there every wrapper fails, `cmd /c` too. Measured on 2026-11-16 on Linux and on Windows 11 (see design.md, Context).

## What Changes

- The session no longer inherits the read end of its pipe; it takes it from the process that holds it. On Linux and macOS it opens the pipe by its path, a FIFO in the folder of the sessions. On Windows it duplicates the handle from that process. The holder is `session start` for the first process of a session, and the process before for a restart.
- `session start` and `session restart` work under a `wrapper`, whatever it does with inherited handles other than the standard ones.
- The output of the wrapper and of the processes it starts while the session runs comes with the answers of the session, as the output of the session does.
- Nothing changes for sessions without a `wrapper`: the output, the answers, the exit codes and the timing of `start` stay as they are.

## Capabilities

### New Capabilities

### Modified Capabilities
- `cli-sessions`: a new requirement says that sessions start, restart and keep their output under a `wrapper`.

## Impact

- `packages/repl/src/robotcode/repl/_session.py`: how the pipe is created, taken and handed on; the files of a session (a FIFO on Linux and macOS, the file of a restart becomes the handover file of every process).
- `packages/repl/src/robotcode/repl/session_cli.py` and `cli.py`: `session start` writes the handover file; the hidden option `--serve-output` goes away.
- `tests/robotcode/repl/test_sessions.py`: tests with a wrapper.
- Not affected: `packages/plugin/.../wrappable.py` and the `wrapper` itself, the other commands, the VS Code extension and the IntelliJ plugin, the documentation (the guide on sessions doesn't mention the wrapper, and with the fix nothing needs saying).
