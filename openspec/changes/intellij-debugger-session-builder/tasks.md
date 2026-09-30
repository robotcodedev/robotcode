# Tasks: intellij-debugger-session-builder

## 1. Implementation

- [ ] 1.1 In `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/debugging/RobotCodeDebugProgramRunner.kt`, replace `manager.startSession(environment, starter)` and `session.runContentDescriptor` in `doExecute` (design D1, D2):
  - use `XDebuggerManager.getInstance(environment.project).newSessionBuilder(starter).environment(environment).startSession().runContentDescriptor`;
  - keep the starter object unchanged;
  - change the return type of `doExecute` to `RunContentDescriptor?`;
  - remove imports that are no longer used.

  Verify that `(cd intellij-client && ./gradlew compileKotlin --rerun-tasks)` prints no `w:` line for `RobotCodeDebugProgramRunner.kt`.

## 2. Verification

- [ ] 2.1 Run `(cd intellij-client && ./gradlew build test)` and verify that build and tests pass.
- [ ] 2.2 Run `(cd intellij-client && ./gradlew verifyPlugin)`. In `intellij-client/build/reports/pluginVerifier/*/report.md`, verify:
  - the plugin is reported compatible with PY-261, 262 and 263;
  - no `Deprecated` line mentions `xdebugger` for any of the three;
  - among the experimental usages, 261 adds only entries for `XDebugSessionBuilder` / `XSessionStartedResult` from `RobotCodeDebugProgramRunner`, and 262 and 263 list none for `xdebugger`.
- [ ] 2.3 Start `(cd intellij-client && ./gradlew runIde)`, open a Robot Framework project and set a line breakpoint on a keyword call in a test. Verify the scenarios of the spec:
  - Debug the test: a session tab opens in the Debug tool window with console output, and the run stops at the breakpoint with call stack and variables.
  - Step over, then resume: the run finishes and the session ends.
  - Rerun from the session tab: the same tab is reused.
  - Start again and stop it: the process ends.
  - `intellij-client/.intellijPlatform/sandbox/robotcode4ij/PY-2026.1/log_runIde/idea.log` shows no exception from `com.intellij.xdebugger` or `dev.robotcode.robotcode4ij.debugging`.
