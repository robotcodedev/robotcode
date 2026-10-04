# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- **One handler for Run and Debug:** `RobotCodeRunProfileState.startProcess()` builds `robotcode … debug [--no-debug] -bl …` for both runners and wraps it in a `KillableColoredProcessHandler`. The Run runner shows that handler in a run tab, the Debug runner wraps it in an XDebugSession.
- **The port:** `NetUtils.findFreePort(6612)` binds 6612 and closes it again, and falls back to an OS-assigned port only when 6612 is busy. Only then does the state add `--tcp <port>`, after the `-bl` items. The debugger binds the port later, after Python has started.
- **The DAP connection** is made in `startNotified`, which still blocks its thread for the whole handshake. The socket is a `lateinit` field that `processTerminated` reads unguarded.
- **What Stop does in 2026.1** (javap, from the analysis): the Stop action and `XDebugSessionImpl.stop()` call `ProcessHandler.destroyProcess()`, or `detachProcess()` when the handler detaches by default. `destroyProcess()` fires `processWillTerminate` and then calls `destroyProcessImpl()`, which ends in `KillableProcessHandler.doDestroyProcess()`. That method tries `destroyProcessGracefully()` (SIGINT to the process tree on Unix, WinP Ctrl+C on Windows) when `canDestroyProcessGracefully()` allows it, and kills the process otherwise. While a process is terminating, Stop turns into Kill, which calls `killProcess()` and kills the process tree directly. `XDebugProcess.stop()` runs only after the process has terminated.
- **Robot Framework's signal handling** (`robot/running/signalhandler.py`): the first signal prints "Second signal will force exit." and stops gracefully, with the running test failing as "Execution terminated by signal", teardowns run and outputs written. A second signal prints "Execution forcefully stopped." and exits. A paused run waits in `Debugger.wait_for_running()` for a client command, so a signal alone leaves it paused: in runtime check Q43 the process was still alive 35 s after Stop, and Kill ended it with exit code 137 and no outputs. In Run mode one Stop already ended a running test gracefully (Q62(b), Linux only).
- **The debugger's `terminate`** (`packages/debugger/src/robotcode/debugger/server.py`): the first request raises SIGINT inside the debugger process and continues a paused run, which sends a `continued` event. A second request, or one with `restart=true`, raises SIGTERM. A DAP probe confirmed that a terminate while paused ends the run with `output.xml`, `log.html` and `report.html` written.
- **The debug process:** `RobotCodeDebugProcess.stop()` sends `terminate` inside `runBlocking` and ignores errors. The protocol client ignores `continued` and `exited`; `terminated` closes the socket.
- **Planned, not implemented:** with decision D1, `intellij-run-configuration-target` turns the state into a `PythonCommandLineState` subclass. PyCharm then creates the handler in `createProcessHandler(Process, String, TargetEnvironment, TargetedCommandLine)`; its default for local runs, `PythonProcessHandler`, is a `KillableProcessHandler` as well. `intellij-async-run-and-debug` moves the handshake off the EDT.

## Goals / Non-Goals

**Goals:**

- One place decides how a Robot run is stopped, independent of where the handler is created.
- Stop adds no wait on the thread that calls it.

**Non-Goals:**

- Detach semantics for sessions attached to a run started elsewhere.
- A setting for the confirmation timeout.
- Non-local targets, where PyCharm creates its own handler.

## Decisions

### Stop goes through the debugger, in the handler's destroy path

A `KillableColoredProcessHandler` subclass overrides `doDestroyProcess()`. While the DAP connection is up, it hands the stop to the stop policy below and returns without sending a signal. Without a connection, it calls the inherited `doDestroyProcess()`, which is today's behaviour. `doDestroyProcess()` is overridden rather than `destroyProcessGracefully()`, because the inherited method skips `destroyProcessGracefully()` whenever `canDestroyProcessGracefully()` is false, for example on Windows without WinP, and kills the process right away. `killProcess()` stays untouched, so the second Stop still kills.

Alternatives:

- A `processWillTerminate` listener that sends `terminate`: the inherited destroy path still sends its own SIGINT right after the one the debugger raises, and Robot Framework treats that as the second signal and exits without outputs.
- An XDebugSession listener: it covers only Debug, and `sessionStopped` arrives after the process is gone.
- Keeping the signal and telling users to press Stop twice: the log and the report are lost.

### Fall back only when the debugger does not confirm

The stop policy sends `terminate` (restart `false`) from a pooled thread and waits for the response, not for the process to exit:

