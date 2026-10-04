# Tasks

## 1. Precondition and expression editors

- [ ] 1.1 Check that `debugger-dap-e2e-tests` has landed: its scenarios "Failed test" and "Hit condition" exist under `tests/robotcode/debugger/` and pass with `hatch run test:test`. The hit count and the "Failed Tests" breakpoint (tasks 4.2, 4.3 and 4.5) depend on it.
- [ ] 1.2 Let `RobotCodeXDebuggerEditorsProvider.createExpressionCodeFragment` create the fragment with the event system enabled when `isPhysical` is requested, and mark it with a user data key. Check in the harness with the Q50 setup (type into the Evaluate dialog for a minute, with the LSP trace on) that `idea.log` gets no SEVERE entry and that LSP4IJ sends nothing for the fragment. If SEVERE entries remain, let `RobotCodeTokensFileViewProviderFactory` return the platform's default view provider for in-memory Robot Framework files and check again; if LSP4IJ sends requests for the fragment, exclude such files through LSP4IJ's per-file client feature switch.
- [ ] 1.3 Add a completion contributor for the Robot Framework language that acts only in marked files, asks the current session's debug process for DAP `completions` in the selected frame with a bounded, cancellable wait, and builds lookup elements with label, kind icon and detail; register it in `plugin.xml`. Verify with a JUnit test that DAP completion items of each kind become the expected lookup elements, and with the completion harness checks in task 5.2.

## 2. Hover

- [ ] 2.1 Add the request `robot/debugging/getEvaluatableExpression` to `RobotCodeServerApi` and override `getExpressionInfoAtOffsetAsync` in `RobotCodeDebuggerEvaluator`: send the file URI as LSP4IJ reports it and the position of the offset, and resolve the promise with the returned range and expression or with `null`. Verify with a JUnit test that converts a returned LSP range into the expected text range of a document and handles `null`, and with harness check Q56.

## 3. Robot debug console

- [ ] 3.1 Add a `ConsoleRootType` for the console history and register it as a scratch root type in `plugin.xml`; override `createTabLayouter()` in `RobotCodeDebugProcess` to add a "Robot Debug Console" tab with a `LanguageConsoleImpl` for the Robot Framework language, a `ConsoleExecuteAction` with a `BaseConsoleExecuteActionHandler` and a `ConsoleHistoryController`; mark the console's input file for the completion contributor. Executing a line evaluates it in the `repl` context with the selected frame and prints the result or the debugger's error message; while the session is not suspended it prints that the run is not paused. Verify with the console harness checks in task 5.2.

## 4. Breakpoint options

- [ ] 4.1 Implement `loadState` of `RobotCodeLineBreakpointProperties` and `RobotCodeExceptionBreakpointProperties` with `XmlSerializerUtil.copyBean`, and add a hit count property to the line breakpoint properties. Verify with a JUnit test that serializes the properties with `XmlSerializer` and reads them back, with and without a hit count.
- [ ] 4.2 Override `getEditorsProvider(breakpoint, project)` in `RobotCodeLineBreakpointType` with the expression editors provider, and `createCustomConditionsPanel` with a hit count field (positive integers) and a comment on the meaning of the log text with and without Suspend; put the texts in `messages/RobotCode.properties`. Verify with harness check Q47 that the breakpoint popup shows Condition, "Evaluate and log" and the hit count.
- [ ] 4.3 Build the `SourceBreakpoint` from the breakpoint: `condition` when enabled, `hitCondition` from the hit count, `logMessage` only with the suspend policy None. Verify with a JUnit test of the mapping for each suspend policy, with and without condition, log expression and hit count.
- [ ] 4.4 Keep the ids of each `setBreakpoints` response per file in the breakpoint bookkeeping; map a stop with reason `breakpoint` to its breakpoint through `hitBreakpointIds`, evaluate the log expression of a suspending breakpoint in the `watch` context, call `breakpointReached` with the result and continue when it returns `false`; fall back to `positionReached` for unknown ids. Verify with JUnit tests of the id lookup (current ids, ids of an older response, the temporary Run to Cursor entry) and with the breakpoint harness checks.
- [ ] 4.5 Add the "Failed Tests" exception breakpoint type on the common base (filter `failed_test`, disabled by default), register it in `plugin.xml` with its texts, and map stops with the description "Test failed." to it. Verify with a JUnit test of the mapping and with the failed-test harness check.

## 5. Verification

- [ ] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 5.2 Check the behaviour in the headless PyCharm harness with `sample.robot` and `loop.robot` (a `FOR` loop over the numbers 0 to 7). Trigger completion by typing a letter, because Ctrl+Space opens no lookup under Xvfb:
  - Q50: typing in the Evaluate dialog for a minute adds no SEVERE entry; typing `${` offers variables of the frame, and typing `Lo` offers `Log`;
  - Q47: the condition `${i} == 3` stops once with `${i}` being 3; the log message `value is ${i}` with suspend policy None prints eight lines and does not stop; suspend policy None with the "Breakpoint hit" message does not stop visibly and logs the message; "Remove once hit" stops once and removes the breakpoint; a breakpoint that waits for another one stops only after the other was hit;
  - the hit count 2 stops in the second iteration only; the "Failed Tests" breakpoint stops at the end of "Third Test Fails" and shows its failure message;
  - Q56: hovering `${message}` while paused shows its value;
  - Robot Debug Console: `Log    hello` runs and `hello` appears in the run's output, the history key recalls the line, typing a letter offers keywords, and a line entered while the run is not paused is not evaluated;
  - a breakpoint with a condition, a log message and a hit count keeps them after an IDE restart;
  - `idea.log` gets no new SEVERE entries from RobotCode.
