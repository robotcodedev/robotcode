# Proposal: intellij-debugger-session-builder

## Why

[RobotCodeDebugProgramRunner.kt](../../../intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/debugging/RobotCodeDebugProgramRunner.kt) starts a debug session with `XDebuggerManager.startSession(environment, starter)` and hands `XDebugSession.runContentDescriptor` back to the platform. Both calls are deprecated in 2026.1 (261), 262 and 263, and the compiler and `verifyPlugin` report them. The documented replacement is `XDebuggerManager.newSessionBuilder(starter)`. It exists since the new minimum 2026.1, and the platform's Java debugger runner already uses it there. None of the deprecated methods is marked for removal, so this is cleanup, not a fix for a break.

## What Changes

- The debug runner starts the session with `newSessionBuilder(starter).environment(environment).startSession()`.
- It returns the `runContentDescriptor` of the started result instead of the one from the session.
- Unchanged:
  - the debug process (`RobotCodeDebugProcess`) and how the Robot Framework run is started inside the starter;
  - the debug tab, content reuse on rerun, breakpoints and the run configuration.
- Trade-off agreed beforehand: `XDebugSessionBuilder` and `XSessionStartedResult` are `@ApiStatus.Experimental` in 261 and stable from 262 on.
  - On 261, `verifyPlugin` lists the builder under experimental API usages instead of the two deprecated usages.
  - From 262 on, it lists neither.
  - Experimental usages do not fail the verification (`failureLevel` in `build.gradle.kts`).

## Capabilities

### New Capabilities

- `intellij-debugging`: How the IntelliJ plugin starts a debug session for a Robot Framework run configuration, and that it does so without debugger API the minimum supported platform deprecates.

### Modified Capabilities

<!-- none -->

## Impact

- [RobotCodeDebugProgramRunner.kt](../../../intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/debugging/RobotCodeDebugProgramRunner.kt): `doExecute` only. Its return type becomes nullable, which `execute` already allows (`Promise<RunContentDescriptor?>`).
- No change to the other debugger classes, `plugin.xml`, the build script, the minimum platform version, the VS Code extension or the Python debugger.
- No user-visible change when debugging.
- Verification: build, tests, `verifyPlugin`, and a debug session in `runIde` covering breakpoint, stepping, rerun and stop.
