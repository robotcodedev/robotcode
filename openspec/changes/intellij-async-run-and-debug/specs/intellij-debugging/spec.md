# Spec Delta

## ADDED Requirements

### Requirement: Run and Debug do not block the user interface

Starting a Robot Framework Run or Debug session, and every debugger action, SHALL NOT block the IDE's user interface while the plugin waits for the process or the RobotCode debugger. Debugger actions are stepping, resuming, pausing, Run to Cursor, evaluating, computing frames and variables, and adding, changing or removing breakpoints. Every wait for the debugger SHALL be bounded, with a bound longer than the debugger's own limit for a keyword evaluation, so that an evaluation the debugger is still working on is not abandoned by the plugin.

#### Scenario: Evaluate a slow keyword

- **WHEN** the run is paused and the user evaluates `Sleep    5s` in the Evaluate dialog
- **THEN** the IDE stays responsive during the five seconds, and the dialog shows the result afterwards

#### Scenario: Start a run

- **WHEN** the user starts a test from the gutter with Run or Debug
- **THEN** the IDE's user interface is not blocked while the plugin starts the process and connects to the debugger

#### Scenario: Change a breakpoint while paused

- **WHEN** the run is paused and the user disables or enables a breakpoint
- **THEN** the IDE's user interface is not blocked while the change is sent to the debugger

### Requirement: A debugger that does not connect is reported

If the RobotCode debugger of a run does not accept the connection within 15 seconds while the process is running, the plugin SHALL write a message to the run's console and end the process. If the process ends before the connection was made, the run SHALL end with the process's exit code. In both cases the run's test results SHALL end, and the plugin SHALL NOT report an IDE error.

#### Scenario: Process ends before the debugger listens

- **WHEN** the Robot Framework process of a Debug session is killed before its debugger accepts connections
- **THEN** the console shows the exit code, the test results do not stay at "Running tests…", and no "IDE error occurred" notification appears

#### Scenario: Debugger never accepts the connection

- **WHEN** the process of a run is alive but its debugger does not accept the connection within 15 seconds
- **THEN** the console says that the debugger did not accept the connection, the process is ended, and no "IDE error occurred" notification appears

### Requirement: Evaluation contexts and errors

Evaluations from the Evaluate dialog and from the inline evaluation field SHALL use the debugger's REPL semantics: a single variable shows its value, anything else runs as a keyword call. Watches SHALL be evaluated as expressions: they SHALL NOT run keywords, and a watch on an unknown variable SHALL show `<undefined>`. When the debugger answers an evaluation with an error, the IDE SHALL show the debugger's error message for that evaluation and SHALL NOT report an IDE error.

#### Scenario: Watches are expressions

- **WHEN** the watches `1 + 2`, `${UNKNOWN}` and `Log    watch-side-effect` exist and the run stops twice
- **THEN** the first watch shows `3`, the second shows `<undefined>`, the third shows the debugger's error message, and `watch-side-effect` is never logged

#### Scenario: Keyword call in the Evaluate dialog

- **WHEN** the run is paused and the user evaluates `Catenate    a    b` in the Evaluate dialog
- **THEN** the dialog shows `a b`

#### Scenario: Error message

- **WHEN** the run is paused and the user evaluates `1 + 2` in the Evaluate dialog
- **THEN** the dialog shows the debugger's message that no keyword with the name `1 + 2` was found, and no "IDE error occurred" notification appears
