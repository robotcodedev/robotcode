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

The output of a Robot Framework run SHALL contain what the effective debugger output options ask the debugger to send: Robot Framework's messages when "Output messages" is on, log messages unless "Output log" is off, and a timestamp on these lines when "Output timestamps" is on. This SHALL apply to runs started with Run and with Debug.

#### Scenario: Timestamps

- **WHEN** "Output timestamps" is on and a test executes `Log    hello`
- **THEN** the line with `hello` in the run's output starts with a timestamp

#### Scenario: Output log off

- **WHEN** "Output log" is off and a test executes `Log    hello`
- **THEN** the run's output contains no line with `hello` from the debugger

## MODIFIED Requirements

### Requirement: A debugger that does not connect is reported

If the RobotCode debugger of a run does not accept the connection within the run configuration's connection timeout, or 15 seconds when it sets none, while the process is running, the plugin SHALL write a message to the run's console and end the process. If the process ends before the connection was made, the run SHALL end with the process's exit code. In both cases the run's test results SHALL end, and the plugin SHALL NOT report an IDE error.

#### Scenario: Process ends before the debugger listens

- **WHEN** the Robot Framework process of a Debug session is killed before its debugger accepts connections
- **THEN** the console shows the exit code, the test results do not stay at "Running tests…", and no "IDE error occurred" notification appears

#### Scenario: Debugger never accepts the connection

- **WHEN** the process of a run is alive but its debugger does not accept the connection within 15 seconds, and the run configuration sets no connection timeout
- **THEN** the console says that the debugger did not accept the connection, the process is ended, and no "IDE error occurred" notification appears

#### Scenario: Slow start with a raised timeout

- **WHEN** the launch wrapper delays the start of `robotcode` by 20 seconds and the configuration's connection timeout is 30 seconds
- **THEN** the run connects and its tests run
