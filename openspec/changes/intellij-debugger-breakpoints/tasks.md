# Tasks

## 1. Line breakpoints

- [ ] 1.1 Add the breakpoint bookkeeping class in `debugging/`: per file an ordered set of breakpoint objects, a map from breakpoint to the file it was registered under, lines computed when a request list is built, and one optional temporary Run to Cursor entry per session. Verify with JUnit tests on plain objects that the request lists are right after add, disable (unregister), mute (unregister all), unmute, a line move, a move to another file (an empty list for the old file), remove, and adding and removing the temporary entry.
- [ ] 1.2 Use the class in `RobotCodeDebugProcess`: register and unregister update it and send the complete list of every affected file, an empty list included, under one lock; take the verified state from the response by position; remove the unused breakpoint list and line-keyed map. Verify with the unit tests of 1.1 and the harness checks Q45 and Q46 in task 5.2.
- [ ] 1.3 Rework Run to Cursor: always resume; add the temporary entry only when no registered breakpoint is on the target line; remove it at the next stop and send the list again; do all of this under the same lock. Verify with a unit test for the temporary entry and harness check Q52.

## 2. Configuration phase

- [ ] 2.1 Override `initialized` in `RobotCodeDebugProtocolClient` and complete a latch that the state creates before it sends `initialize`; the handshake waits for it for at most five seconds. Verify with a JUnit test against a fake DAP server (lsp4j `DebugLauncher` on a local socket) that sends `initialized` before the `initialize` response, and one that never sends it.
- [ ] 2.2 Restructure the handshake in `RobotCodeRunProfileState`: `initialize`, the `initialized` latch, a configuration step that the debug process provides (all `setBreakpoints` requests and `setExceptionBreakpoints`, all awaited; nothing in Run mode), `attach` (awaited), then `configurationDone` (awaited). Replace the asynchronous breakpoint sending on `afterInitialize`; keep the 10 s connect wait. Verify with a JUnit test against the fake DAP server that records the requests: the order is `initialize`, `setBreakpoints`…, `setExceptionBreakpoints`, `attach`, `configurationDone`, and `configurationDone` is sent only after every `setBreakpoints` response has arrived.

## 3. Exception breakpoints

- [ ] 3.1 Replace the exception breakpoint type by three types with a common base, one handler each and a default breakpoint each: "Uncaught Failed Keywords" (id `robotcode-exception`, enabled), "Failed Keywords" and "Failed Suites" (disabled); register them in `plugin.xml` and put their titles and display texts in `messages/RobotCode.properties`. Verify that the plugin builds and, in task 5.2, that View Breakpoints lists the three types and that a workspace with a disabled "Any Exception" breakpoint shows "Uncaught Failed Keywords" disabled.
- [ ] 3.2 Send `setExceptionBreakpoints` with empty `filters` and one `filterOptions` entry per registered exception breakpoint in the configuration phase and after every register and unregister, an empty list when none is registered. Verify with a JUnit test that the request contains exactly the registered filters, and an empty list after all are unregistered.
- [ ] 3.3 Map stops with reason `exception` by their description ("Keyword failed." to "Failed Keywords" if registered, else "Uncaught Failed Keywords"; "Suite failed." to "Failed Suites"), call `breakpointReached` and continue when it returns `false`, show the stop text with `XDebugSession.reportMessage` when the session suspends, and fall back to `positionReached` without a match. Verify with a JUnit test of the mapping, including an unknown description and a description whose breakpoint is not registered, and with harness check Q44.

## 4. Placement

- [ ] 4.1 Let `RobotCodeLineBreakpointType.canPutAt` accept only files of the Robot Framework suite and resource file types. Verify with harness check Q48. If the #658 fix has already landed, verify only that it matches this rule.

## 5. Verification

- [ ] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 5.2 Check the behaviour in the headless PyCharm harness with `loop.robot` (one keyword with a single breakpoint, called eight times in a `FOR` loop) and `sample.robot`:
  - Q45: after disabling the breakpoint in the gutter popup, after Mute Breakpoints, after Force Step Over on the call line, and after removing all breakpoints, the run no longer stops at the affected lines;
  - Q46: a breakpoint dragged to another line stops only at its new line; inserting a line above a breakpoint moves the stop with it;
  - Q52: Run to Cursor onto a line with a breakpoint resumes and stops there, and a Run to Cursor target without a breakpoint does not stop a second time;
  - Q54/Q73: ten Debug starts after an IDE restart each stop at a breakpoint on the first keyword line;
  - Q44: with all exception breakpoints disabled, and with "Uncaught Failed Keywords" set to suspend policy None, "Third Test Fails" finishes without hanging and `idea.log` gets no SEVERE entry; with "Failed Keywords" enabled, the run stops at the first failing keyword and the failure message is shown;
  - Q48: a real gutter click in a `.py` file creates a Python breakpoint, and one in a `.txt` file creates no Robot Framework breakpoint.
