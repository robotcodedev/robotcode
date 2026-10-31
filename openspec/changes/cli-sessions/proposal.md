# Proposal

## Why

An AI agent without a tool that writes to a running process, such as Claude Code, can't drive `robotcode repl` or `robotcode robot-debug` turn by turn. It either pipes a fixed list of statements into them or builds its own plumbing with a FIFO, a log file, blind waits and `pkill`, as the recordings of the AI agents guide showed (findings A3–A6); that plumbing differs on every operating system. A session that RobotCode keeps running in the background, and that each command talks to, gives every agent on Linux, macOS and Windows the same way to work turn by turn, which the RobotCode skill can then teach once.

## What Changes

- **A new command group `robotcode session`:**
  - `session start repl` and `session start debug` start a REPL or a debug run in the background, with the options of `robotcode repl` and `robotcode robot-debug`. They wait until the session is ready, at its first prompt or, for a debug run, at its first stop or its end, and print the session's ID, such as `repl-3f9a2c1e`, and its output so far.
  - `session send <id> "<input>"` gives the session a whole input, one line or a block of lines, at its prompt (`>>>` or `(rdb)`), prints the output until the next prompt and exits with 0 when the statement passed and 1 when it failed. A block the input leaves unfinished fails.
  - `--timeout` limits how long `send` waits; after it, `send` returns while the statement goes on, and `session wait <id>` prints the rest. `session interrupt <id>` works like Ctrl-C at the session's terminal.
  - `session stop <id>` ends a session, `session list` shows the open sessions.
  - `session status <id>` says whether a session runs, waits at its prompt or its REPL or run has ended, `session result <id>` prints the exit code of its REPL or run once it has ended, and `session restart <id>` starts it again under the same ID in a new process, with the breakpoints as they are.
- **A session ends** with `session stop`, also while it runs, or after 15 minutes without a request; `--idle-timeout` at the start changes that time. The end of a debug run or `.exit` in the REPL leaves the session open, as a debugger stays open after its program has ended.
- **Exit codes:** a `session` command exits with how the command went, with 0, 1, 124 or 252. The exit code of the REPL or the run shows in the output, as `exit_code` in JSON and through `session result`, as Robot Framework gives exit codes a meaning of its own.
- **The console interpreter gets a channel:** in a session, it reads each line from a local channel instead of standard input, a Unix socket on Linux and macOS and a named pipe on Windows, and answers each line with its output and its status.
- **The output of a session stays in memory** until a command gets it, and no output is written to a file.
- **Where sessions can't run**, as in the sandbox of an agent: `session start` says why and exits with code 252, the other `session` commands work without writing to the folder of the sessions, and a session counts as ended when its channel is gone, not by its process ID.
- **Documentation:** a guide page on sessions in the Command Line group, and the CLI reference generated again.
- This change builds on `repl-prompt-and-statement-results`: a session shows the results of statements as `=> <value>` and never `=> None`, as the terminal REPL then does.

Not part of this change: teaching sessions in the RobotCode skill (robotframework-agent-plugins), which follows as a change of its own, and `robotcode repl-server`, which stays as it is.

## Capabilities

### New Capabilities

- `cli-sessions`: REPL and debug sessions that run in the background and that separate `robotcode session` commands start, drive, wait for, interrupt, restart, list and end.

### Modified Capabilities

None.

## Impact

- `packages/repl/`: the channel in `console_interpreter.py`, a hidden mode of `repl` and `robot-debug` that serves a session and starts its new process on a restart, the `session` command group, registered in `hooks.py`, and a registry of open sessions in a directory of the user.
- Tests in `tests/robotcode/repl/`, also on Windows.
- Documentation: a new page in `docs/src/content/docs/guides/cli/`, `reference/cli.md` generated with `hatch run create-cmd-line-docs`.
- Follow-up outside this change: the skill tells agents to use sessions for the REPL and the debugger.
