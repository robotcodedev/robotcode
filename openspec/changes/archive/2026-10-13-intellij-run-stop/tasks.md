# Tasks

## 1. Debugger port

- [x] 1.1 In `RobotCodeRunProfileState.buildPythonExecution`, allocate an OS-assigned port (bind port 0, read it, close the socket) instead of `NetUtils.findFreePort(6612)`, and let `debugArguments` pass `--tcp <port>` for every port; remove `utils/NetUtils.kt`, which nothing else uses. Verify with JUnit tests that several allocations do not all return the same port and that `--tcp <port>` comes after `--no-debug` and before `--` and every Robot Framework argument for Run and for Debug, with the other arguments unchanged; the assertion in `RobotCodeRunTargetTest` that the default port is left out changes accordingly.

## 2. Graceful stop

- [x] 2.1 Add the stop policy class in `execution/` with injected functions (send `terminate`, returning the response future or nothing without a connection; fallback; scheduler) and a five-second confirmation timeout. Verify with JUnit tests using fakes: `terminate` is sent once; nothing else happens while the response is pending; no fallback after a response; exactly one fallback after the timeout, after a failed send, and at once without a connection; a second destroy request sends no second `terminate`.
- [x] 2.2 Override `doDestroyProcess()` in `RobotCodeProcessHandler` so that it hands the stop to the policy, with the inherited `doDestroyProcess()` as the fallback; keep `killProcess()` unchanged. The state's `createProcessHandler` override hands the handler a `terminate` function that reads the DAP connection through a nullable reference. Verify that the plugin builds and, in task 3.2, the stop behaviour.
- [x] 2.3 Handle the `continued` event in `RobotCodeDebugProtocolClient` with a new signal and call `XDebugSession.sessionResumed()` from `RobotCodeDebugProcess`. Verify with a JUnit test that calling the client's `continued` handler fires the signal, and in task 3.2 that the Debug tool window leaves the paused state after Stop.
- [x] 2.4 Change `RobotCodeDebugProcess.stop()` to send `terminate` only while the connection is up, from a pooled thread and without waiting for the answer. Verify in task 3.2 that a session whose debuggee was killed ends without a hang and without new SEVERE entries.
- [x] 2.5 Let the output fence of `RobotCodeProcessHandler` skip its wait only once the process has ended (`isProcessTerminated`), not already while it is terminating. Verify in task 3.2.

## 3. Verification

- [x] 3.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [x] 3.2 Check the behaviour in the headless PyCharm harness with the process log, the console text and the mtimes of the output files:
  - Q43/Q62(a): paused at a breakpoint in `sample.robot`, one Stop ends the process within ten seconds; the console shows "Second signal will force exit." once and no "Execution forcefully stopped."; `log.html` and `report.html` are rewritten; the session no longer reports itself as suspended after the Stop;
  - Rerun while paused at that breakpoint starts the new process within ten seconds without a Kill;
  - Q62(b)/Q76: in Run mode, Stop during `Sleep    30s` ends the run gracefully with all three output files written;
  - a test whose `[Teardown]` runs `Sleep    30s`: the first Stop lets the teardown start, the second Stop (Kill) ends the process at once;
  - Q16: a compound configuration with two Robot Framework configurations starts two processes with different `--tcp` ports, and both result trees are complete;
  - a configuration with "Allow multiple instances" started twice while its first run is still running starts two processes with different `--tcp` ports, and both result trees are complete;
  - a test whose `[Teardown]` and whose suite's `Suite Teardown` call `Log To Console`, stopped during `Sleep    30s` in five runs: the test's result node shows the test teardown's line and "Second signal will force exit.", and the suite's node shows the suite teardown's line;
  - after a debuggee is killed from outside while paused, the session ends without a hang;
  - `idea.log` gets no new SEVERE entries from RobotCode.
