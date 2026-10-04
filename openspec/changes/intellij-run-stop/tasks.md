# Tasks

## 1. Debugger port

- [ ] 1.1 In `RobotCodeRunProfileState`, allocate an OS-assigned port (bind port 0, read it, close the socket) and always pass `--tcp <port>` after `debug` and `--no-debug`, before the Robot Framework arguments; remove the probing code from `utils/NetUtils.kt`. Keep the `debug` argument list in a small function and verify with a JUnit test that two allocations return different ports, that `--tcp <port>` is among the debugger options and before every Robot Framework argument for Run and for Debug, and that the other arguments are unchanged.

## 2. Graceful stop

- [ ] 2.1 Add the stop policy class in `execution/` with injected functions (send `terminate`, returning the response future or nothing without a connection; fallback; scheduler) and a five-second confirmation timeout. Verify with JUnit tests using fakes: `terminate` is sent once; nothing else happens while the response is pending; no fallback after a response; exactly one fallback after the timeout, after a failed send, and at once without a connection; a second destroy request sends no second `terminate`.
- [ ] 2.2 Add the `KillableColoredProcessHandler` subclass whose `doDestroyProcess()` hands the stop to the policy and whose fallback calls the inherited `doDestroyProcess()`; keep `killProcess()` unchanged. Create it in `RobotCodeRunProfileState.startProcess()` with a `terminate` function that reads the DAP connection through a nullable reference; if `intellij-run-configuration-target` has already landed, return it from the state's `createProcessHandler(Process, String, TargetEnvironment, TargetedCommandLine)` override instead. Verify that the plugin builds and, in task 3.2, the stop behaviour.
- [ ] 2.3 Handle the `continued` event in `RobotCodeDebugProtocolClient` with a new signal and call `XDebugSession.sessionResumed()` from `RobotCodeDebugProcess`. Verify with a JUnit test that calling the client's `continued` handler fires the signal, and in task 3.2 that the Debug tool window leaves the paused state after Stop.
- [ ] 2.4 Change `RobotCodeDebugProcess.stop()` to send `terminate` only while the connection is up, from a pooled thread and without waiting for the answer. Verify in task 3.2 that a session whose debuggee was killed ends without a hang and without new SEVERE entries.

## 3. Verification

- [ ] 3.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 3.2 Check the behaviour in the headless PyCharm harness with the process log, the console text and the mtimes of the output files:
  - Q43/Q62(a): paused at `sample.robot:15`, one Stop ends the process within ten seconds; the console shows "Second signal will force exit." once and no "Execution forcefully stopped."; `log.html` and `report.html` are rewritten; the session no longer reports itself as suspended after the Stop;
  - Rerun while paused at `sample.robot:15` starts the new process within ten seconds without a Kill;
  - Q62(b)/Q76: in Run mode, Stop during `Sleep    30s` ends the run gracefully with all three output files written;
  - a test whose `[Teardown]` runs `Sleep    30s`: the first Stop lets the teardown start, the second Stop (Kill) ends the process at once;
  - Q16: a compound configuration with two Robot Framework configurations starts two processes with different `--tcp` ports, and both result trees are complete;
  - after a debuggee is killed from outside while paused, the session ends without a hang;
  - `idea.log` gets no new SEVERE entries from RobotCode.
