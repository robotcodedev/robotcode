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
- Without a wrapper, `start`, `send`, `restart` and the output behave and take as long as today, except for a `start` that is aborted (D7).
- A `start` that fails or is aborted leaves no process of the session behind, also none that a wrapper has started (D6, D7).

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

`session start` creates the FIFO `<id>.pipe` in the folder of the sessions with the mode `0600`, before it starts the process. It opens the read end without blocking, so that the open doesn't wait for a writer, and then the write end, which it gives the process as standard output and standard error. It reads its read end only when the session ends before it is ready, and then only what the FIFO holds (D6). The session opens `<id>.pipe` for reading, without blocking, as `_own_pipe` sets it today.

- The data stays in the kernel; no output goes to the disk, as the requirement "Output in memory" asks.
- On Linux `session start` sets the size of the FIFO to 1 MiB with `F_SETPIPE_SZ`, as much as a user may set by default (`/proc/sys/fs/pipe-max-size`), as large as the pipe on Windows. Until the session is ready, nothing reads the pipe: with the default size of 64 KiB, a wrapper that wrote 100 KB before it started its command made `start` wait 60 seconds and fail with 252 (measured on 2026-11-16). Chosen by the maintainer on 2026-11-16. Rejected: `session start` reads the pipe while it waits and prints what came before the first answer. That has no limit, but it changes for every session which process reads the pipe when, and needs tests for the order.
- A restart leaves the FIFO in place, and the new process opens it while the old one still holds its read end.
- `remove_session_files` removes `<id>.pipe` with the other files of the session. The end of a session, a session that ends before it is ready, and the next command after a crash all remove it.
- Rejected: `/proc/<pid>/fd/<n>`, which only exists on Linux.

### D3: `DuplicateHandle` on Windows

The pipe stays as it is. The session opens the holder's process with `PROCESS_DUP_HANDLE` and duplicates the handle into its own process with `DUPLICATE_SAME_ACCESS`, not inheritable, and opens a file descriptor on it with `msvcrt.open_osfhandle`.

- The holder still runs then. `session start` keeps its read end until the file of the session appears, which the session writes only after it has taken the pipe. The old process of a restart waits in `_wait_for_new_process`. When `session start` ends before that, the session ends with it (D7), so the session doesn't take a handle from another process that has got the same ID.
- `start_session_process` no longer marks a handle inheritable and passes neither `handle_list` nor `pass_fds`: only the standard handles go to the process, which Python passes by itself when they are redirected.
- When the handle can't be taken, for example because a sandbox forbids opening the holder, the session raises `SessionError` with the process ID and the reason. `session start` reports it as it reports a channel that can't be opened.

### D4: The handover file names the holder, also for the first process

The file `<id>.restart` becomes `<id>.handover`, and `session start` writes it too, before it starts the process: generation 0, the start time and, on Windows, the holder (`_PipeHolder` with the process ID and the handle). A restart writes it as today, with the old process as the holder. The session reads it in `__init__` before it takes the pipe, as today, and fails with `SessionError` without one. The hidden option `--serve-output` goes away: on Linux and macOS the session finds the FIFO by its ID, on Windows the holder in the file.

- Rejected: `--serve-output PID:HANDLE` on the command line. A restart starts the new process with the command line of the old one, whose value names `session start`, which is gone by then. The restart would have to rewrite its command line, or a value from the file would have to override the one on the command line.
- The new name says what the file is now; with `session start` writing it, `.restart` would mislead.

### D5: Tests

`tests/robotcode/repl/test_sessions.py` gets a project folder of its own whose `robot.toml` sets a `wrapper` that runs `w.py` with `sys.executable`; the command goes into the TOML file as a JSON array, as in `tests/robotcode/cli/test_wrapper.py`, so that the backslashes of Windows paths hold. `w.py` starts its command with `subprocess.Popen`, waits for a file that the test creates, writes a line, creates a second file, and waits for its command. The tests cover the scenarios of the spec delta. The one with `cmd /c` runs only on Windows. Each passes with the fix and fails without it, since `start` already fails without it on Linux, macOS and Windows.

Existing tests change where they name the files of a session (`.handover` instead of `.restart`, and `.pipe` on Linux and macOS) or build a `SessionServer` with the read end (`test_a_session_that_cant_write_its_file_says_why`).

For D2, D6 and D7, `w.py` writes 100 KB before it starts its command, when the test asks for it, and a second wrapper starts a child that runs for ten minutes and writes its process ID to a file, then waits for it or exits with 3. The tests check that `start` prints the 100 KB, that a start that fails ends the child and exits as the scenarios say, and that a start that is aborted ends the child and leaves no files. For the last one `session start` runs in a process of its own, which the test ends with SIGINT, SIGTERM and SIGHUP on Linux and macOS, and kills on Windows. Each passes with its fix and fails without it, on Linux and on Windows; the 100 KB fail without the fix only on Linux, since the pipe on Windows holds 1 MB already.

