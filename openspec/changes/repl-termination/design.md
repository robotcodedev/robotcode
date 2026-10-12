# Design

## Context

- **repl-server shutdown.** `repl_server` runs the JSON-RPC server in a daemon thread and then `run_repl`. Its `finally` calls `server.loop.stop()` and `server_task.result(5)`. Only `JsonRPCServer.close()` sets the stop event of the stdio reader (`start_stdio`), so the reader never stops: at EOF it waits in 10 ms steps, on a pipe that stays open it blocks in `peek(1)`. The reader runs in a `ThreadPoolExecutor` worker; those aren't daemon threads, and Python joins them at exit. So `server_task.result(5)` raises `TimeoutError`, which replaces the session's `ClickException` (for example an invalid `robot.toml`), and the process doesn't end.
- **Signals.** Robot Framework's `_StopSignalMonitor` handles SIGINT and SIGTERM while `TestSuite.run` runs (and around every REPL statement). It counts signals, stops a run gracefully with `ExecutionFailed("Execution terminated by signal", exit=True)` while a keyword runs or at the next keyword start (`start_running_keyword`), and raises `SystemExit` on the second signal. The REPL replaces `__call__` (act only while a keyword runs, no counting) and `_stop_execution_gracefully` (raise the REPL's `ExecutionInterrupted`, which `BaseInterpreter.run` records as a failure before it reads the next input). That suits Ctrl-C, but it also applies to SIGTERM, and because the patch is global it applies to `robot-debug` runs as well.
- **Where sessions wait.** `ConsoleInterpreter.read_line` calls `input()`; the prompt_toolkit backend runs `PromptSession.prompt()`; the repl-server's `Interpreter.run_input` waits in `has_input.wait()` and already has `shutdown()`, which ends the session with `EOFError`. At a `robot-debug` stop, `wait_at_stop` reads with `read_line` and resumes the run on `EOFError`. Robot Framework's `suite.run()` swallows exceptions raised from a logger callback, so a stop can't end the run by raising.
- **Exit codes.** `.exit CODE` sets `interpreter.exit_code`, which `_session_exit_code` puts before the status-based code. `repl_server` doesn't exit with a session code.
- **Windows.** SIGTERM isn't a catchable signal there; `os.kill(pid, SIGTERM)` ends the process at once.

## Goals / Non-Goals

**Goals:**
- `repl-server` reports a session error through Click (exit 252 for its own errors) and the process ends.
- SIGTERM ends `repl`, `repl-server` and `robot-debug` as the specs describe, while SIGINT keeps working as it does today.

**Non-Goals:**
- Changing SIGINT. Ctrl-C still interrupts a running keyword and the session goes on.
- Windows: the requirements apply where SIGTERM is a signal; the signal tests are skipped on Windows.
- Other users of the stdio reader (language server, debug launcher) beyond the daemon thread below.

## Decisions

### The stdio reader runs in a daemon thread and reads the file descriptor

`JsonRPCServer.start_stdio` reads stdin in a daemon thread instead of a `ThreadPoolExecutor` worker, so a read that blocks on an open pipe can't keep the process alive once everything else has ended. The thread reads the file descriptor (`os.read`) instead of the buffered `peek`/`read1`: a read that blocks inside the buffered reader holds its lock, and at shutdown the interpreter needs that lock and aborts with `Fatal Python error: _enter_buffered_busy` (seen with the first version of this change).

Alternative: ending the repl-server process with `os._exit` when the server thread doesn't stop in time. A config error has to go through Click first to print its message and exit code, so the fast exit would have to print it itself; and the language server and the debug launcher would keep the same problem.

### repl-server closes its server and doesn't hide the session's error

In its `finally`, `repl_server` schedules `server.close()` on the server's loop instead of calling `server.loop.stop()`; that sets the reader's stop event and closes a TCP server. Called from the main thread, `close()` would wait for the TCP server's `wait_closed()`, which from Python 3.12 on waits until every client has disconnected. It then waits up to one second for the server thread with `concurrent.futures.wait`, which doesn't raise, so the session's own exception propagates: an invalid `robot.toml` reaches the root group as a `ClickException` and exits with 252. After the session, `repl_server` exits with the interpreter's exit code when one is set, as `repl` does.

