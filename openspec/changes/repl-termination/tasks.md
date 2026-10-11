# Tasks

## 1. repl-server ends after an error

- [ ] 1.1 Run the stdio reader of `JsonRPCServer.start_stdio` in `packages/jsonrpc2/src/robotcode/jsonrpc2/server.py` in a daemon thread instead of a `ThreadPoolExecutor` worker; verify that the existing tests in `tests/robotcode/jsonrpc/`, `tests/robotcode/language_server/` and `tests/robotcode/repl_server/` still pass.
- [ ] 1.2 In `packages/repl_server/src/robotcode/repl_server/cli.py`, call `server.close()` in the `finally`, wait up to one second for the server thread with `concurrent.futures.wait`, and exit with the interpreter's exit code when one is set; verify with subprocess tests in `tests/robotcode/repl_server/` that `repl-server` with an invalid `robot.toml` prints `Error: Invalid TOML file`, no traceback, and exits with 252 within a few seconds, with stdin at EOF and with stdin kept open.

## 2. SIGTERM ends a REPL session

- [ ] 2.1 Split the patched stop-signal monitor in `packages/repl/src/robotcode/repl/base_interpreter.py` by signal: SIGINT keeps today's path; on SIGTERM count separately, end the process with `os._exit(253)` and Robot Framework's message on the second one, and hand the first one to the interpreter that installed the patch (registered on construction), keeping Robot Framework's original `__call__` and `_stop_execution_gracefully` for `robot-debug` runs; verify with unit tests that SIGINT still raises `ExecutionInterrupted` while a keyword runs, that SIGTERM requests the termination, and that a second SIGTERM forces the end (with `os._exit` patched in the test).
- [ ] 2.2 End a console session on SIGTERM (`console_interpreter.py`, `prompt_toolkit_interpreter.py`): set `exit_code = 253` and a termination flag, raise `EOFError` out of a waiting read, don't run an unfinished block, and end after an interrupted keyword; verify with subprocess tests in `tests/robotcode/repl/`, skipped on Windows, that a piped `repl -o output.xml` waiting for input exits with 253 and writes the session test, that SIGTERM during `Sleep    30` exits with 253 within seconds, that an unfinished `FOR` loop doesn't run, that two SIGTERMs end the process with 253 at once, and with a prompt_toolkit pipe-input test that the prompt ends with `EOFError`.
- [ ] 2.3 End a repl-server session on SIGTERM through `shutdown()` and exit with 253; verify with a subprocess test, skipped on Windows, that `repl-server` waiting for a client with stdin kept open exits with 253 within seconds.
- [ ] 2.4 Add SIGTERM to the "Exit code and session status" section of `docs/src/content/docs/guides/repl.md` (the session ends with 253, a second SIGTERM forces it; SIGINT interrupts a running keyword); verify with `npm run docs:build`.

## 3. SIGTERM in robot-debug

- [ ] 3.1 At a `robot-debug` stop, detach the controller and raise `EOFError` out of the stop's read on SIGTERM, so Robot Framework ends the run gracefully; verify with subprocess tests, skipped on Windows, that SIGTERM at the entry stop of the first of two tests fails that test with `Execution terminated by signal`, doesn't execute the second and writes `output.xml`, and that SIGTERM during `Sleep    30` without a stop fails the test and ends the run.
- [ ] 3.2 Describe SIGTERM in `docs/src/content/docs/guides/robot-debug.md` (ends the run like Robot Framework, also at a stop; a second SIGTERM forces the end); verify with `npm run docs:build`.

## 4. Integration

- [ ] 4.1 Run `hatch run lint:all` and `hatch run test:test`, and verify both pass on the full Robot Framework matrix.

## Workflow follow-up

- Archive the change after review.
