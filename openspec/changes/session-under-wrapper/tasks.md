# Tasks: session-under-wrapper

## 1. The pipe and the handover file

- [ ] 1.1 In `packages/repl/src/robotcode/repl/_session.py`, rename the file of a restart from `<id>.restart` to `<id>.handover` (D4) and give `_Handover` the holder of the read end: a `_PipeHolder` dataclass with the process ID and the handle, set on Windows only. `remove_session_files` removes `<id>.handover`, its temporary file and `<id>.pipe`. Change `test_the_files_of_a_session_that_no_longer_runs_are_removed` to leave a `<id>.handover` and, on Linux and macOS, a FIFO `<id>.pipe` made with `os.mkfifo`. Verify that it passes.
- [ ] 1.2 Create and take the pipe as in D2 and D3:
  - `create_output_pipe(session_id)` creates the FIFO `<id>.pipe` with the mode `0600` on Linux and macOS, opens the read end without blocking, then the write end, and sets the read end to blocking. On Windows it stays as it is.
  - A function that replaces `_own_pipe` opens the FIFO by the session's ID on Linux and macOS, and duplicates the handle from the holder on Windows. It raises `SessionError` with the reason when it can't.
  - `start_session_process` loses its `output` parameter, the inheritable handle, `handle_list` and `pass_fds`.
  - `SessionServer.__init__` takes the pipe with the holder from the handover file, and fails with `SessionError` without that file. `_start_again` writes the handover file with its own process as the holder.
  - `session_cli._start` writes the handover file (generation 0, the start time, the holder) before it starts the process, and no longer passes `--serve-output`. A FIFO that can't be created gives the message "Can't create the files of the session in …", as a folder that can't be written does.
  - `packages/repl/src/robotcode/repl/cli.py` drops `--serve-output` from `SESSION_OPTIONS`, from `_session_server` and from `repl` and `robot-debug`.

  Change `test_a_session_that_cant_write_its_file_says_why` to the new way of taking the pipe. Verify that `hatch run test.rf75:test tests/robotcode/repl/test_sessions.py` passes.
- [ ] 1.3 Add the tests of D5 for the scenarios of the spec delta: a REPL session and a debug session under the `w.py` wrapper, the line of the wrapper in the answer of the next `send`, a restart under the wrapper, and `["cmd", "/c"]` on Windows only. Verify that they pass with the change and fail without it.
- [ ] 1.4 Add a test for a session process that can't take its output: on Linux and macOS without `<id>.pipe`, on Windows with the process ID of a process that has ended as the holder. `SessionServer` raises `SessionError` that names the reason, and no file of the session stays behind. Verify that the test passes.

## 2. Verification

- [ ] 2.1 `hatch run lint:all` and `hatch run test:test` pass.
- [ ] 2.2 On Linux, the steps of #690 with the `w.py` wrapper and with a shell wrapper with `exec "$@"`: `session start repl`, `send`, `restart`, `send`, `stop`, and `session start debug` up to a stop. Each starts, and `session list` shows no session afterwards.
- [ ] 2.3 On the Windows VM (ask the user to start it), copy the working tree and run `hatch run test.rf75:test tests/robotcode/repl/test_sessions.py`. Then run the steps of 2.2 in PowerShell with the `w.py` wrapper and with `["cmd", "/c"]`, over SSH and from a process with a console of its own. Each starts, and `session list` shows no session afterwards.

## Workflow follow-up

- Commit and push only on request; the commit carries `Fixes #690`.
- Answer #690 on request.
- Archive the change.
