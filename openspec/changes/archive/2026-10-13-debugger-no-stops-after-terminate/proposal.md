# Proposal

## Why

After a debug client has asked the RobotCode debugger to end a run with a `terminate` request, the run still stops at line breakpoints that it reaches on its way to the end, such as a breakpoint in a test's `[Teardown]`. A DAP probe that drives `robotcode debug` as the IDEs do showed it: stopped in a test body, `terminate`, and the run stopped again in the teardown until the client sent `continue`. In PyCharm and IntelliJ IDEA, Stop sends `terminate` since `intellij-run-stop`, so the session shows as paused again after Stop, and a second Stop kills the process without writing the output, the log or the report. VS Code sends the same request to the same debugger.

## What Changes

- Once the debugger has received a `terminate` request, it no longer pauses the run: not at line breakpoints, not for steps, not for pause requests and not on entry. Exception breakpoints already behave this way and keep doing so.
- Breakpoints with a log message, which never pause the run, keep writing their message after `terminate`.
- The run itself ends as before: teardowns run, and Robot Framework writes its output files.

Not part of this change: what the debugger does with a second `terminate` request (SIGTERM), `disconnect`, and the command-line debugger of `robotcode robot-debug`.

## Capabilities

### New Capabilities

- `debugger-termination`: how the RobotCode debugger behaves once a debug client has asked it to end a run with a `terminate` request.

### Modified Capabilities

_None._

## Impact

- `packages/debugger/src/robotcode/debugger/debugger.py`: the places that pause the run (`process_start_state` for pause requests, steps and line breakpoints; the stop on entry in `start_suite`) skip pausing once `terminated` is set.
- New tests under `tests/robotcode/debugger/`.
- No change to the DAP messages, the IntelliJ plugin or the VS Code extension; both clients get the new behaviour through the debugger.