### D6: A start that fails ends what the session process has started

When the session process ends before it is ready, or isn't ready in time, `session start` ends it together with the processes it has started, such as the wrapper and its children. It then prints what the pipe holds at that moment, `read_available`: `PeekNamedPipe` on Windows, a read without blocking on Linux and macOS. Before, it ended only the process it had started and then read the pipe until the last writer had closed it. Under a wrapper whose processes outlive it, `start` waited for them, up to the idle timeout of the session (found in a review on 2026-11-16; measured with a wrapper that exits while its child runs on).

- Linux and macOS: the process leads a process group of its own (`start_new_session`), which `os.killpg` ends.
- Windows: the process starts suspended (`CREATE_SUSPENDED`), goes into a job object of its own (`_windows_job.py`, with `ctypes`, as `_winapi` has no job functions) and runs only then, so that nothing it starts is outside the job. `TerminateJobObject` ends the job. `Popen` closes the handle of the thread (CPython `subprocess.py`), so `resume` finds the thread with `CreateToolhelp32Snapshot` and resumes it with `ResumeThread`. The job allows processes to break away (`JOB_OBJECT_LIMIT_BREAKAWAY_OK`), since the `CreateProcess` of a program that asks for it fails otherwise. When Windows doesn't put the process into the job, the session starts anyway, and ending it ends only that process.
- Rejected by the maintainer: `taskkill /T /F`, which isn't guaranteed to reach every process.

### D7: An aborted start ends the session

Until the session is ready, it ends with `session start`, with and without a wrapper, however `start` ends: by Ctrl-C, by SIGTERM or SIGHUP, as when the terminal closes, or on Windows in any way. `start` also removes the files of the session where it still can. Before, the session ran on with an ID that `start` never printed, until its idle timeout. Chosen by the maintainer on 2026-11-16, for all platforms.

- Windows: the job of D6 has `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` until the session is ready. Windows ends its processes once the handle of `session start` to it is closed, also when `start` is killed. Once the session is ready, `start` clears the limit and closes the handle (`SessionProcess.release`); a restart does the same for its new process. Since the session ends with the holder, it can't take a handle from a process that has the holder's ID later (D3).
- Linux and macOS: Ctrl-C raises `KeyboardInterrupt`. While `start` waits for the session, SIGTERM and SIGHUP raise `SystemExit` with 128 plus the number of the signal. `start` then ends the process group (D6) and removes the files of the session. Python takes signal handlers only in its main thread, so a `start` that runs in another thread sets none.
- Not covered: SIGKILL on Linux and macOS. Nothing there ends the processes of a wrapper with `start` as the job does: `PR_SET_PDEATHSIG` exists only on Linux and reaches only the direct child, not the processes that a wrapper starts.
- Rejected: the session compares the start time of the holder with one in the handover file before it takes the handle. That needs more `ctypes` on both sides and covers only Windows; after an aborted start, the wrapper and the session would run on until the session fails to take the handle. Rejected: leaving it as it was and noting the risk.

## Risks / Trade-offs

- [A sandbox forbids creating the FIFO] → `session start` says that it can't create the files of the session, as for a folder that can't be written, and exits with 252. Not tried in a sandbox.
- [A sandbox on Windows forbids opening the process of `session start`] → the session says why it can't take its output, and `start` exits with 252. Not tried in a sandbox.
- [Another process of the same user opens the FIFO] → the folder is open only to the user and the FIFO has the mode `0600`, so only processes of the user can open it, as only they can connect to the channel.
- [The size of a FIFO can't be set on macOS] → once it is ready, the session reads it from before its REPL or run starts, as today, so a writer at most waits for a moment. A wrapper that writes more than the FIFO holds before the session is ready makes `start` wait until its limit and fail with 252. How much a FIFO holds on macOS isn't measured.
- [A process that the session or its wrapper starts breaks away from the job, or leaves the process group] → it runs on after a start that fails or is aborted. Such a process leaves on purpose.
- [Windows doesn't put the session process into a job] → a start that fails ends only that process, and a `start` that is killed before the session is ready leaves the session running; the session may then take a handle from a process that has got the ID of `session start` (D3). Nested jobs exist since Windows 8, so this is not expected.
- [`session start` gets SIGKILL on Linux or macOS before the session is ready] → the session runs on until its idle timeout, as before the change (D7).
- [Sessions that are open while robotcode is updated] → a restart of such a session starts the new version, which finds no `<id>.handover`. The restart fails as a restart whose new process doesn't get ready: the session stays open with its REPL or run ended, and `session start` starts a new one.

## Migration Plan

None. Rollback: revert the change; sessions open at that moment end as described under Risks.
