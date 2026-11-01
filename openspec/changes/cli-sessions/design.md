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

`session start` starts `robotcode` again, with the same Python, project root, profiles and options, in a hidden mode of `repl` or `robot-debug` that serves the session. The process runs detached from the starting command: in a new process session on Linux and macOS, in a new process group on Windows, with a console without a window, which the console programs it starts share instead of opening windows of their own. `session start` waits until the session reports through its channel that it is ready, prints the ID and the output so far, and returns. A restart starts the new process of a session the same way, from the session process itself (D11).

- Rejected: running the session inside the starting process. That process has to return to the agent.

### D2: The channel

Each session listens with `multiprocessing.connection.Listener`: a Unix socket in a directory only the user can open on Linux and macOS, a named pipe on Windows, both with a random authentication key. The `session` commands connect with `Client`. Requests are small messages (`send` with an input, `wait`, `interrupt`, `stop`, `status`, and for D11 `state`, `result` and `restart`). Each request gets a thread of its own in the session: the inputs of `send` requests run one after the other, while `interrupt`, `stop` and the `status` after a timeout are answered while a statement runs.

The listener keeps up to 16 connections waiting: each command connects twice, once to check the channel (D10) and once for its request, and on macOS a connection to a full queue fails at once with `Connection refused`, which the check takes for an ended session (found by the CI on macOS, 2026-10-31; `multiprocessing` listens with a queue of 1).

- Rejected: TCP on localhost. It needs a free port, and other users of the machine can reach it.

### D3: The interpreter reads from the channel

In a session, `ConsoleInterpreter` takes each line from the channel where it would call `_read()`. When it arrives at a prompt again (`>>> ` or `(rdb) `), it answers the open request with the output collected since then and the status.

- **A whole input:** A request is one input. The interpreter takes it as a whole and parses it as it parses a script file, at `>>> ` and at `(rdb) ` alike, instead of line by line as from a terminal: a block the input leaves unfinished fails with what Robot Framework says it lacks, and a session never waits at `... `. A dot-command is an input of its own; the session refuses a request that starts with one and has more lines, with the error that dot-commands can only be sent on their own (decided by the maintainer, 2026-10-30).

- **Output:** `session start` gives the session process a pipe as its standard output and standard error and passes it the other end of the pipe, so that Robot Framework's console, `Log To Console`, libraries and child processes all write into it, also on Windows, where child processes take the standard handles of the process. Once the session is ready, a thread of the session reads the pipe into memory; when the interpreter arrives at a prompt, the session reads what is still in the pipe, so that the answer has all output up to the prompt. Output a command has got is dropped; output written after an answer comes with the next answer, as before. When the session ends before it is ready, `start` reads the pipe and prints it. At a stop, the debugger breaks off the line of the run's console that Robot Framework leaves open, such as the name of a test before its status; a session knows its output and breaks it off only when it is open (2026-10-31). No output goes to a file (decided by the maintainer, 2026-10-31): the output of a REPL or a debug run can hold secrets, the runtime folder isn't always in memory, in a container for example, and a file would grow with the session.
  - Rejected: the file `<id>.out` that `start` gave the process as standard output and standard error (the first implementation). It lands on the disk wherever the runtime folder isn't in memory, grows for the whole session, and stays on Windows until the next `session` command. Its cost in time wasn't measurable (2026-10-31, 20000 lines of `Log To Console` on Linux and Windows).
- **Status:** `passed` or `failed` from the outcome of the statement, which the interpreter knows. When the REPL exits or the run ends, the session keeps its exit code and goes on answering (D11). A keyword at a stop counts as at the REPL prompt: `Pass Execution` and `Skip` don't fail it, unless failures were continued before (2026-10-31).
- **Interrupt:** An `interrupt` request raises SIGINT in the main thread of the session process (`pthread_kill`, on Windows `raise_signal`), so that it takes the path of Ctrl-C; a Ctrl-C from outside doesn't reach a detached process on Windows. A second `interrupt` acts like a second Ctrl-C.
- **Stop:** A `stop` request takes the path of SIGTERM; for a debug run, it acts like `.abort`. After the end of the REPL or the run, it ends the session at once.

The maintainer chose this over a console in the background whose text output the commands would read (2026-10-30), so that the status needs no parsing.

### D4: Timeout and `wait`

The timeout is on the side of the command: `send` waits for its answer at most `--timeout` seconds, 60 without the option. Then it fetches the output collected so far with a `status` request, prints it and exits with 124, as `timeout(1)` does; the statement goes on, and `wait` takes over the open request. `wait` returns once the session waits at its prompt again or its REPL or run has ended.

