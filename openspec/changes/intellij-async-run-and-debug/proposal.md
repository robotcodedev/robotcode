# Proposal

## Why

In PyCharm and IntelliJ IDEA, the RobotCode plugin waits for the Robot Framework process and its debugger on the IDE's user interface thread. Every Run and Debug start freezes the IDE for about half a second while the plugin connects to the debugger. If the debugger never comes up, for example because the process died before it could listen, the IDE freezes for ten seconds and then reports two "IDE errors" from RobotCode. While debugging, each step and each change to a breakpoint blocks the IDE for a round trip, and evaluating a keyword such as `Sleep    5s` in the Evaluate dialog freezes the whole IDE until the keyword has finished. None of these waits has a limit, so a debugger that stops answering would freeze the IDE for good.

Evaluation has two more defects. Every evaluation runs as if typed into a debug console, so a watch such as `Log    something` runs the keyword again at every stop, and a watch on an unknown variable fails instead of showing that the variable is undefined. And when the debugger reports an error, the IDE shows only the error type, such as `ExecutionFailed`, plus an "IDE error occurred" balloon, although the debugger sends a readable message.

## What Changes

- Run and Debug start without blocking the IDE: the plugin starts the process and connects to the debugger in the background.
- Stepping, resuming, pausing, Run to Cursor, evaluating, expanding variables and changing breakpoints no longer block the IDE. A keyword evaluated from the debugger may run as long as the debugger waits for it, 60 seconds, while the IDE stays usable; every wait has a limit.
- If the debugger does not accept the connection within 15 seconds while its process is running, the run's console says so and the run ends. If the process ends before it connected, the run ends with the process's exit code. Neither case shows an "IDE error" balloon.
- The Evaluate dialog and the inline evaluation field keep their current meaning: a single variable shows its value, anything else runs as a keyword call. Watches are evaluated as expressions instead: they never run keywords, and an unknown variable shows as `<undefined>`.
- When the debugger reports an error for an evaluation, the IDE shows the debugger's message, for example "No keyword with name '1 + 2' found.", and logs no IDE error.

Behaviour that users notice, for the release notes (not breaking): watches no longer run keywords; a watch like `Log    something` now shows an error message instead of logging at every stop. Write keyword calls in the Evaluate dialog instead.

Not part of this change: completion, syntax-aware editing and hover values in the debugger; a debug console; paging and changing variable values, and frame names; settings for the connection and debugger timeouts; how Robot Framework events become test results.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-debugging`: Run and Debug sessions start, and debugger actions complete, without blocking the user interface; a debugger that never connects is reported; evaluation errors and evaluation contexts.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeProgramRunner.kt` and `debugging/RobotCodeDebugProgramRunner.kt`: start the process off the user interface thread.
- `execution/RobotCodeRunProfileState.kt`: the handshake runs in a coroutine scope of its own per run.
- `debugging/RobotCodeDebugProcess.kt`, `RobotCodeDebuggerEvaluator.kt`, `RobotCodeStackFrame.kt`, `RobotCodeNamedValue.kt`, `RobotCodeValueGroup.kt`: asynchronous completion of every debugger callback, timeouts, evaluation contexts and error messages.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the RobotCode debugger, the language server or the VS Code extension.
