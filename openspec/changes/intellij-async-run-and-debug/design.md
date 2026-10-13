# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- **Runners** (since `intellij-run-configuration-target`): both runners start the process in the background. `startInBackground` runs `state.execute()` on a pooled thread and shows the result on the EDT, where the Debug runner starts the session through `XDebuggerManager.newSessionBuilder(...)` with a starter that wraps the execution result; errors reject the runner's promise, which the platform reports as "Error running".
- **The handshake** runs in `RobotCodeRunProfileState.startNotified` inside `runBlocking(Dispatchers.IO)`. It connects to the port of the run (`DEBUG_PORT`, chosen per run since `intellij-run-stop`) for up to 10 s, retrying every 100 ms, throws a `CantRunException` from the listener when that fails, and keeps the socket in a `lateinit` property that `processTerminated` reads. In 2026.1 `startNotify` is called on the EDT for Run and Debug (javap, and seen at runtime in Q71). A normal start blocked the EDT for about 0.55 s; a debuggee killed before it listened blocked it for 9.99 s ("UI was frozen for 10020ms"), and two SEVERE entries followed: the `CantRunException` thrown from the listener, and an `UninitializedPropertyAccessException` because `processTerminated` reads the `lateinit` socket (Q54). The run state's subscription to the debugger's `terminated` event lives for good (`adviseEternal`).
- **Stop** (since `intellij-run-stop`): `requestTerminate()` sends `terminate` through `connectedServer`, which the handshake sets; without a connection, the process handler ends the process with a signal. `RobotCodeDebugProcess.stop()` already asks on a pooled thread.
- **Debugger callbacks:** the plugin has 17 `runBlocking` call sites, 16 of them in `debugging/` and one in `startNotified`. In `RobotCodeDebugProcess` they are `resume`, the three step methods, `startPausing`, `runToPosition`, and the bookkeeping of line and exception breakpoints (`registerBreakpoint`, `unregisterBreakpoint`, `breakpointPropertiesChanged` for conditions, log messages and hit counts, `registerExceptionBreakpoint`, `unregisterExceptionBreakpoint`); the bookkeeping (`lineBreakpoints`, `exceptionBreakpoints`, `configured`) is guarded by `breakpointsMutex` since `intellij-debugger-breakpoints`, which the stop handler takes as well. The others are `computeChildren` of frames and groups, the children of a value and the next page of a long list in `RobotCodeNamedValue` (since `intellij-debugger-variables`), Set Value through its `XValueModifier`, and the evaluator. The platform calls `resume`, the step methods, `startPausing`, `runToPosition`, `XDebuggerEvaluator.evaluate` and `XValueModifier.setValue` on the EDT, and the breakpoint handlers inside an EDT write action; `computeChildren` comes from a background coroutine (javap, from the analysis). Measured in Q42: evaluating `Sleep    5s` froze the IDE for 5 s; a Debug start to a breakpoint 589 ms; Step Over 158 ms; enabling a breakpoint 34 ms. No wait has a timeout. The debug process subscribes to `stopped` and `continued` for `Lifetime.Eternal`.
- **Evaluation:** `RobotCodeDebuggerEvaluator` sends no `context`, so the debugger treats every evaluation as REPL input, and it lets `ResponseErrorException` escape (SEVERE plus "IDE error occurred"). In Q49 the watch `Log    watch-side-effect` ran twice at every stop. The debugger (`debugger.py`) evaluates `watch` and `hover` as expressions, where it runs a keyword only for an expression that starts with `! ` and returns `<undefined>` for unknown variables; any other input runs as a keyword only for `repl`. VS Code sends `watch` for its watches. Its error responses carry the type as the message and a readable text in the body's `error.format`, for example "ExecutionFailed: No keyword with name '1 + 2' found." (`protocol.py`); `messageOf(ResponseError)` in `RobotCodeNamedValue.kt` reads that text. The Robot Debug Console already sends `repl` and completes without blocking, and the log text of a suspending breakpoint is evaluated as `watch` (since `intellij-debugger-expressions` and `intellij-debugger-breakpoints`).
- **The debugger's own limits:** it waits up to 60 s for a keyword evaluated from the debugger (`KEYWORD_EVALUATION_TIMEOUT`) and answers nothing else meanwhile, because the wait blocks its event loop. It waits 15 s for a client to connect (`--wait-for-client-timeout`) and 15 s for the configuration (`--configuration-done-timeout`, `cli.py`).
- **The evaluation origin:** the platform passes the origin of an evaluation only through internal API: the callback implements `XEvaluationCallbackWithOrigin` with `getOrigin()`, returning an `XEvaluationOrigin` with the values `INLINE`, `DIALOG`, `WATCH`, `INLINE_WATCH`, `BREAKPOINT_CONDITION`, `BREAKPOINT_LOG`, `RENDERER`, `EDITOR`, `UNSPECIFIED` and `UNSPECIFIED_WATCH`. Both are `@ApiStatus.Internal` in 2026.1 (javap). LSP4IJ 0.21.0's DAP evaluator reads the origin by reflection (from the analysis).