- Rejected: no default timeout. The agent's own tool would then cut `send` off, Claude Code after two minutes by default, without telling the agent that the statement still runs.

`session start` limits with `--timeout` only the wait for the first prompt. It waits for the file of the session without counting `--timeout`, up to 60 seconds or `--timeout` when that is longer, so that a session whose ID `start` has printed can always be reached by `wait` and the other commands; a session that isn't ready by then is ended, and `start` exits with 252 (decided by the maintainer, 2026-10-31).

- Rejected: `start` writes the file of the session itself before the process starts. The check by the channel would take a session whose channel isn't open yet for ended, unless it allowed a starting session some time or asked its process ID again.

### D5: Registry and IDs

Each open session has a JSON file in `platformdirs.user_runtime_dir("robotcode")`, in a folder `sessions` only the user can read: ID, kind, process id, channel address, key, project folder, start time, time of the last request and idle timeout. The ID is the kind and eight hexadecimal characters of a random UUID, such as `repl-3f9a2c1e` (decided by the maintainer, 2026-10-30). An old ID never reaches a newer session, which a reused number such as `repl-1` would; `start` draws again in the rare case that an open session has the ID already. Sessions have no other name. A file whose channel nobody listens on any more is removed by the next `session` command that finds it (D10). On Linux without `$XDG_RUNTIME_DIR`, as in a container, platformdirs falls back to `/run/user/<uid>` or to a folder in the temporary folder and warns about it at each call; the sessions use that folder and ignore the warning (decided by the maintainer, 2026-10-31). The session replaces its file as a whole when it changes; a command that reads the file at that moment on Windows, which doesn't open it then, tries again a moment later. The file names the process and the channel of the session's current process, which a restart replaces (D11).

The project folder is the folder RobotCode finds for its `robot.toml` from the folder `session start` ran in, also for a debug run whose suite lies in another project. `session stop --project` ends the sessions of the project of the current folder, found the same way, and `session stop --all` all sessions of the user (decided by the maintainer, 2026-10-30).

### D6: Idle timeout

The session process ends itself after waiting at its prompt, or after the end of its REPL or run, for `--idle-timeout` minutes without a request, 15 by default (decided by the maintainer, 2026-10-30). A running statement doesn't count as waiting. A debug session ends as with `.abort`. `--idle-timeout` takes fractions of a minute, so tests can use a few seconds.

### D7: Exit codes

`send` and `wait` exit with 0 when the statement passed, 1 when it failed and 124 when it still runs after the timeout, also when the REPL or the run ends with it. `start` and `restart` exit with 0 once the session waits at its first prompt or its run has ended, and with 124 after `--timeout`. Robotcode's own errors (no such session, broken channel, a `send` after the end) exit with 252, as other commands that run Robot Framework do (`cli-exit-codes`).

The exit code of the REPL or the run is never the exit code of a `session` command: the text output names it at the end, the JSON output carries it as `exit_code`, and `session result` prints it (decided by the maintainer, 2026-10-31, as Robot Framework gives exit codes a meaning of its own, the number of failed tests).

- Rejected: the exit code of the run as the exit code of the command that got the end (the first implementation). 0 and 1 then meant either the outcome of an input or the end of a run with no or one failed test.
- Rejected: an exit code of their own for the end in `wait` and `send`. `session status` tells it (decided by the maintainer, 2026-10-31).

### D8: JSON

With the global `--format json`, `send` and `wait` print one object: `output`, `status` (`passed`, `failed`, `running`) and, once the REPL or the run has ended, its `exit_code`. `status` prints an object with the `state`, `result` one with the `exit_code`, and `list` a list of the sessions.

No answer carries the prompt the session waits at: each request is a whole input (D3), a debug stop shows by its banner in the output, and printed after the output the prompt looked like one to type at (decided by the maintainer, 2026-10-30). The text output adds a note on standard error while the statement still runs, and once the REPL or the run has ended with its exit code: `The run has ended with exit code 2.` or `The REPL has ended with exit code 1.`

### D9: Documentation

A page `guides/cli/sessions.md` in the Command Line group, after robot-debug: what a session is, the commands, exit codes, the end of a run and the restart, idle timeout and an example of an agent working turn by turn. `repl.md` and `robot-debug.md` link it. `reference/cli.md` is generated again.

### D10: Sandboxes

