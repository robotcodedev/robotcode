# Spec Delta

## ADDED Requirements

### Requirement: Debugging a run with a WSL interpreter

When a Robot Framework run configuration whose interpreter is a WSL interpreter is started with Debug, the session SHALL behave as with a local interpreter. The run SHALL stop at the enabled breakpoints that the user set in the IDE; the frames of the call stack SHALL open the files the IDE shows, at the right lines; stepping, Run to Cursor, resuming and evaluating SHALL work.

#### Scenario: Breakpoint in a suite

- **WHEN** a line breakpoint is set on a keyword call in a suite of a project inside the distribution "Ubuntu", and the test is started with Debug
- **THEN** the run stops at the breakpoint, and the top frame opens that suite below `\\wsl.localhost\Ubuntu\` at the breakpoint's line

#### Scenario: Breakpoint in a resource file

- **WHEN** a breakpoint is set in a keyword of a resource file that the test calls
- **THEN** the run stops there, and Step Over and Resume then continue the run to its end

#### Scenario: Project on a Windows drive

- **WHEN** a project in `C:\work\robot-project` uses a WSL interpreter and a breakpoint is set in one of its suites
- **THEN** the run stops at the breakpoint, and the frame opens the suite below `C:\work\robot-project`

### Requirement: Stopping a debug run with a WSL interpreter

Stop SHALL end a debug run with a WSL interpreter gracefully, also while it is paused, so that Robot Framework writes its output, log and report files.

#### Scenario: Stop while paused

- **WHEN** the run is paused at a breakpoint and the user presses Stop once
- **THEN** the robot process inside the distribution ends, and the output, log and report files of the run are written
