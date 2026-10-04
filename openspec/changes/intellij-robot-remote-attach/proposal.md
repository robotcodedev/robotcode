# Proposal

## Why

In VS Code, the debugger can attach to a `robotcode debug` process that was started elsewhere: in a terminal, in a container, on a CI machine or on another computer. Path mappings connect the local files with the files on the other side, where the project may live in another folder (the "RobotCode: Remote-Attach" configuration). In PyCharm and IntelliJ IDEA, the RobotCode plugin can only debug runs that it starts itself.

## What Changes

- A new configuration "Robot Framework (Attach)" under the Robot Framework configuration type, with:
  - host, `127.0.0.1` by default, and port, `6612` by default;
  - path mappings from a local folder to the folder on the side of the run, empty by default for runs on the same machine.
  It starts no process and has no interpreter, environment or Robot Framework options. It can only be started with Debug. Its editor says how to start a run to attach to, for example with `robotcode debug --tcp 0.0.0.0:6612`.
- Debug connects to that run, sends the path mappings and then debugs as for a run the IDE started: breakpoints and exception breakpoints in the local files, frames that open the local files, variables and evaluation. The debugger's output appears in the session's console.
- Stop detaches the debugger: the run goes on to its end without stopping and without waiting for the IDE. A "Terminate Run" action in the debug session ends the run gracefully, so its report and log are still written.
- If nothing accepts the connection within 15 seconds, the session ends with a message in its console.

Not part of this change: debugging the Python code of keywords in the same session; running tests on remote interpreters; showing the test results of an attached run; starting the run to attach to from the IDE.

## Capabilities

### New Capabilities

- `intellij-run-configurations`: the "Robot Framework (Attach)" configuration, its options, storage and validation.

### Modified Capabilities

- `intellij-debugging`: debugging a run started elsewhere, with path mappings, detach and terminate.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/`: the attach configuration with its options class, factory and editor; a second factory in `RobotCodeConfigurationType.kt`; `RobotCodeRunConfigurationProducer.kt` picks the launch factory by its id.
- `debugging/`: a run state and a process handler without a process for attach sessions; `RobotCodeDebugProgramRunner.kt` accepts the attach configuration; `RobotCodeDebugProcess.kt` works with either kind of session and offers the terminate action.
- `messages/RobotCode.properties`: the texts of the configuration, its editor and the action.
- New unit tests under `intellij-client/src/test/kotlin/`.
- Requires the debugger fix of `debugger-dap-e2e-tests` that keeps a detached run from waiting for acknowledgements. No change to the language server or the VS Code extension.