The sandbox of an agent can keep sessions from running, as that of Codex does on Linux (found on 2026-10-31 with Codex 0.166): it makes the runtime folder read-only, forbids Unix sockets without network access, and gives the commands processes of their own, whose IDs differ from those outside and which end with the command. So a session can't outlive the command that starts it there, even where the folder and the channel are allowed. RobotCode can't make sessions work in such a sandbox; it says so instead of failing with a traceback, and the skill tells an agent there to drive `robotcode repl` or `robot-debug` in its own terminal.

- Only `session start` and the session process create and write the folder of the sessions; the other `session` commands only read it.
- `start` reports a folder it can't write, and the session process a channel it can't open, with the reason and exit code 252.
- Whether a session still runs is told by its channel, not by its process ID: a channel that refuses the connection or is gone means that the session has ended; a channel that can't be reached for another reason, such as a connection the sandbox forbids, counts as open. A process ID can't tell across a sandbox with processes of its own: a session that ended inside one leaves an ID that another process has outside, and a command inside doesn't see the ID of a session outside.

### D11: The end of a run and the restart

A session stays open after its REPL has exited or its run has ended, until `stop` or the idle timeout ends it, as a debugger stays open after its program has ended (decided by the maintainer, 2026-10-31). The session process goes on serving its channel: its file says `ended`, the rest of the output waits for `wait`, `status` answers `ended`, and `result` prints the exit code. `send` and `interrupt` fail with 252 and name `restart` and `result`. A SIGTERM that the session didn't send itself for `stop` or `restart`, as at a shutdown, ends the session with its REPL or run, as it ends a debugger; the interpreter tells whether a signal ended them (found 2026-10-31, when a SIGTERM to a session process left the session open).

- Rejected: ending the session with its run (the first implementation). A run that ended while no command waited, after a `send` that returned with 124 for example, took its exit code and the rest of its output with it, and the next `wait` found no session (2026-10-31).
- Rejected: keeping only the exit code in the file of the session. The rest of the output would still be lost, as no output goes to a file (D3).

`status` asks the session with a request `state`, which takes no output, so that a script can call `wait` in a loop until `status` says `ended` (decided by the maintainer, 2026-10-31). `result` prints the exit code as a number on standard output and exits with 0; before the end, it fails with 252 (decided by the maintainer, 2026-10-31).

- Rejected: `result` exiting with the exit code of the run. Robot Framework uses almost every exit code, so no code would be left to tell "not ended yet" or robotcode's own errors from a result.

`restart` ends the REPL or the run as `stop` does, but not the session, and starts it again in a new process under the same ID (decided by the maintainer, 2026-10-31):

- **The new process:** The session process starts it itself, with its own command line, environment and folder, so that it runs with the options, profiles and environment of `session start`. It stops reading the pipe of the session then, so that only one process reads it, and the new process gets the read end as from `start`. The new process opens a channel of its own at a new address; once it is ready, it writes the file of the session with its process and channel, and the old process answers `restart` with the output since the last command and ends. `restart` then waits for the first prompt of the new process as `start` does.
- **Breakpoints:** The new process gets them as they are at the restart, with their numbers, conditions, ignore counts, logpoints and commands, the disabled ones and the exception stops of `.catch` (decided by the maintainer, 2026-10-31); breakpoints that `.delete` removed stay removed, also those of the command line. The old process writes them to a file in the folder of the sessions, which the new process reads and removes. Their hit counts start at 0, as `.ignore` counts the hits of a run.
- **Commands during a restart:** A command that finds the channel of the old process gone reads the file of the session again before it takes the session for ended, so that a restart doesn't make it remove the files. A request that still reaches the old process after the new one has taken over gets the answer that the session has moved, and the command asks the new process; so does a `stop` that came during the restart, which the old process otherwise took for its own and left the new process running (found in the review of 2026-10-31).
- **A restart that fails:** When the new process ends before it is ready, or isn't ready within 60 seconds, the old process ends it, reads what it wrote, and keeps the session with its REPL or run ended; `restart` prints that output and exits with 252.

- Rejected: a restart in the session process itself, as pdb does. It saves starting a process, but the Python modules of the first run, such as a library being worked on, stay loaded, so the new run wouldn't see their changes (decided by the maintainer, 2026-10-31).
- Rejected: the breakpoints of the command line and those added in the session. A breakpoint removed or changed in the session would come back as it is on the command line (decided by the maintainer, 2026-10-31).

### D12: Types in the session code

The session code passes typed values instead of `Dict[str, Any]`, and no text that stands for something else (decided by the maintainer, 2026-11-01, on reading the code). Except for the second move below, nothing changes for a user: the output, the JSON output, the exit codes and the file of a session stay as they are.

