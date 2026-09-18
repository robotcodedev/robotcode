# Spec Delta

## Purpose

Defines the behaviour a Debug Adapter Protocol client can rely on when debugging a Robot Framework run through `robotcode debug`: session lifecycle and the synced-event handshake, breakpoints, stepping, stack and variable inspection, evaluation, exception filters, detaching and run-end events, on every supported Robot Framework version.

## ADDED Requirements

### Requirement: Session lifecycle

`robotcode debug` SHALL accept a DAP client over TCP, answer `initialize` with its capabilities, accept `attach` and `configurationDone` in either order, send `initialized` after `attach`, start the Robot Framework run once `configurationDone` has arrived, report the run's end with `robotExited` (carrying Robot Framework's return code), `terminated` and `exited`, in that order, and end its process once the client has disconnected.

#### Scenario: Run without breakpoints
- **WHEN** a client attaches, sends `configurationDone` without setting breakpoints, and the suite has one passing and one failing test
- **THEN** the client receives `robotStarted`/`robotEnded` events for the suites and both tests, `robotExited` with exit code 1, `terminated` and `exited` with exit code 1
- **AND** the server process exits with code 1 after the client's `disconnect`

#### Scenario: Terminate a running session
- **WHEN** the client sends `terminate` while the run is stopped at a breakpoint
- **THEN** the run ends, `terminated` is sent and the process exits after the client's `disconnect`

### Requirement: Synced events are acknowledged with robot/sync

Custom events whose body carries `synced: true` (`robotEnqueued`, `robotStarted`, `robotEnded`, `robotLog`, …) SHALL pause the Robot Framework run until the client acknowledges them with a `robot/sync` request, so that the client has processed an event before execution moves on; without an acknowledgement the run SHALL continue after 15 seconds. The server SHALL NOT wait for an acknowledgement when no client is connected and attached.

#### Scenario: Acknowledging client
- **WHEN** a client answers every synced event with `robot/sync`
- **THEN** a run of two short tests completes within a few seconds and the client has received every `robotStarted` event before the matching `robotEnded` event

### Requirement: Breakpoints stop the run at the requested line

Line breakpoints set with `setBreakpoints` SHALL be reported as verified and SHALL stop the run before the keyword on that line is executed, with a `stopped` event of reason `breakpoint`. A breakpoint condition (a Python expression over the current variables) SHALL stop only when it is true, a hit condition `N` SHALL stop only on the N-th hit of that line, and a log point SHALL emit its message, with Robot Framework variables replaced, as output without stopping.

#### Scenario: Line breakpoint
- **WHEN** a breakpoint is set on a keyword call line of a test
- **THEN** the client receives `stopped` with reason `breakpoint` and the top stack frame reports that file and line

#### Scenario: Conditional breakpoint
- **WHEN** a breakpoint inside a `FOR` loop over four values has the condition `$i == 1`
- **THEN** the run stops once, in the iteration where `${i}` is 1

#### Scenario: Hit condition
- **WHEN** a breakpoint inside a `FOR` loop over four values has the hit condition `2`
- **THEN** the run stops exactly once, in the second iteration

#### Scenario: Log point
- **WHEN** a breakpoint inside the loop has the log message `value is ${i}`
- **THEN** `value is 0`, `value is 1`, … appear as `output` events, one per iteration, and the run does not stop

### Requirement: Stack, scopes and variables reflect the execution state

At a stop, `stackTrace` SHALL list the keyword frames, the test and one frame per suite level from innermost to outermost with their source locations. `scopes` SHALL offer `Local`, `Suite` and `Global` for a frame directly in a test body, where `Local` holds the test's variables, and `Local`, `Test`, `Suite` and `Global` for a frame inside a user keyword called from a test. `variables` SHALL return the variables of a scope with their values, expandable for lists and dictionaries. `setVariable` SHALL evaluate the given value as a Python expression, after replacing Robot Framework variables in it, and assign the result for the rest of the run.

#### Scenario: Frames inside a resource keyword
- **WHEN** a directory is run and execution is stopped inside a user keyword from a resource file called by a test
- **THEN** the frames are the inner keyword call (resource file and line), the calling line in the test, the test, the file suite and the directory suite

#### Scenario: Variables by scope
- **WHEN** the run is stopped in a test body after `${local}=    Set Variable    value` with suite variables `${SUITE_VAR}`, `@{LIST_VAR}` and `&{DICT_VAR}`
- **THEN** `${local}` is in the `Local` scope, the three suite variables are in the `Suite` scope, and `@{LIST_VAR}` can be expanded into its items