- no connection, or the request cannot be sent: the inherited destroy path runs at once;
- no response within five seconds: the inherited destroy path runs once;
- a response: nothing more happens. The run ends on its own, teardowns take as long as they need, and the platform's Kill stays available.

Five seconds is far above the normal round trip. The debugger answers `terminate` after raising the signal and resuming the run, so the answer comes within milliseconds unless its event loop is blocked, for example by a keyword evaluated from the debugger, which can hold it for up to 60 s (`KEYWORD_EVALUATION_TIMEOUT`).

The policy is a plain class with injected functions: send `terminate` (returns the response future, or nothing without a connection), the fallback, and a scheduler. JUnit tests drive it without a process. A second destroy request does not send a second `terminate`, which the debugger would answer with SIGTERM.

Alternatives:

- A timeout on the process exit, followed by the soft and the hard kill: it would force-kill long teardowns although Robot Framework is stopping as asked, and the second Stop already kills.
- Waiting for the response without a limit: a debugger with a blocked event loop would leave Stop without effect until the user kills the process.

### Where the handler is created, before and after the run configuration base changes

Today `RobotCodeRunProfileState.startProcess()` creates the handler from the command line and gives it a function that sends `terminate` over the state's connection when the connection is up. The function reads the connection through a nullable reference, not through the `lateinit` socket.

After `intellij-run-configuration-target` has landed, the state's override of `createProcessHandler(Process, String, TargetEnvironment, TargetedCommandLine)` returns the same handler class, built with its `(Process, String, Charset)` constructor. Both constructors this change uses are public and not deprecated in 2026.1; only `(GeneralCommandLine, Boolean)` is. Whichever of the two changes lands second makes the move: if this change lands first, the override in `intellij-run-configuration-target` returns this handler; if it lands second, this change adds the override instead of editing `startProcess()`. For non-local targets PyCharm keeps creating its own handler; they are out of scope.

### The session follows `continued`

The protocol client turns `continued` into a signal, and the debug process calls `XDebugSession.sessionResumed()`, which is public and unannotated in 2026.1. The debugger sends `continued` when a `terminate` resumes a paused run. Without it, the Debug tool window keeps showing the paused frames while Robot Framework runs its teardowns.

### `XDebugProcess.stop()` stays a fallback that never waits

`stop()` sends `terminate` only while the connection is still up, from a pooled thread and without waiting for the answer. The platform calls it only after the process has ended, so it rarely has anything to do; today it can block on a request that never gets an answer.

### An OS-assigned port for every run, always passed

The state binds port 0, reads the assigned port, closes the socket and passes `--tcp <port>` after `debug` and `--no-debug`, before the Robot Framework arguments. That keeps it a debugger option even when the Robot Framework arguments follow a `--`, the order the planned `intellij-run-configuration-target` uses as well. VS Code's launcher allocates its port the same way (`find_free_port` with port 0, `launcher/server.py`). The probing code in `NetUtils` goes.

Alternatives:

- Keep preferring 6612: two runs started at once race for it.
- Let the IDE listen and the debugger connect back: it needs work in the debugger, whose asynchronous start handles only TCP, and `--pipe-server` fails today.

## Risks / Trade-offs

- [The debugger answers after the five-second fallback, because its event loop was blocked, and then raises its own SIGINT, which Robot Framework takes as a second signal and exits without outputs] → It happens only when the debugger was blocked for more than five seconds; without a fallback, Stop would do nothing in that case.
- [Stop takes as long as the teardowns] → That is Robot Framework's graceful stop; the second Stop kills at once, and the release notes say so.
- [Windows and macOS are not covered by the harness] → The stop policy is unit-tested with fakes. The debugger raises SIGINT inside its own process, so the stop no longer depends on how the IDE delivers signals on these systems; this is not verified at runtime.
- [The handler overrides a protected method of a platform class] → `doDestroyProcess()` is unannotated in 2026.1, and `verifyPlugin` checks every configured IDE version.
- [Another process takes the port between allocation and the debugger's bind] → The OS hands out ephemeral ports in sequence, so this is unlikely; the run then fails to connect, as it would today.
- [Stop cannot be pressed while the handshake blocks the EDT] → Unchanged in this change; it ends when the handshake moves off the EDT.

## Migration Plan

None for users. When this change is archived, the Purpose of the `intellij-debugging` main spec, which speaks only of starting debug sessions, no longer covers Run sessions; it needs to be widened in the main spec, because a delta cannot change it.