## Goals / Non-Goals

**Goals:**

- No wait for the debugger on the EDT, and none without a bound.
- The order of DAP requests that change the run's state is the order of the user's actions.
- A run that fails to connect ends cleanly, with a message in its console.

**Non-Goals:**

- Settings for the connect and request timeouts.

## Decisions

### One coroutine scope per run, bound to the process handler

The state creates a coroutine scope for each run (a supervisor job on `Dispatchers.IO`) and cancels it when the process terminates or is detached. `startNotified` launches the handshake in that scope and returns at once, for Run and Debug. The connect loop waits up to 15 s, the debugger's default `--wait-for-client-timeout`, instead of today's 10 s. If the process is still running after that, the handshake writes a message to the console and destroys the process; if the process ends first, the cancelled scope ends the handshake quietly, and the console shows the exit code. No exception leaves a process listener, and the socket is a nullable reference, so `processTerminated` cannot fail. `connectedServer` is set once the connection stands, so a Stop while the handshake still connects finds no connection and ends the process with a signal, as `intellij-run-stop` specifies.

The debug process uses the same scope. Its subscriptions to `stopped` and `continued`, and the run state's subscription to `terminated`, end with the scope instead of living for good, so no handler runs for a session that has ended.

### Every callback returns at once and completes later

- `resume`, the step methods, `startPausing`, `runToPosition` and the breakpoint bookkeeping (line and exception breakpoints, and changes of a breakpoint's properties) queue their work and return. Requests that change the run's state and all breakpoint bookkeeping run on one single-threaded dispatcher of the session, so their order is the order of the user's actions, and the EDT write action of a breakpoint change no longer waits for the debugger. The bookkeeping keeps `breakpointsMutex`, which the stop handler takes too.
- `computeChildren` of frames, groups and values, the next page of a long list, Set Value and `evaluate` run as coroutines in the scope and complete through the platform's callbacks: `addChildren`, `setErrorMessage`, `valueModified`, `evaluated`, `errorOccurred`. A node that has become obsolete in the meantime is not completed. Reads run in parallel with each other.
- Every DAP request has a timeout of 90 s. The debugger answers a keyword evaluation after at most 60 s and answers nothing else meanwhile, so the timeout never fires while the debugger works normally, and an unresponsive debugger is noticed. A request that times out completes its callback with an error message.

Alternative: shorter timeouts for requests other than `evaluate`. They would fire for a variables request issued while a keyword evaluation blocks the debugger's event loop.

### The evaluation context comes from the origin, read by guarded reflection

The evaluator asks the callback for a method `getOrigin()` by reflection and maps the name of the returned value: `WATCH`, `INLINE_WATCH` and `UNSPECIFIED_WATCH` to `watch`, `EDITOR` to `hover`, and everything else, including a missing method or a failed call, to `repl`, which keeps today's behaviour of the Evaluate dialog and the inline field. There is no compile-time reference to the internal classes, so `verifyPlugin` reports no internal API use. A JUnit test checks that the platform still has `XEvaluationCallbackWithOrigin.getOrigin()` and the expected value names, so a platform update that changes them fails the build instead of silently turning watches back into REPL input.

Error responses go to `errorOccurred` with the text that `messageOf` reads: the body's `error.format`, or the response message when there is no body.

Alternatives:

- Compile against `XEvaluationOrigin`: `verifyPlugin` would report internal API use.
- Guess from the expression text, for example "a single variable means expression mode": it cannot tell a watch from a dialog evaluation of the same text.
- Keep sending no context: watches stay REPL input, which runs every keyword call again at every stop and fails for unknown variables.

## Risks / Trade-offs

- [The internal origin API changes] → The reflection is guarded and falls back to `repl`, today's behaviour, and the JUnit guard test fails on the next platform update.
- [Answers arrive after a session has ended] → The scope is cancelled when the process ends, and obsolete nodes are not completed.
- [A long keyword evaluation blocks the debugger's event loop, so the Variables view waits] → Its nodes show "Collecting data…" until the debugger answers; the IDE stays usable.

## Migration Plan

None.
