# Design

## Context

- **The console interpreter** (`packages/repl/src/robotcode/repl/console_interpreter.py`) waits for input at three prompts, all through `_read(prompt)`: `>>> ` and `... ` in the REPL, `(rdb) ` at a debugger stop. Its own output goes through `_echo`; Robot Framework's console output and `Log To Console` write to `sys.__stdout__`.
- **Ctrl-C and SIGTERM** are handled in `BaseInterpreter` (`_interrupt_waiting`, `_pause_on_interrupt`, `_termination_requested`): a detached REPL fails the running statement with `Execution interrupted`, an attached debugger pauses at the next keyword (`session-interrupt`), and SIGTERM ends a session or run (`session-termination`).
- **The commands** `repl` and `robot-debug` are defined in `cli.py` and registered in `hooks.py`; `repl-server` is a separate package and stays as it is.
- **User directories** come from `platformdirs`, as in `packages/robot/src/robotcode/robot/config/utils.py`.
- **The standard library** has `multiprocessing.connection` with the families `AF_UNIX` (Linux, macOS) and `AF_PIPE` (named pipes, Windows) and an authentication key.
- **The change `repl-prompt-and-statement-results`** comes first: it shows `=> <value>` after each statement and never `=> None`, so a session's answers carry results.

## Goals / Non-Goals

**Goals:**
- One way to work turn by turn for every agent on Linux, macOS and Windows.
- The status of a statement without reading it from text.
- No session processes left behind.

**Non-Goals:**
- `robotcode repl-server`, remote access over the network, several clients working in one session at the same time.
- The RobotCode skill, which follows as a change of its own.

## Decisions

### D1: A detached session process

`session start` starts `robotcode` again, with the same Python, project root, profiles and options, in a hidden mode of `repl` or `robot-debug` that serves the session. The process runs detached from the starting command: in a new process session on Linux and macOS, in a new process group without a console on Windows. `session start` waits until the session reports through its channel that it is ready, prints the ID and the output so far, and returns.

- Rejected: running the session inside the starting process. That process has to return to the agent.

### D2: The channel

Each session listens with `multiprocessing.connection.Listener`: a Unix socket in a directory only the user can open on Linux and macOS, a named pipe on Windows, both with a random authentication key. The `session` commands connect with `Client`. Requests are small messages (`send` with a line, `wait`, `interrupt`, `stop`, `status`); the session serves them one at a time, and a second request waits for the first.

- Rejected: TCP on localhost. It needs a free port, and other users of the machine can reach it.

### D3: The interpreter reads from the channel

In a session, `ConsoleInterpreter` takes each line from the channel where it would call `_read()`. When it arrives at a prompt again (`>>> `, `... ` or `(rdb) `), it answers the open request with the output collected since then, the status and the prompt.

- **Output:** The session process redirects its file descriptors 1 and 2 into a buffer, so Robot Framework's console, `Log To Console`, libraries and child processes all end up in the answer.
- **Status:** `passed` or `failed` from the outcome of the statement, which the interpreter knows; `ended` when the REPL exits or the run ends.
- **Interrupt:** An `interrupt` request takes the path a SIGINT takes today, inside the session process and without a signal, which a detached process on Windows can't receive. A second `interrupt` acts like a second Ctrl-C.
- **Stop:** A `stop` request takes the path of SIGTERM; for a debug run, it acts like `.abort`.

The maintainer chose this over a console in the background whose text output the commands would read (2026-10-30), so that the status needs no parsing.

### D4: Timeout and `wait`

The timeout is on the side of the command: `send` waits for its answer at most `--timeout` seconds, 60 without the option. Then it fetches the output collected so far with a `status` request, prints it and exits with 124, as `timeout(1)` does; the statement goes on, and `wait` takes over the open request.

- Rejected: no default timeout. The agent's own tool would then cut `send` off, Claude Code after two minutes by default, without telling the agent that the statement still runs.

### D5: Registry and IDs

Each open session has a JSON file in `platformdirs.user_runtime_dir("robotcode")`, in a folder `sessions` only the user can read: ID, kind, process id, channel address, key, project folder, start time, time of the last request and idle timeout. The ID is the kind and eight hexadecimal characters of a random UUID, such as `repl-3f9a2c1e` (decided by the maintainer, 2026-10-30). An old ID never reaches a newer session, which a reused number such as `repl-1` would; `start` draws again in the rare case that an open session has the ID already. Sessions have no other name. A file whose process no longer runs is removed by the next `session` command that finds it.

### D6: Idle timeout

The session process ends itself after waiting at its prompt for `--idle-timeout` minutes without a request, 15 by default (decided by the maintainer, 2026-10-30). A running statement doesn't count as waiting. A debug session ends as with `.abort`. `--idle-timeout` takes fractions of a minute, so tests can use a few seconds.

### D7: Exit codes

`send` and `wait` exit with 0 when the statement passed, 1 when it failed, 124 when it still runs after the timeout, and with the run's exit code when a debug run ends. Robotcode's own errors (no such session, broken channel) exit with 252, as other commands that run Robot Framework do (`cli-exit-codes`).

### D8: JSON

With the global `--format json`, `send` and `wait` print one object: `output`, `status` (`passed`, `failed`, `running`, `ended`) and `prompt` (`>>>`, `...`, `(rdb)` or `null`). `list` prints a list of the sessions.

### D9: Documentation

A page `guides/cli/sessions.md` in the Command Line group, after robot-debug: what a session is, the commands, exit codes, idle timeout and an example of an agent working turn by turn. `repl.md` and `robot-debug.md` link it. `reference/cli.md` is generated again.

## Risks / Trade-offs

- [Session processes left behind, holding a browser] → The idle timeout ends them, `session list` shows them, and stale registry files are removed.
- [An agent's sandbox ends the background processes of a command] → The session process runs in a process session or group of its own, detached from the command that started it.
- [Named pipes and detaching behave differently on Windows] → Tests run on Windows, and the flows of the recordings are tried on the maintainer's Windows VM in PowerShell.
- [Two agents work in one session] → Requests are served one at a time; both see the same state, as two people at one terminal would.
