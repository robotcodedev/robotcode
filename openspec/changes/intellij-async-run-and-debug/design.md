# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- **Runners:** both runners are `AsyncProgramRunner`s but return an already resolved promise: they call the state synchronously on the EDT. The Debug runner calls `state.execute()` inside `XDebugProcessStarter.start`, so the process is created on the EDT. `buildRobotCodeCommandLine` may run the environment check there as well, two subprocesses with five-second timeouts, when no verdict is cached.
- **The handshake** runs in `RobotCodeRunProfileState.startNotified` inside `runBlocking(Dispatchers.IO)`. In 2026.1 `startNotify` is called on the EDT for Run and Debug (javap, and seen at runtime in Q71). A normal start blocked the EDT for about 0.55 s; a debuggee killed before it listened blocked it for 9.99 s ("UI was frozen for 10020ms"), and two SEVERE entries followed: the `CantRunException` thrown from the listener, and an `UninitializedPropertyAccessException` because `processTerminated` reads the `lateinit` socket (Q54).
- **Debugger callbacks:** the plugin has 18 `runBlocking` call sites, 14 of them in `debugging/`. The platform calls `resume`, the step methods, `startPausing`, `runToPosition` and `XDebuggerEvaluator.evaluate` on the EDT, and the breakpoint handlers inside an EDT write action; `computeChildren` comes from a background coroutine (javap, from the analysis). Measured in Q42: evaluating `Sleep    5s` froze the IDE for 5 s; a Debug start to a breakpoint 589 ms; Step Over 158 ms; enabling a breakpoint 34 ms. No wait has a timeout.
- **Evaluation:** `RobotCodeDebuggerEvaluator` sends no `context`, so the debugger treats every evaluation as REPL input, and it lets `ResponseErrorException` escape (SEVERE plus "IDE error occurred"). In Q49 the watch `Log    watch-side-effect` ran twice at every stop. The debugger (`debugger.py`) evaluates `watch` and `hover` as expressions, returns `<undefined>` for unknown variables there, and runs keywords only for `repl`. Its error responses carry the type as the message and a readable text in the body's `error.format`, for example "ExecutionFailed: No keyword with name '1 + 2' found." (`protocol.py`).
- **The debugger's own limits:** it waits up to 60 s for a keyword evaluated from the debugger (`KEYWORD_EVALUATION_TIMEOUT`) and answers nothing else meanwhile, because the wait blocks its event loop. It waits 15 s for a client to connect (`--wait-for-client-timeout`) and 15 s for the configuration (`cli.py`).
- **The evaluation origin:** the platform passes the origin of an evaluation only through internal API: the callback implements `XEvaluationCallbackWithOrigin` with `getOrigin()`, returning an `XEvaluationOrigin` with the values `INLINE`, `DIALOG`, `WATCH`, `INLINE_WATCH`, `BREAKPOINT_CONDITION`, `BREAKPOINT_LOG`, `RENDERER`, `EDITOR`, `UNSPECIFIED` and `UNSPECIFIED_WATCH`. Both are `@ApiStatus.Internal` in 2026.1 (javap). LSP4IJ 0.21.0's DAP evaluator reads the origin by reflection (from the analysis).
- **Builds on planned changes, not implemented yet:** `intellij-debugger-breakpoints` orders the handshake (`initialize`, `initialized`, configuration requests, `attach`, `configurationDone`) inside the blocking code and adds a bookkeeping class for breakpoints; this change moves that phase into the background without reordering it. `intellij-run-stop` adds the process handler whose destroy path asks the debugger to end the run; this change does not touch it. `intellij-run-configuration-target` moves the run state onto PyCharm's `PythonCommandLineState` and, because the target API must not run on the EDT, also lets both runners call `state.execute()` on a background thread and build the debug session on the EDT with a starter that wraps the existing execution result. Where one of them has not landed yet, this change works on today's code in the same way.

## Goals / Non-Goals

**Goals:**

- No wait for the process or the debugger on the EDT, and none without a bound.
- The order of DAP requests that change the run's state is the order of the user's actions.
- A run that fails to connect ends cleanly, with a message in its console.

**Non-Goals:**

- Settings for the connect and request timeouts.
- The event converter's own five-second wait for the first output; after this change it blocks a background thread, not the EDT, and the converter is reworked separately.
- The language server's blocking "Clear Cache" call.

## Decisions

### Start the process in the background, show it on the EDT

