# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach, checked against the code on main and LSP4IJ 0.21.0 (bytecode):

- **The connection provider:** `lsp/RobotCodeLanguageServer` extends LSP4IJ's `OSProcessStreamConnectionProvider`. Its constructor already builds a command line through `buildRobotCodeCommandLine`, which runs the environment check. `start()` opens `ServerSocket(0)` on all interfaces, starts `robotcode language-server --socket <port>` and calls `accept()` without a timeout. `stop()` calls `super.stop()` and then `clientSocket!!.close()`, which throws when the server never connected (#630). `logError` sends every stderr line to `Logger.error`. `getInputStream()` returns the socket stream.
- **How LSP4IJ drives the provider:** it creates a new provider for every start, asks it for `getInitializationOptions` and then calls `start()` on a pooled thread. It registers its own stderr handler, which writes each line into the server's log in the Language Servers tool window with message type Error. It copies stdout into a `PipedInputStream` that only the provider's own `getInputStream()` would read, and RobotCode never reads it. A failed `start()` ends in a start error that LSP4IJ shows as a notification. On stop, LSP4IJ sends `shutdown`, queues the `exit` notification on its writer thread and then calls `provider.stop()`, on a common-pool thread unless the server is being disposed. The base `stop()` ends the process at once.
- **The server side of the socket:** in socket mode the server connects to `127.0.0.1` unless `--bind` is given (`language_server/cli.py`, `run_server`; `jsonrpc2/server.py`, `start_socket`).
- **The Python check:** `RobotCodeHelpers.checkPythonAndRobotVersion` runs `import sys; print(sys.version_info[:2]>=(3,8))` and then the bundled `check_robot_version.py`, inside `executeOnPooledThread { }.get()`, and caches the result in project user data. The texts live in the enum `CheckPythonAndRobotVersionResult`; the Python one says "Minimum required version is 3.9". A run that fails the check gets `InvalidPythonOrRobotVersionException` with the text "PythonSDK is not defined or robot version is not valid for project …". Every package declares `requires-python >=3.10`. VS Code uses the same 3.8 probe (`vscode-client/extension/pythonmanger.ts:61`); its picker title is "Invalid python version for workspace folder '…'" (`languageclientsmanger.ts:464`), while the detail of "Select Python Interpreter..." already names 3.10.
- **The actions:** Restart calls `restartAll(debounced = false)` without a reset, on the EDT, so a cached failed result stays. Clear Cache runs `runBlocking` on the EDT, waits for `getLanguageServer(...)` and casts `server?.server as RobotCodeServerApi`; with the server stopped this throws before the restart (runtime check Q24(c) in the analysis notes).
- **The restart manager:** `RobotCodeRestartManager` creates its own `CoroutineScope(Dispatchers.IO.limitedParallelism(1))`, never cancels it, and checks `project.isDisposed` only before it launches the debounced job.
- **Runtime evidence** (analysis notes, sections 4 and D): the listener shows up as `*:<port>` for the whole server lifetime; stderr lines become SEVERE reports blamed on RobotCode; LSP4IJ reports "SocketException: Socket closed" on every restart.

## Goals / Non-Goals

**Goals:**

- A start either connects or fails within a bounded time with a reason, and stop and restart never throw.
- No IDE error comes from what the server prints.
- One version rule and one wording for unusable interpreters, in both clients.
- The restart actions recover a stopped server without blocking the EDT.

**Non-Goals:**

- Moving the environment check into a background state with separate results, timeouts and re-checks on interpreter changes. This change keeps the existing check and its cache.
- Other transports (stdio, pipes) and remote interpreters.
- Changing when the plugin restarts on its own (configuration files, settings).
- The small plugin.xml cleanups found in the analysis (`org.toml.lang` dependency, dead registrations, the missing `RobotIcons.Robot` file). They ship as separate fixes.

## Decisions

### Keep the socket, bound to 127.0.0.1, and close the listener after the connect

The listener is a `ServerSocket` with backlog 1 bound to `127.0.0.1`, the address the server connects to. It is closed as soon as the server has connected, so no port stays open while the server runs.

Alternatives:
- `InetAddress.getLoopbackAddress()` returns `::1` when the JVM prefers IPv6 addresses, while the server connects to `127.0.0.1`.
- stdio through LSP4IJ's default streams would need the server to keep library output off stdout, because the stdio mode writes the protocol to the process's stdout (`jsonrpc2/server.py`, `start_stdio`). That is a server change, and it only pays off for remote interpreters.

### A connect step with a liveness check and a 60-second limit

`start()` builds the command line, starts the process and then waits for the connection in a loop: `accept()` with a short socket timeout, and between tries a check whether the process is still alive. When it is gone, the start fails with a `CannotStartProcessException` that names the exit code. After 60 seconds without a connection, the process is ended and the start fails with a message that the server did not connect in time. The loop is a small function with the liveness check, the exit code and the limit passed in, so that unit tests cover it without a real server.

The constructor no longer builds a command line, so creating a provider no longer runs the environment check. LSP4IJ calls `start()` on a pooled thread, so the wait never runs on the EDT.

60 seconds is far above the measured start times (about 0.7 to 1.7 seconds in the analysis), and a process that dies ends the wait at once.

Alternatives:
- No limit, as today: a server that hangs before it connects blocks the start forever.
- Relying on LSP4IJ's `ensureIsAlive()`: it runs only after `start()` has returned, so it cannot end a blocked `accept()`.

### Stop waits for the server, then closes and ends