- **The channel:** A request is a dataclass with its kind (`Request`) and its input; `_Request`, the input in the queue of the session, becomes `_QueuedInput`, so that the names stay apart. Each answer is a dataclass of its own, and a `Union` names them all: `OutputAnswer` (`output`, `status`, and `exit_code` once the REPL or the run has ended), `StateAnswer`, `ResultAnswer`, `InterruptedAnswer`, `StoppedAnswer`, `RestartedAnswer`, `RestartFailedAnswer`, `RefusedAnswer` and `MovedAnswer`. `multiprocessing.connection` pickles them as it pickles the enums of the channel today, so neither end converts anything (tried 2026-11-01).
- **The commands:** `_request` deals with `MovedAnswer` and `RefusedAnswer`, so the commands see neither. A command that can get only one class asks for it by type and gets that class back; `stop` and `restart` tell theirs with `isinstance`, as they also get an `OutputAnswer` after their limit. `_exit_code` then needs no fallback for an answer without a status. The JSON output comes from the dataclass: `as_dict(answer, remove_defaults=True)` leaves out an `exit_code` of None and gives the same objects as before (tried 2026-11-01).
- **A second move:** `_request` follows `MovedAnswer` until the file of the session names no other channel. So far it followed one: after a second restart during the same command, the answer without a status reached the command, which then exited with 252 without a message, or with a `KeyError` in `session status`.
- **The methods that answer:** `_await` and the methods that use it always return an answer, so their `Optional` and the check in `_serve` go. `_answer` ends with `assert_never`, so that mypy reports a kind of request that it doesn't handle, in place of the answer to an unknown request.
- **The restart:** `_Handover` holds the number of the new process, the start time and a `BreakpointState`, which stands beside `Breakpoint` in `_debug/types.py` and replaces the dict of `breakpoint_state` and `restore_breakpoints`. `_take_handover` returns None for the first process of a session. A new process that doesn't get ready raises `SessionError` from `_wait_for_new_process`, instead of returning its reason as text.
- **The files:** `from_json` of `robotcode.core.utils.dataclasses` reads the file of a session and the file of a restart, with their enums and nested dataclasses, so `SessionEntry.__post_init__` goes. A broken file still counts as none: `from_json` raises `ValueError` for broken JSON and `TypeError` for missing or wrong values, which the readers catch (tried 2026-11-01). `_write_json` takes these two classes instead of `Any`.
- **Smaller places:** `self._prompt` holds an enum instead of the text of the prompt, which only served to compare it with `DEBUG_PROMPT`. `start_session_process` calls `Popen` once per platform instead of passing `_DETACHED` and `passed` as `Dict[str, Any]`, so that mypy knows the arguments. `_update_entry` takes named parameters instead of `**changes: Any`.
- **What stays:** The values of variables in `controller.py` can be anything, so `Dict[str, Any]` is right there. `SessionKind.what`, `_address` and `_minutes` produce text. `completer: Any` in `read_line` is the signature of the base class.

- Rejected: one class `Answer` with optional fields. The commands would stay almost as they are, but `status` would stay optional, with the fallback in `_exit_code`, and combinations such as `moved` with `output` would stay possible (decided by the maintainer, 2026-11-01).

Outside this change: `Breakpoint.kind` as `"line"` or `"keyword"`, the exception filters as `Set[str]` and `_dot_command_index` with its tuple of five dicts are older code of the REPL package with similar points.

## Risks / Trade-offs

- [Session processes left behind, holding a browser] → The idle timeout ends them, `session list` shows them, and stale registry files are removed.
- [An agent's sandbox ends the background processes of a command] → The session process runs in a process session or group of its own, detached from the command that started it. A sandbox that gives a command processes of its own still ends it (D10); there the agent drives the REPL or the debugger in its own terminal.
- [Named pipes and detaching behave differently on Windows] → Tests run on Windows, and the flows of the recordings are tried on the maintainer's Windows VM in PowerShell.
- [Output that the session writes before it reads its pipe] → It waits in the pipe, which holds 64 KB on Linux and macOS and is made to hold 1 MB on Windows, where the default is far smaller; `start` reads it when the session ends before it is ready.
- [Two agents work in one session] → Their inputs run one after the other; both see the same state, as two people at one terminal would.
- [Sessions whose run has ended stay open] → The idle timeout ends them as it ends a session waiting at its prompt, and `session list` shows them as `ended`.
- [A restart whose new process doesn't get ready] → The old process keeps the session, and `restart` prints what the new process wrote (D11).
- [The classes of the answers are part of the channel (D12)] → Both ends come from the same installation; only a session that outlives an update of RobotCode meets another version, as with the enums of the channel so far.
