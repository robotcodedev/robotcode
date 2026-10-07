# Spec Delta

## ADDED Requirements

### Requirement: Stop ends a Robot Framework run gracefully

When the user stops a Robot Framework run that the IDE started, in a Run or a Debug session, or reruns it while it is still running, the plugin SHALL ask the RobotCode debugger to end the run, so that Robot Framework stops gracefully: the running test fails, the remaining tests are not run, teardowns run, and the output files are written. This SHALL work whether the run is paused in the debugger or running.

#### Scenario: Stop while paused at a breakpoint

- **WHEN** a debug session is paused at a breakpoint in a test and the user presses Stop once
- **THEN** the run ends without a further Stop, Robot Framework reports a single stop signal ("Second signal will force exit.") and no forced exit ("Execution forcefully stopped."), the stopped test fails, and `output.xml`, `log.html` and `report.html` are written
- **AND** the Debug tool window no longer shows the run as paused while it ends

#### Scenario: Stop a running test

- **WHEN** a test that runs `Sleep    30s` is started with Run and the user presses Stop once
- **THEN** the run ends within a few seconds, the test fails with "Execution terminated by signal", and `output.xml`, `log.html` and `report.html` are written

#### Scenario: Rerun a paused debug session

- **WHEN** a debug session is paused at a breakpoint and the user reruns it
- **THEN** the paused run ends gracefully and the new run starts without the user killing the old process

### Requirement: While a stopped run is ending

While the debugger handles the request to end a stopped run, the plugin SHALL NOT send a signal to the process. If the debugger is not connected, or does not confirm the request within five seconds, the plugin SHALL interrupt the process instead. A second Stop while the run is ending SHALL kill the process. Once a paused run continues towards its end, the debug session SHALL no longer show it as paused.

#### Scenario: Debugger does not confirm

- **WHEN** the user stops a run whose debugger connection is not established, or whose debugger does not confirm the stop request within five seconds
- **THEN** the plugin interrupts the process, as Stop did before this change

#### Scenario: Kill a run that is ending

- **WHEN** the user presses Stop again while a stopped run is still executing its teardowns
- **THEN** the process is killed

### Requirement: Concurrent Robot Framework runs use separate debugger ports

Every Robot Framework Run and Debug session SHALL connect to its RobotCode debugger through a port of its own, chosen when the run starts instead of a fixed preferred port, and SHALL pass that port to robotcode explicitly. Runs started at the same time SHALL NOT connect to each other's debugger.

#### Scenario: Compound configuration

- **WHEN** a compound run configuration starts two Robot Framework configurations at the same time
- **THEN** the two runs use different debugger ports, and each run's test results are complete

#### Scenario: Multiple instances

- **WHEN** a Robot Framework configuration with "Allow multiple instances" is started a second time while its first run is still running
- **THEN** both runs complete, each with its own results
