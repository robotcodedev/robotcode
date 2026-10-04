# Spec Delta

## Purpose

Defines how the IntelliJ plugin turns the events of a Robot Framework run into the results shown in the run window: the results tree, test statuses and failure details, the output of each test, and the Robot Framework log messages of the run.

## ADDED Requirements

### Requirement: Robot Framework's log messages appear in a "Robot Log" tab

The run window of every Robot Framework run SHALL have a "Robot Log" tab next to its console. The tab SHALL list the log messages that the RobotCode debugger sends for the run, in the order they were logged. Each message SHALL show its level unless the level is `INFO`, and SHALL be colored by its level. A message for which the debugger reports the file and line it was logged from SHALL end with a link that opens the file at that line.

#### Scenario: A message of `Log`

- **WHEN** a test that calls `Log    should not in console` is run
- **THEN** the "Robot Log" tab shows `should not in console`

#### Scenario: A warning

- **WHEN** a test logs `a warning` with level `WARN`
- **THEN** the "Robot Log" tab shows `[ WARN ] a warning` in the color of warnings

#### Scenario: Opening the location of a message

- **WHEN** the user clicks the link at the end of `should not in console` in the "Robot Log" tab
- **THEN** the editor opens the test's file at the line of that `Log` call

#### Scenario: Order across tests

- **WHEN** the tests `First` and `Second` each log a message and are run in that order
- **THEN** the "Robot Log" tab lists the message of `First` before the message of `Second`

### Requirement: The console shows what a terminal run shows

The run console SHALL show the output of the Robot Framework process as a terminal run of the same suite shows it. It SHALL NOT show the log messages that the "Robot Log" tab lists, neither for the whole run nor in the output of a test.

#### Scenario: `Log` and `Log To Console`

- **WHEN** a test calls `Log    should not in console` and `Log To Console    show in console` and is run
- **THEN** the console shows `show in console` and does not show `should not in console`, also when the test is selected in the results tree

#### Scenario: Warnings in both places

- **WHEN** a test logs `a warning` with level `WARN` and is run
- **THEN** the console shows the line `[ WARN ] a warning` that Robot Framework writes to its console, and the "Robot Log" tab lists the message as well

#### Scenario: Trace level

- **WHEN** `robot.toml` sets `log-level = "TRACE"` and a test is run
- **THEN** the arguments and return values that Robot Framework logs at `TRACE` level appear in the "Robot Log" tab and not in the console

### Requirement: Debug sessions show the "Robot Log" tab

A Debug session of a Robot Framework run configuration SHALL show the same "Robot Log" tab next to its Console and Debugger tabs, with the log messages of the debugged run. Its Console tab SHALL follow the same rule as the console of a run.

#### Scenario: Log message while debugging

- **WHEN** a test that calls `Log    should not in console` is debugged and stops at a breakpoint on a later line of the test
- **THEN** the "Robot Log" tab of the debug session shows `should not in console`, and its Console tab does not
