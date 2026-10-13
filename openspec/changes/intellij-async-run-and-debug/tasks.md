# Tasks

## 1. Session scope and requests

- [ ] 1.1 Give each run a coroutine scope (supervisor job on `Dispatchers.IO`) owned by `RobotCodeRunProfileState`, cancelled when the process terminates or is detached, plus a single-threaded dispatcher for state-changing requests and breakpoint bookkeeping, and a request helper with a 90 s timeout. Verify with JUnit tests: the scope is cancelled after the process handler (a `NopProcessHandler`) terminates; the helper completes with a timeout error for a future that never completes (with a short timeout injected); work queued on the dispatcher runs in submission order.

## 2. Handshake in the background

- [ ] 2.1 Launch the handshake from `startNotified` in the run's scope and return at once; keep the order of the configuration phase as it is; connect to the run's `DEBUG_PORT` for up to 15 s instead of 10 s; when the process is still alive after that, write a message to the console and destroy the process; when the process ends first, end quietly; replace the `lateinit` socket by a nullable reference so `processTerminated` cannot fail; set `connectedServer` once the connection stands; bind the subscription to the debugger's `terminated` event (`adviseEternal`) to the run's scope; fire `afterInitialize` from the handshake coroutine. Verify with JUnit tests against a fake DAP server and a fake process handler: a connect timeout writes the message and destroys the process without an exception escaping; terminating the process cancels a pending connect; a successful handshake sends its requests in the configured order.

## 3. Asynchronous debugger callbacks

- [ ] 3.1 In `RobotCodeDebugProcess`, let `resume`, the step methods, `startPausing`, `runToPosition`, `registerBreakpoint`, `unregisterBreakpoint`, `breakpointPropertiesChanged`, `registerExceptionBreakpoint` and `unregisterExceptionBreakpoint` queue their work on the session's dispatcher and return at once, keeping `breakpointsMutex` for the bookkeeping; bind the subscriptions to `stopped` and `continued` (`Lifetime.Eternal`) to the run's scope; remove every `runBlocking` from `debugging/` and from `startNotified`. Verify with `grep -rn runBlocking intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/debugging` (no hit) and harness check Q42(c, e) in task 5.2.
- [ ] 3.2 Let `computeChildren` of `RobotCodeStackFrame`, `RobotCodeNamedValue` and `RobotCodeValueGroup`, and the next page of a long list in `RobotCodeNamedValue`, complete through `addChildren` or `setErrorMessage` from a coroutine in the run's scope, and skip obsolete nodes; let Set Value send `setVariable` from a coroutine and complete with `valueModified`, or with `errorOccurred` and the text of `messageOf`. Verify with harness check Q42(b) and the Set Value and paging checks in task 5.2.

## 4. Evaluation

- [ ] 4.1 Make `RobotCodeDebuggerEvaluator` asynchronous: send the `context` mapped from the origin read by guarded reflection (`WATCH`, `INLINE_WATCH`, `UNSPECIFIED_WATCH` to `watch`; `EDITOR` to `hover`; everything else and every failure to `repl`), complete with `evaluated` or with `errorOccurred` and the text of `messageOf`. Verify with JUnit tests: the callback is completed from a background thread; the mapping for each origin name, for a callback without `getOrigin()` and for a throwing one; the error text with and without a body; a guard test that `XEvaluationCallbackWithOrigin.getOrigin()` and the expected `XEvaluationOrigin` value names exist in the platform.

## 5. Verification

- [ ] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass and report no new deprecated or internal API use.
- [ ] 5.2 Check the behaviour in the headless PyCharm harness with the EDT heartbeat and stack sampler:
  - Q42/Q71/Q68: a gutter Run, a Debug to `sample.robot:15`, Step Over, evaluating `Sleep    5s` in the Evaluate dialog, and disabling a breakpoint while paused each leave no EDT gap above 100 ms with RobotCode frames on the EDT, and no `threadDumps-freeze-*` folder appears; the evaluation shows its result after about five seconds;
  - Set Value of a local variable and loading the next page of a list with more than 100 items leave no such EDT gap, and the Variables view shows the new value and the next items;
  - Q54: a debuggee killed before it listens shows its exit code in the console, the test tree does not stay at "Running tests…", and `idea.log` gets no SEVERE entry;
  - Q49: the watches `1 + 2`, `${UNKNOWN}` and `Log    watch-side-effect` show `3`, `<undefined>` and an error message, `watch-side-effect` never appears in the console over two stops, and `idea.log` gets no SEVERE entry; `1 + 2` in the Evaluate dialog shows the "No keyword with name" message;
  - Stop while the handshake still connects ends the process, and `idea.log` gets no SEVERE entry.
