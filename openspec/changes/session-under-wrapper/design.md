# Design: session-under-wrapper

## Context

See proposal.md, Why. How the output reaches the session today (HEAD 8a8a9276f):

- `session start` creates the pipe (`create_output_pipe`; on Windows with `CreatePipe` and room for 1 MB) and gives the process the write end as its standard output and standard error. It passes the number of the read end, a handle on Windows, in the hidden option `--serve-output`, and lets the process inherit it: `pass_fds` on Linux and macOS, an inheritable handle in `handle_list` on Windows.
- `SessionServer.__init__` takes the read end with `_own_pipe(output)` before it writes the file of the session, and reads it from then on. `session start` keeps its own read end until that file appears, and reads it only when the session ends before it is ready.
- A restart: the old process stops reading and starts the new process with `start_session_process(self._command, self._pipe_handle(), ...)`. `self._command` is its own command line, `--serve-output` included. It then waits in `_wait_for_new_process` until the new process has written the file of the session. The breakpoints, the start time and the next generation go to the new process in the file `<id>.restart` (`_Handover`), which the new process reads in `__init__` before it takes the pipe.
- The wrapper (`packages/plugin/.../wrappable.py`): robotcode starts again under the `wrapper`, with `os.execvp` on Linux and macOS, which keeps inherited file descriptors, and with `subprocess.run(command)` on Windows, which passes only the standard handles. It sets `ROBOTCODE_WRAPPER_APPLIED=1`, so robotcode under the wrapper doesn't start it again. The session process keeps that variable in the environment of a restart, so a restart doesn't start the wrapper again either. Measured on Linux with a shell wrapper that logs each run: one run for `start`, `restart` and a `send`.

Measured on 2026-11-16, on Linux (Python 3.14, Robot Framework 7.5.1) and on the Windows 11 VM (Python 3.13, Robot Framework 7.4.2, as in the report; PowerShell over SSH, and from a process with a console of its own), `robotcode session start repl`:

| `wrapper` | Linux | Windows |
|---|---|---|
| none | starts | starts |
| `["python", "w.py", "--"]`, `w.py` runs its command with `subprocess.run` | `OSError: [Errno 9] Bad file descriptor` in `_own_pipe` | `OSError: [WinError 6]` in `_own_pipe` |
| `["./w.sh"]` with `exec "$@"` | starts | – |
| `["cmd", "/c"]` | – | `OSError: [WinError 6]` |
| `["cmd", "/c"]`, RobotCode's own step with `close_fds=False` (in a copy on the VM only) | – | starts |
| `w.py`, RobotCode's own step with `close_fds=False` | – | `OSError: [WinError 6]` |

A prototype outside the repository compared three ways for a process under `w.py`, which also writes a line of its own while the process runs:

| Way | Linux | Windows | Line of the wrapper |
|---|---|---|---|
| inherited number, as today | `Errno 9` | `Errno 9` (the number was another, valid handle in that process) | – |
| A: the process takes the read end from the holder | works (FIFO by path) | works (`DuplicateHandle` from the holder by its process ID) | read by the process |
| B: the holder sends the read end over a channel | works (`multiprocessing.reduction.send_handle`) | `send_handle` fails with `WinError 5`; with `DupHandle(handle, GENERIC_READ, pid)` it works | read by the process |
| C: the process creates its own pipe and moves its standard output and standard error onto it | works | works | lost: `BrokenPipeError` in the wrapper on Linux, `OSError 22` on Windows |

## Goals / Non-Goals

**Goals:**
- The session gets its output whatever the wrapper does with inherited handles other than the standard ones.
- Without a wrapper, `start`, `send`, `restart` and the output behave and take as long as today.

**Non-Goals:**
- `wrappable.py` stays as it is. Passing handles on in its Windows step would only help wrappers that pass them on themselves (measured, see Context).
- What the wrapper writes after the session process has ended, such as a message when it cleans up, goes into a pipe without a reader, as today.
- No change to the documentation.

## Decisions

### D1: The session takes the read end from the process that holds it

The read end of the pipe stays with the process that has it, `session start` or the process before a restart, and the new session process takes it from there in `__init__`, where it takes the inherited one today. Nothing has to pass through the wrapper but the standard handles. The output of the wrapper and of the processes it starts goes into the same pipe and comes with the answers (measured in the prototype). Chosen by the maintainer on 2026-11-16 from the three ways in Context.