`stop()` first waits up to two seconds for the process to end on its own, which it does after the `exit` notification. Then it closes the client socket and the listener, if they exist, and calls the base `stop()`, which ends a process that is still running. Every step is null-safe, and a second call does nothing. LSP4IJ calls `stop()` on a common-pool thread on a stop or restart, so the wait does not block the EDT. When the project closes, LSP4IJ calls `stop()` on the EDT without sending `exit` (seen in the harness check: the wait froze the EDT for the full two seconds), so on the EDT `stop()` does not wait and ends the process at once, as before.

The null-safe stop (#630) may land earlier as a plain fix. This change then builds the wait and the closing order on top of it.

Because the process now ends before the base `stop()` marks the provider as stopped, LSP4IJ would take that end for an unexpected stop and record "The server was stopped unexpectedly." for a normal restart. The same message would replace the exit code of a server that ends before it connects. The provider therefore wraps the handlers that LSP4IJ registers through `addUnexpectedServerStopHandler` and runs them only after the server has connected and before its own `stop()` has begun (found in the harness check).

Alternative: closing the sockets before the process has ended, as today, makes LSP4IJ's queued `exit` write fail with "Socket closed".

### No new start after a failed start

LSP4IJ starts the server on demand, for every feature request of an open editor, and it consults the factory's `isEnabled` before it does. After a failed start, pending requests triggered bursts of new starts in the harness check, up to six processes at once, and each failed start makes LSP4IJ's feature collectors, such as document links, log SEVERE errors that the IDE blames on LSP4IJ. Before this change, such a start never ended, so neither happened. (Decided by the maintainer on 2026-10-08.)

So the provider reports every failed start to the language server manager, and the factory's `isEnabled` returns `false` while the failure is reported. Every start through the manager clears it first; all restart paths go through it: Restart, Clear Cache and Restart, changes to `robot.toml`, Apply on a settings page, the startup activity and SDK changes. The errors of the first failed start remain, because LSP4IJ logs them before the plugin can react.

Alternative: leaving the on-demand starts as they are, as a limitation of LSP4IJ; a broken environment then spawns new processes and errors whenever an editor needs the server.

### Server output goes only to LSP4IJ's log

The provider no longer registers its own stderr handler, because LSP4IJ already writes stderr into the server's log. For stdout, the provider reads the pipe that LSP4IJ fills on a pooled thread until it ends, and passes each line to the log handlers that LSP4IJ registered on the provider. It keeps references to them by overriding `addLogErrorHandler`. So stdout shows up next to stderr, as it does in VS Code's language server output channel, and it can no longer fill the pipe.

Alternatives:
- Discarding stdout loses output that VS Code shows.
- Writing stdout to idea.log hides it from users.

### Python 3.10 and one wording, in both clients

The IntelliJ probe becomes `import sys; print(sys.version_info[:2] >= (3, 10))`. The texts move from the enum into `messages/RobotCode.properties`, and each names "Python 3.10 or newer with Robot Framework 5.0 or newer":
- no interpreter;
- an interpreter path that does not exist;
- a Python older than 3.10;
- Robot Framework missing or older than 5.0.

The results stay as they are; telling a missing Robot Framework from an old one, and naming the detected versions, needs a richer probe and is not part of this change. A run that fails the check gets the text of the result instead of the generic one.

In VS Code, `_pythonVersionScript` gets the same `>= (3, 10)` comparison, and the picker title for that case says that Python 3.10 or newer is required. The rest of the picker stays.

### Restart and Clear Cache run in the background

- **Restart** calls `restartAll(reset = true)` on the debounced path. The check, the server restart and the discovery then run on the restart manager's coroutine scope, the same path that changes to robot.toml use.
- **Clear Cache and Restart** launches a coroutine on the language server manager's injected scope and wraps it in `withBackgroundProgress`. If LSP4IJ reports the server as started, it sends `robot/cache/clear` and waits for the answer with a time limit. A failure or a timeout is logged as a warning. Then it calls `restartAll(reset = true)`. It checks the status first because `getLanguageServer` would start a stopped server and wait for its initialization.
- Both actions get `update()` with `ActionUpdateThread.BGT` and are enabled only when the event has a project.

Alternatives:
- `Task.Backgroundable` is marked `@ApiStatus.Obsolete` in 2026.1; `withBackgroundProgress` carries no status annotation and fits the coroutine scope.
- Calling `restartAll(reset = true, debounced = false)` from `actionPerformed` runs the check on the EDT, which blocks it for up to two probe timeouts of 5 seconds each.

### The restart manager uses the service scope

`RobotCodeRestartManager` takes the `CoroutineScope` that the platform injects into project services as a constructor parameter. The platform cancels that scope when the project closes or the plugin is unloaded. The debounced job runs on a dispatcher limited to one thread, so restarts stay in order, and it checks `project.isDisposed` again after the delay.

## Risks / Trade-offs

- [A very slow machine needs more than 60 seconds before the server connects] → The start error says that the server did not connect in time, so the cause is visible. The limit is about 35 times the measured start time.
- [stdout lines appear as error-level entries in LSP4IJ's log, like stderr lines today] → They appear where users look for server output, and they raise no IDE error.
- [Users whose interpreter is Python 3.8 or 3.9 lose RobotCode at once] → It could not run there before, because every package requires Python 3.10. The message names the fix, and the release notes mention it.
- [LSP4IJ's feature collectors, such as document links, log a SEVERE error for every failed start, which the IDE blames on LSP4IJ] → After a failed start, the plugin does not start the server on its own any more, so the errors come only from starts the user asked for.
- [The VS Code change has no automated test] → The probe string is checked against Python 3.9 and 3.10 interpreters in the tasks, and lint and compile cover the rest.
- [#630 lands earlier as a plain fix] → `stop()` is then rebased onto it; the fix and this change touch the same method.

## Migration Plan

None. Nothing is stored, and no setting changes.