Alternative: catching `TimeoutError` around `server_task.result(5)`. It hides the symptom but leaves the reader running.

### The patched monitor tells SIGTERM apart from SIGINT

The patch keeps Robot Framework's original `__call__` and `_stop_execution_gracefully`. SIGINT takes today's REPL path. For SIGTERM the patched `__call__` counts on its own (Robot Framework resets its count after every REPL statement):

- On the second SIGTERM it writes Robot Framework's `Execution forcefully stopped.` to stderr and ends the process with `os._exit(253)`, because `BaseInterpreter.run` catches `SystemExit` and would only end the session gracefully.
- On the first SIGTERM it hands over to the interpreter that installed the patch (the interpreter registers itself on construction). A REPL session ends itself (next decision). A `robot-debug` run gets Robot Framework's own handling: the original `__call__` runs, and while a SIGTERM is pending the patched `_stop_execution_gracefully` raises Robot Framework's `ExecutionFailed(exit=True)` instead of `ExecutionInterrupted`.

Alternative: not patching at all for SIGTERM, so Robot Framework handles it everywhere. Robot Framework only stops at the next keyword start, so an idle REPL session would still not end.

### A REPL session ends itself on SIGTERM

The interpreter sets `exit_code = 253` and a termination flag.

- While it waits for input, the read ends with `EOFError`. The signal handler raises it out of `input()`. The prompt_toolkit prompt ends through its event loop (`Application.exit(exception=EOFError())`, scheduled with `call_soon_threadsafe`): the handler can run inside one of the loop's callbacks, such as its terminal size poll, where asyncio only reports a raised error and the prompt would go on. For the repl-server, the handler raises it out of `has_input.wait()`; `shutdown()` would set the event, which takes a lock that the main thread, interrupted by the signal, may hold.
- While a keyword runs, the keyword is interrupted as today (`ExecutionInterrupted`), and the next read ends the session. An attached debugger is detached first, so the interrupted keyword doesn't stop at an exception break.
- Between two keywords of a statement, such as in a `FOR` loop, the signal is counted in Robot Framework's monitor, so the next keyword that starts stops the statement, as in a `robot` run; the monitor resets the count when the statement ends. A statement that hasn't started yet doesn't run.
- With the flag set, `get_input` doesn't run an unfinished block on `EOFError` (it does today when the input ends inside one).

The session then ends as at the end of the input: Robot Framework finishes the session test and writes the output files, and the exit code is 253.

### A robot-debug stop resumes with the debugger detached

At a stop, the interpreter detaches the controller, so no breakpoint or step pauses again, and raises `EOFError` out of the stop's read, which `wait_at_stop` treats as continue. Robot Framework's pending signal then ends the run gracefully at the next keyword start, as in a plain `robot` run. The controller is detached after Robot Framework's handler also when that handler raises because a keyword runs, so the interrupted keyword doesn't stop at an exception break.

Alternative: raising a stop exception at the stop. Robot Framework swallows exceptions from logger callbacks, so it wouldn't end the run.

## Risks / Trade-offs

- [Ending the prompt_toolkit prompt from a signal handler] → The prompt ends through `Application.exit`, so prompt_toolkit's own cleanup restores the terminal. Tests with prompt_toolkit's pipe input send a real SIGTERM while the prompt waits and inside one of its loop's callbacks, and check that the prompt ends with `EOFError`.
- [A daemon reader thread in the shared JSON-RPC server] → For the language server and the debug launcher it only changes that a blocked stdin read no longer keeps the process alive at exit.
- [SIGTERM between two statements] → Neither reading nor running, the flag ends the session at the next read. The read checks the flag after it marks itself as reading, so a signal in between isn't missed.
- [`os._exit` on the second signal skips cleanup] → That is the point of forcing; Robot Framework's `SystemExit` skips its remaining work too.
- [Robot Framework's private monitor state] → The patch already replaces two private methods and reads `_running_keyword`; it now also raises `_signal_count`, which `start_running_keyword` checks in Robot Framework 5.0 through 7.5. The unit tests run against the real monitor on every supported version.