- Rejected: B, the holder sends the read end over the channel of the session. It also needs code of its own on Windows (`send_handle` of the standard library fails, measured), adds a request before the first answer, and the session can read its pipe only after the handover. It would then have to end itself when the handover doesn't come, for example when `session start` is aborted in between.
- Rejected: C, the session creates its own pipe. Once `session start` has returned, the wrapper and the processes it started write into a pipe without a reader (measured). Their output is lost, and a wrapper can fail on it.

### D2: A FIFO on Linux and macOS

`session start` creates the FIFO `<id>.pipe` in the folder of the sessions with the mode `0600`, before it starts the process. It opens the read end without blocking, so that the open doesn't wait for a writer, and then the write end, which it gives the process as standard output and standard error. It then sets the read end to blocking again, so that reading it to its end waits for the last writer, as with the anonymous pipe today. The session opens `<id>.pipe` for reading, without blocking, as `_own_pipe` sets it today.

- The data stays in the kernel; no output goes to the disk, as the requirement "Output in memory" asks.
- A restart leaves the FIFO in place, and the new process opens it while the old one still holds its read end.
- `remove_session_files` removes `<id>.pipe` with the other files of the session. The end of a session, a session that ends before it is ready, and the next command after a crash all remove it.
- Rejected: `/proc/<pid>/fd/<n>`, which only exists on Linux.

### D3: `DuplicateHandle` on Windows

The pipe stays as it is. The session opens the holder's process with `PROCESS_DUP_HANDLE` and duplicates the handle into its own process with `DUPLICATE_SAME_ACCESS`, not inheritable, and opens a file descriptor on it with `msvcrt.open_osfhandle`.

- The holder still runs then. `session start` keeps its read end until the file of the session appears, which the session writes only after it has taken the pipe. The old process of a restart waits in `_wait_for_new_process`. So the process ID can't belong to another process yet.
- `start_session_process` no longer marks a handle inheritable and passes neither `handle_list` nor `pass_fds`: only the standard handles go to the process, which Python passes by itself when they are redirected.
- When the handle can't be taken, for example because a sandbox forbids opening the holder, the session raises `SessionError` with the process ID and the reason. `session start` reports it as it reports a channel that can't be opened.

### D4: The handover file names the holder, also for the first process

The file `<id>.restart` becomes `<id>.handover`, and `session start` writes it too, before it starts the process: generation 0, the start time and, on Windows, the holder (`_PipeHolder` with the process ID and the handle). A restart writes it as today, with the old process as the holder. The session reads it in `__init__` before it takes the pipe, as today, and fails with `SessionError` without one. The hidden option `--serve-output` goes away: on Linux and macOS the session finds the FIFO by its ID, on Windows the holder in the file.

- Rejected: `--serve-output PID:HANDLE` on the command line. A restart starts the new process with the command line of the old one, whose value names `session start`, which is gone by then. The restart would have to rewrite its command line, or a value from the file would have to override the one on the command line.
- The new name says what the file is now; with `session start` writing it, `.restart` would mislead.

### D5: Tests

`tests/robotcode/repl/test_sessions.py` gets a project folder of its own whose `robot.toml` sets a `wrapper` that runs `w.py` with `sys.executable`; the path goes into the TOML string with forward slashes, so that it holds on Windows. `w.py` starts its command with `subprocess.Popen`, waits for a file that the test creates, writes a line, creates a second file, and waits for its command. The tests cover the scenarios of the spec delta. The one with `cmd /c` runs only on Windows. Each passes with the fix and fails without it, since `start` already fails without it on Linux, macOS and Windows.

Existing tests change where they name the files of a session (`.handover` instead of `.restart`, and `.pipe` on Linux and macOS) or build a `SessionServer` with the read end (`test_a_session_that_cant_write_its_file_says_why`).

## Risks / Trade-offs

- [A sandbox forbids creating the FIFO] → `session start` says that it can't create the files of the session, as for a folder that can't be written, and exits with 252. Not tried in a sandbox.
- [A sandbox on Windows forbids opening the process of `session start`] → the session says why it can't take its output, and `start` exits with 252. Not tried in a sandbox.
- [Another process of the same user opens the FIFO] → the folder is open only to the user and the FIFO has the mode `0600`, so only processes of the user can open it, as only they can connect to the channel.
- [A FIFO may hold less than a pipe on macOS] → the session reads it from before its REPL or run starts, as today, so a writer at most waits for a moment.
- [Sessions that are open while robotcode is updated] → a restart of such a session starts the new version, which finds no `<id>.handover`. The restart fails as a restart whose new process doesn't get ready: the session stays open with its REPL or run ended, and `session start` starts a new one.

## Migration Plan

None. Rollback: revert the change; sessions open at that moment end as described under Risks.
