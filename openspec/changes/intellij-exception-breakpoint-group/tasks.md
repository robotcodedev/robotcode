# Tasks

## 1. One exception breakpoint type

- [ ] 1.1 Replace the four exception breakpoint types with one `RobotCodeExceptionBreakpointType`, id `robotcode-exception`, titled "Robot Framework Exception Breakpoints" through `messages/RobotCode.properties`, whose default breakpoint is "Uncaught Failed Keywords", enabled, and whose display text is the name of the breakpoint's kind; give `RobotCodeExceptionBreakpointProperties` a `kind` text property with `loadState` through `XmlSerializerUtil.copyBean`, a missing kind counting as "Uncaught Failed Keywords"; register only this type in `plugin.xml`. Verify with a JUnit test that serializes the properties with and without a kind and reads them back, and that the kind names, including the one for a missing kind, come out as expected.
- [ ] 1.2 Show the add button of the type: `addBreakpoint` opens a modal `ChooseElementsDialog` with the kinds the project does not have yet, adds each chosen kind as an enabled breakpoint in a write action and returns the first one; when no kind is missing, it shows an info message and returns `null`. Verify with a JUnit test of the missing kinds for none, some and all kinds present, and with the harness checks in task 3.2.

## 2. Debug process

- [ ] 2.1 Register one `RobotCodeExceptionBreakpointHandler` for the type in `RobotCodeDebugProcess` and read the filter of a breakpoint from the kind in its properties. Verify that `RobotCodeExceptionBreakpointsTest` passes unchanged, and with the stop checks in task 3.2.

## 3. Verification

- [ ] 3.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 3.2 Check the behaviour in the headless PyCharm harness:
  - the Breakpoints dialog shows one "Robot Framework Exception Breakpoints" group that holds "Uncaught Failed Keywords", enabled and not removable;
  - the add button adds "Failed Tests", enabled, and then offers only "Failed Keywords" and "Failed Suites";
  - with "Failed Tests" added, a failing test stops when it ends and shows its message, and after removing it the test runs through; with "Failed Keywords" added, a failure inside `TRY/EXCEPT` stops;
  - "Failed Tests" with the suspend policy None is still in the group after an IDE restart, with that policy;
  - a workspace that stores the former "Any Exception" breakpoint as disabled shows "Uncaught Failed Keywords" disabled;
  - `idea.log` gets no new SEVERE entries from RobotCode.

## Workflow follow-up

- Implement only after `intellij-debugger-expressions` is committed; both change `RobotCodeDebugProcess.kt`.