Both runners resolve their promise later. They run `state.execute()`, which starts the process and creates the console, on a pooled thread; the console creation keeps its existing `invokeAndWait`. Then, on the EDT, the Run runner shows the content and the Debug runner starts the session through `XDebuggerManager.newSessionBuilder(...)` with a starter that wraps the execution result that already exists. Errors reject the promise, so the platform shows its "Error running" notification, as it does today for a missing interpreter. The process cannot lose output in between: the handler starts reading only on `startNotify`, and the debugger waits up to 15 s for its client.

`newSessionBuilder` stays, although it is `@ApiStatus.Experimental` in 2026.1, because it is the only way to start a session there that is not deprecated, and `intellij-debugging` forbids deprecated debugger API.

`intellij-run-configuration-target` plans the same start for its own reason. Whichever of the two changes lands first makes it; the second one finds the runners done and keeps them.

Alternative: keep starting the process inside the starter on the EDT. Process creation itself is fast, but the environment check behind `buildRobotCodeCommandLine` can block for seconds.

### One coroutine scope per run, bound to the process handler

The state creates a coroutine scope for each run (a supervisor job on `Dispatchers.IO`) and cancels it when the process terminates or is detached. `startNotified` launches the handshake in that scope and returns at once, for Run and Debug. The connect loop waits up to 15 s, the debugger's default `--wait-for-client-timeout`. If the process is still running after that, the handshake writes a message to the console and destroys the process; if the process ends first, the cancelled scope ends the handshake quietly, and the console shows the exit code. No exception leaves a process listener, and the connection is a nullable reference, so `processTerminated` cannot fail.

The debug process uses the same scope. Its signal subscriptions end with the scope instead of living for `Lifetime.Eternal`, so no handler runs for a session that has ended.

### Every callback returns at once and completes later

- `resume`, the step methods, `startPausing`, `runToPosition`, `stop` and the breakpoint handlers queue their work and return. Requests that change the run's state and all breakpoint bookkeeping run on one single-threaded dispatcher of the session, so their order is the order of the user's actions, and the EDT write action of a breakpoint change no longer waits for the debugger.
- `computeChildren` of frames, groups and values, and `evaluate`, run as coroutines in the scope and complete through the platform's callbacks: `addChildren`, `setErrorMessage`, `evaluated`, `errorOccurred`. A node that has become obsolete in the meantime is not completed. Reads run in parallel with each other.
- Every DAP request has a timeout of 90 s. The debugger answers a keyword evaluation after at most 60 s and answers nothing else meanwhile, so the timeout never fires while the debugger works normally, and an unresponsive debugger is noticed. A request that times out completes its callback with an error message.

Alternative: shorter timeouts for requests other than `evaluate`. They would fire for a variables request issued while a keyword evaluation blocks the debugger's event loop.

### The evaluation context comes from the origin, read by guarded reflection

The evaluator asks the callback for a method `getOrigin()` by reflection and maps the name of the returned value: `WATCH`, `INLINE_WATCH` and `UNSPECIFIED_WATCH` to `watch`, `EDITOR` to `hover`, and everything else, including a missing method or a failed call, to `repl`, which keeps today's behaviour of the Evaluate dialog and the inline field. There is no compile-time reference to the internal classes, so `verifyPlugin` reports no internal API use. A JUnit test checks that the platform still has `XEvaluationCallbackWithOrigin.getOrigin()` and the expected value names, so a platform update that changes them fails the build instead of silently turning watches back into keyword calls.

Error responses go to `errorOccurred` with the text of the body's `error.format`, or with the response message when there is no body.

Alternatives:

- Compile against `XEvaluationOrigin`: `verifyPlugin` would report internal API use.
- Guess from the expression text, for example "a single variable means expression mode": it cannot tell a watch from a dialog evaluation of the same text.
- Keep sending no context: watches keep running keywords.

## Risks / Trade-offs

- [The internal origin API changes] → The reflection is guarded and falls back to `repl`, today's behaviour, and the JUnit guard test fails on the next platform update.
- [`XDebugSessionBuilder` is experimental in 2026.1] → It is the only non-deprecated path; `verifyPlugin` runs against every configured IDE version.
- [Answers arrive after a session has ended] → The scope is cancelled when the process ends, and obsolete nodes are not completed.
- [A long keyword evaluation blocks the debugger's event loop, so the Variables view waits] → Its nodes show "Collecting data…" until the debugger answers; the IDE stays usable.
- [Errors from a start in the background no longer surface where they did] → They reject the runner's promise, which the platform reports as "Error running", as before; harness check Q18 confirms it.

## Migration Plan

None.