#### Scenario: Test scope inside a user keyword
- **WHEN** the run is stopped inside a user keyword called from a test
- **THEN** the scopes are `Local` (the keyword's arguments), `Test`, `Suite` and `Global`

#### Scenario: Set variable
- **WHEN** the client sets `${local}` to the value `'changed'` and continues
- **THEN** the following `Log    ${local}` logs `changed`

### Requirement: Stepping

`next` SHALL stop at the next keyword in the current frame, `stepIn` SHALL stop at the first keyword inside a called user keyword, `stepOut` SHALL stop after the current user keyword returns, `continue` SHALL run to the next stop or the end, and `pause` SHALL stop a running session at the next keyword; each stop SHALL be reported with reason `step` or `pause`.

#### Scenario: Step into and out of a resource keyword
- **WHEN** the run is stopped on a line calling a resource keyword and the client sends `stepIn`, then `stepOut`
- **THEN** the first stop is on the first body line of the keyword in the resource file and the second on the line after the call

### Requirement: Evaluation and completion in the paused context

`evaluate` in the `watch` and `hover` contexts SHALL return the value of a variable or of a Python expression over the variables of the selected frame, and SHALL return an undefined marker instead of an error for an unknown variable. `evaluate` in the `repl` context SHALL treat the input as Robot Framework test-body syntax: a single variable returns its value, anything else is executed as a keyword call in the paused run. Failures in the `repl` context SHALL be reported as unsuccessful responses without ending the session. `completions` SHALL offer keywords and variables visible in the paused context.

#### Scenario: Evaluate a variable, an expression and a keyword
- **WHEN** the run is stopped with `${local}` set to `local value` and the client evaluates `${local}` and `$local.upper()` in the `watch` context and `Log    from the debug console` in the `repl` context
- **THEN** the first returns `'local value'`, the second `'LOCAL VALUE'`, and the third succeeds and its message appears as output

#### Scenario: Unknown variable
- **WHEN** the client evaluates `${does_not_exist}` in the `watch` context and then in the `repl` context
- **THEN** the first response is successful with the result `<undefined>`, the second is unsuccessful, and the session stays stopped

### Requirement: Exception filters stop on failures

Every exception filter the server declares in its capabilities — failed keyword, uncaught failed keyword, failed test, failed suite — SHALL be accepted by `setExceptionBreakpoints` and SHALL stop the run with a `stopped` event of reason `exception` carrying the failure message, whether the client sends the filter in `filters` or in `filterOptions`. Without a `setExceptionBreakpoints` request the uncaught-failed-keyword filter SHALL be active; a request enabling no filter SHALL disable all exception stops. "Uncaught" SHALL exclude failures handled by `TRY/EXCEPT` or by BuiltIn's error-handling keywords (`Run Keyword And Expect Error`, `Run Keyword And Ignore Error`, `Run Keyword And Return Status`, `Run Keyword And Continue On Failure`, `Run Keyword And Warn On Failure`, `Wait Until Keyword Succeeds`).

#### Scenario: Uncaught failed keyword
- **WHEN** the uncaught-failed-keyword filter is enabled through `filterOptions` and a test runs `Fail    boom`
- **THEN** the client receives `stopped` with reason `exception` and a text containing `boom`, and after `continue` the run finishes

#### Scenario: Plain filters
- **WHEN** the client sends `setExceptionBreakpoints` with `filters: ["uncaught_failed_keyword"]` and no `filterOptions`
- **THEN** the run stops at `Fail    boom` in the same way

#### Scenario: Default and disabled
- **WHEN** one session sends no `setExceptionBreakpoints` request and another sends one with empty `filters`
- **THEN** the first stops at `Fail    boom` and the second does not stop

#### Scenario: Caught failure with the uncaught filter
- **WHEN** only the uncaught filter is enabled and `Fail    expected` runs inside `TRY/EXCEPT` and inside `Run Keyword And Expect Error`
- **THEN** the run does not stop there

#### Scenario: Failed test
- **WHEN** only the failed-test filter is enabled and a test fails
- **THEN** the filter is reported as verified and the run stops at the end of that test with reason `exception` and a text starting with `Test failed`

#### Scenario: Failed suite
- **WHEN** only the failed-suite filter is enabled and a test of a file suite inside a directory suite fails
- **THEN** the run stops at the end of each failing suite level with a text starting with `Suite failed`

#### Scenario: Timeout while stopped
- **WHEN** a test with `[Timeout]    1 second` is stopped at a breakpoint for longer than its timeout, the default uncaught filter is active, and the client continues
- **THEN** the client receives an exception stop for the timed-out keyword, and after `continue` the test ends with status FAIL and the message `Test timeout 1 second exceeded.` and the session ends normally

### Requirement: A vanished or detached client never ends or stalls the run

After `disconnect` without `terminateDebuggee`, and likewise when the client connection is lost without the client having sent `terminate`, the server SHALL detach and carry on: a stopped run resumes, no further stops occur while no client is attached, no synced event waits for an acknowledgement, the server keeps accepting a new client, and the process ends when the run ends. Only `terminate`, or `disconnect` with `terminateDebuggee`, SHALL end the run early.

#### Scenario: Disconnect at a stop
- **WHEN** the client sends `disconnect` while the run is stopped at a breakpoint in a short test
- **THEN** the server process exits by itself within a few seconds with Robot Framework's return code

#### Scenario: Connection lost at a stop
- **WHEN** the client closes its socket while the run is stopped at a breakpoint in a short test
- **THEN** the run resumes and the server process exits by itself within a few seconds with Robot Framework's return code

### Requirement: A new client can attach to the session

While the run is in progress and no client is connected, the server SHALL accept a new client: it answers `initialize`, `attach`, breakpoint requests and `configurationDone`, reports the running thread with its current stack trace and variables, stops at the new client's breakpoints, sends it the synced and run-end events, and waits for its `disconnect` at the end of the run. A second client while one is connected SHALL be refused.

#### Scenario: New client after the first one vanished
- **WHEN** the first client closes its socket at a stop in a long-running test, and a second client connects, attaches and sets a breakpoint on a later line
- **THEN** the run stops at that breakpoint for the second client with a complete stack trace, and after `continue` the second client receives `robotExited`, `terminated` and `exited` and its `disconnect` is answered

#### Scenario: New client after a disconnect
- **WHEN** the first client sends `disconnect` at a stop in a long-running test, and a second client connects, attaches and sets a breakpoint on a later line
- **THEN** the run stops at that breakpoint for the second client and it can drive the run to its end
