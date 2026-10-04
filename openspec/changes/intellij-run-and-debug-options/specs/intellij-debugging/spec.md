# Spec Delta

## ADDED Requirements

### Requirement: Stop on entry

When a run configuration has stop on entry switched on and is started with Debug, the debug session SHALL pause when the run starts its top-level suite, before any test or task runs, and Resume SHALL continue the run. A run started with Run SHALL NOT pause.

#### Scenario: Debug with stop on entry

- **WHEN** stop on entry is on and the user starts a configuration of the test project with Debug, without breakpoints
- **THEN** the session pauses before the first test runs and shows the top-level suite in the call stack, and after Resume all tests run to the end

#### Scenario: Run with stop on entry

- **WHEN** stop on entry is on and the user starts the same configuration with Run
- **THEN** the run does not pause

### Requirement: Debugger output options

The output of a Robot Framework run SHALL contain what the effective debugger output options ask the debugger to send: Robot Framework's messages when messages are on, log messages unless log messages are off, and a timestamp on these lines when timestamps are on. This SHALL apply to runs started with Run and with Debug.

#### Scenario: Timestamps

- **WHEN** timestamps are on and a test executes `Log    hello`
- **THEN** the line with `hello` in the run's output starts with a timestamp

#### Scenario: Log messages off

- **WHEN** log messages are off and a test executes `Log    hello`
- **THEN** the run's output contains no line with `hello` from the debugger

### Requirement: Connection timeout

The plugin SHALL wait for the connection to the debugger of a run as long as the run configuration's connection timeout allows, or 15 seconds when it sets none, before it reports that the connection failed.

#### Scenario: Slow start with a raised timeout

- **WHEN** the launch wrapper delays the start of `robotcode` by 20 seconds and the configuration's connection timeout is 30 seconds
- **THEN** the run connects and its tests run

#### Scenario: Slow start with the default timeout

- **WHEN** the launch wrapper delays the start of `robotcode` by 20 seconds and the configuration sets no connection timeout
- **THEN** the run ends with a message that the debugger did not connect
