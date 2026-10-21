# debugger-termination Specification

## Purpose

Defines how the RobotCode debugger behaves once a debug client, such as VS Code or the IntelliJ plugin, has asked it to end a Robot Framework run with a `terminate` request.

## Requirements

### Requirement: No pause after a terminate request

Once the debugger has received a `terminate` request, it SHALL NOT pause the run again: not at line breakpoints, exception breakpoints or on entry, and not for a step or a pause request from the client. A pause that is just beginning when the request arrives SHALL end at once. The run SHALL continue to its end, with its teardowns and its output files. A breakpoint with a log message SHALL keep writing its message when the run reaches it.

#### Scenario: Line breakpoint in a teardown

- **WHEN** a run is paused at a line breakpoint in a test, the test's `[Teardown]` has a line breakpoint too, and the client sends `terminate`
- **THEN** the run does not pause in the teardown and ends without a further request from the client
- **AND** the test fails with "Execution terminated by signal", its teardown runs, and the output files are written

#### Scenario: Log message in a teardown

- **WHEN** the breakpoint in that teardown has a log message instead of pausing, and the client sends `terminate` while the run is paused in the test
- **THEN** the debugger writes the message when the teardown reaches the breakpoint, and the run ends without pausing

#### Scenario: Terminate while a pause begins

- **WHEN** the `terminate` request arrives while the run is just pausing at a breakpoint, before it is shown as paused
- **THEN** the run goes on at once and ends without a further request from the client

#### Scenario: Step or pause request after terminate

- **WHEN** the client sends `next`, `stepIn`, `stepOut` or `pause` after `terminate`
- **THEN** the run does not pause at the next keyword

#### Scenario: Exception breakpoint after terminate

- **WHEN** the exception breakpoint for failed keywords is enabled and a keyword fails after `terminate`
- **THEN** the run does not pause at the failure

### Requirement: A terminate request after the run has ended

When a `terminate` request arrives after the debugger has reported the end of the run with the `exited` event, the debugger SHALL NOT interrupt its process. The process SHALL end with the exit code of the run, as after a `disconnect` alone.

#### Scenario: Run from VS Code's Test Explorer

- **WHEN** a run from the Test Explorer passes and VS Code sends `disconnect` and then `terminate` after the `exited` event
- **THEN** the process ends with exit code 0

#### Scenario: Terminate during the run

- **WHEN** the client sends `terminate` while the run is still in progress
- **THEN** the debugger interrupts the run as before
