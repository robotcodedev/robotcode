# Tasks: session-under-wrapper

## 1. The pipe and the handover file

- [x] 1.1 In `packages/repl/src/robotcode/repl/_session.py`, rename the file of a restart from `<id>.restart` to `<id>.handover` (D4) and give `_Handover` the holder of the read end: a `_PipeHolder` dataclass with the process ID and the handle, set on Windows only. `remove_session_files` removes `<id>.handover`, its temporary file and `<id>.pipe`. Change `test_the_files_of_a_session_that_no_longer_runs_are_removed` to leave a `<id>.handover` and, on Linux and macOS, a FIFO `<id>.pipe` made with `os.mkfifo`. Verify that it passes.
- [x] 1.2 Create and take the pipe as in D2 and D3:
  - `create_output_pipe(session_id)` creates the FIFO `<id>.pipe` with the mode `0600` on Linux and macOS, opens the read end without blocking, then the write end, and sets the read end to blocking. On Windows it stays as it is.
  - A function that replaces `_own_pipe` opens the FIFO by the session's ID on Linux and macOS, and duplicates the handle from the holder on Windows. It raises `SessionError` with the reason when it can't.
  - `start_session_process` loses its `output` parameter, the inheritable handle, `handle_list` and `pass_fds`.
  - `SessionServer.__init__` takes the pipe with the holder from the handover file, and fails with `SessionError` without that file. `_start_again` writes the handover file with its own process as the holder.
  - `session_cli._start` writes the handover file (generation 0, the start time, the holder) before it starts the process, and no longer passes `--serve-output`. A FIFO that can't be created gives the message "Can't create the files of the session in …", as a folder that can't be written does.
  - `packages/repl/src/robotcode/repl/cli.py` drops `--serve-output` from `SESSION_OPTIONS`, from `_session_server` and from `repl` and `robot-debug`.

  Change `test_a_session_that_cant_write_its_file_says_why` to the new way of taking the pipe. Verify that `hatch run test.rf75:test tests/robotcode/repl/test_sessions.py` passes.
- [x] 1.3 Add the tests of D5 for the scenarios of the spec delta: a REPL session and a debug session under the `w.py` wrapper, the line of the wrapper in the answer of the next `send`, a restart under the wrapper, and `["cmd", "/c"]` on Windows only. Verify that they pass with the change and fail without it.
- [x] 1.4 Add a test for a session process that can't take its output: on Linux and macOS without `<id>.pipe`, on Windows with the process ID of a process that has ended as the holder. `SessionServer` raises `SessionError` that names the reason, and no file of the session stays behind. Verify that the test passes.

## 2. Verification

- [x] 2.1 `hatch run lint:all` and `hatch run test:test` pass.
- [x] 2.2 On Linux, the steps of #690 with the `w.py` wrapper and with a shell wrapper with `exec "$@"`: `session start repl`, `send`, `restart`, `send`, `stop`, and `session start debug` up to a stop. Each starts, and `session list` shows no session afterwards.
- [x] 2.3 On the Windows VM (ask the user to start it), copy the working tree and run `hatch run test.rf75:test tests/robotcode/repl/test_sessions.py`. Then run the steps of 2.2 in PowerShell with the `w.py` wrapper and with `["cmd", "/c"]`, over SSH and from a process with a console of its own. Each starts, and `session list` shows no session afterwards.

## 3. Fixes from the review

- [x] 3.1 Files and messages: `session_cli._start` removes the files of the session when `start_session_process` fails. `_take_pipe` opens the file descriptor inside its `try`, `SessionServer.__init__` no longer creates the folder of the sessions, and `_take_handover` names the reason when the handover file can't be read. The docstring of `start_session_process` says where the read end comes from on each platform. The Windows test with a holder that has ended keeps that process's object, so that Windows can't give its ID to another process. Verify that `test_a_session_process_that_cant_be_started_leaves_no_files` and `test_a_session_without_a_handover_file_it_can_read_says_why` pass.
- [x] 3.2 The size of the FIFO on Linux (D2): `create_output_pipe` sets 1 MiB with `F_SETPIPE_SZ`. Add `test_a_session_starts_under_a_wrapper_that_writes_much_before_it`, skipped on macOS. Verify that it passes with the change and fails without it on Linux.
- [x] 3.3 A start that fails (D6): `start_session_process` returns a `SessionProcess` with its process group, or on Windows its job (`_windows_job.py`, a start with `CREATE_SUSPENDED`, then `resume`), and `end` ends both. `session_cli._start` reads the pipe with `read_available`. Add `test_a_start_that_fails_under_a_wrapper_ends_what_the_wrapper_started` for a start that isn't ready in time and one whose wrapper exits first. Verify that it passes with the change and fails without it, on Linux and on Windows.
- [x] 3.4 A start that is aborted (D7): the job has `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` until `SessionProcess.release`, which `session_cli._start` calls once the session is ready, as `_start_again` does for a restart. While `_start` waits, SIGTERM and SIGHUP raise `SystemExit` on Linux and macOS, and on any exception it ends the session and removes its files. Add `test_a_start_that_is_aborted_ends_the_session` with SIGINT, SIGTERM and SIGHUP on Linux and macOS, and a kill on Windows. Verify that it passes with the change and fails without it, on Linux and on Windows.
- [x] 3.5 `hatch run lint:all` and `hatch run test:test` pass, and on the Windows VM `tests/robotcode/repl/test_sessions.py` passes.

## Workflow follow-up

- Commit and push only on request; the commit carries `Fixes #690`.
- Answer #690 on request.
- Archive the change.
