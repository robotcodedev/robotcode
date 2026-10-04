# Proposal

## Why

In PyCharm and IntelliJ IDEA, Stop does not end a Robot Framework run that is paused in the debugger. The IDE stops a run by interrupting its process. Robot Framework notes the first interrupt ("Second signal will force exit.") but the paused debugger keeps waiting for a command, so the run stays paused. Only a second Stop, which kills the process, ends it, and then Robot Framework writes neither `output.xml` nor the log or the report. Rerunning a paused session hangs the same way until the user kills the old process. In VS Code, Stop asks the RobotCode debugger to end the run. The debugger then interrupts Robot Framework itself and lets the paused run continue to a graceful end.

The same start-up code has a second defect. Every run first tries the debugger port 6612. Two runs started at the same moment, for example from a compound configuration, with "Allow multiple instances" or by overlapping gutter runs, can both pick it, and the second run can end up connected to the first run's debugger.

## What Changes

- Stop asks the RobotCode debugger to end the run, as VS Code does. Robot Framework then stops as on Ctrl+C in a terminal: the running test fails with "Execution terminated by signal", the remaining tests are not run, teardowns run, and `output.xml`, `log.html` and `report.html` are written. This works for Run and for Debug, and whether the run is paused or running.
- While the debugger handles the request, the IDE sends no signal of its own. If the debugger is not connected or does not confirm the request within five seconds, Stop interrupts the process as it does today.
- A paused run shows as running again as soon as it continues towards its end, so the Debug tool window no longer shows stale frames.
- Pressing Stop again while a run is ending still kills the process at once.
- Rerunning a paused debug session ends the old run gracefully and starts the new one without a Kill.
- Every run asks the operating system for a free port for its debugger connection and always passes it to robotcode, so runs started at the same time no longer share a port.

Behaviour that users notice, for the release notes (not breaking): one Stop ends a paused debug session and still writes the report and the log. Because Stop now always ends a run gracefully, teardowns run before the run ends; a second Stop kills it.

Not part of this change: detaching from a run that was started outside the IDE; timeouts for the debugger handshake, and starting runs without blocking the IDE; a connection mode in which the IDE listens and the debugger connects back; changes to how the RobotCode debugger handles a stop request; runs on remote interpreters.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-debugging`: Stop ends Run and Debug sessions gracefully, also while paused, and concurrent runs use separate debugger ports.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeRunProfileState.kt`: creates the new process handler, allocates the port and always passes `--tcp` among the debugger options.
- A new process handler class and a small stop policy in `execution/`.
- `debugging/RobotCodeDebugProcess.kt` and `debugging/RobotCodeDebugProtocolClient.kt`: the `continued` event, and `stop()` without a blocking request.
- `utils/NetUtils.kt`: the port probing goes.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the RobotCode debugger, the language server or the VS Code extension.
