# Proposal: session-under-wrapper

## Why

`robotcode session start repl` and `robotcode session start debug` fail when the selected profiles set a `wrapper` (#690). The session process gets the read end of its output pipe as an inherited file descriptor, a handle on Windows, and finds it by the number on its command line. A wrapper that starts its command with the defaults of Python's `subprocess` doesn't pass that handle on. On Windows, RobotCode starts the wrapper that way itself, so there every wrapper fails, `cmd /c` too. Measured on 2026-11-16 on Linux and on Windows 11 (see design.md, Context).

## What Changes

- The session no longer inherits the read end of its pipe; it takes it from the process that holds it. On Linux and macOS it opens the pipe by its path, a FIFO in the folder of the sessions. On Windows it duplicates the handle from that process. The holder is `session start` for the first process of a session, and the process before for a restart.
- `session start` works under a `wrapper`, whatever it does with inherited handles other than the standard ones. `session restart`, which `remove-session-restart` removes, goes on working, but its new process runs without the wrapper: a wrapper that runs its command as a child, such as `xvfb-run`, ends with the old process (measured on 2026-11-16).
- The output of the wrapper and of the processes it starts while the session runs comes with the answers of the session, as the output of the session does.
- A `session start` that fails, because the session ends before it is ready or isn't ready in time, also ends the processes that the wrapper has started, and no longer waits for them.
- On Linux the pipe holds 1 MiB, as on Windows, so that a wrapper can write that much before the session is ready.
- A `session start` that is aborted before the session is ready, by Ctrl-C, SIGTERM or SIGHUP, or on Windows in any way, ends the session, with and without a `wrapper`. Before, the session ran on until its idle timeout, with an ID that `start` had never printed.
- Otherwise nothing changes for sessions without a `wrapper`: the output, the answers, the exit codes and the timing of `start` stay as they are.

## Capabilities

### New Capabilities

### Modified Capabilities
- `cli-sessions`: a new requirement says that sessions start and keep their output under a `wrapper`, another that an aborted `start` ends the session.

## Impact

- `packages/repl/src/robotcode/repl/_session.py`: how the pipe is created, taken and handed on; the files of a session (a FIFO on Linux and macOS, the file of a restart becomes the handover file of every process).
- `packages/repl/src/robotcode/repl/_windows_job.py` (new): the job object on Windows that ends a session together with the processes it has started.
- `packages/repl/src/robotcode/repl/session_cli.py` and `cli.py`: `session start` writes the handover file, and ends the session when it fails or is aborted; the hidden option `--serve-output` goes away.
- `tests/robotcode/repl/test_sessions.py`: tests with a wrapper.
- Not affected: `packages/plugin/.../wrappable.py` and the `wrapper` itself, the other commands, the VS Code extension and the IntelliJ plugin, the documentation (the guide on sessions doesn't mention the wrapper, and with the fix nothing needs saying; that an aborted `start` ends the session needs no mention either, as decided by the maintainer on 2026-11-16).
