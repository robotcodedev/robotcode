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

### Requirement: Python debugging of a run with a WSL interpreter

When a Robot Framework run configuration with a WSL interpreter is started with Debug and its effective "Attach Python" is on, PyCharm's Python debugger SHALL debug the run as with a local interpreter: Python breakpoints set in the IDE's files SHALL stop the run inside the distribution, the Python frames SHALL open the files the IDE shows, and Stop in either session SHALL end the run gracefully.

#### Scenario: Python breakpoint in a library inside the distribution

- **WHEN** a project inside the distribution "Ubuntu" uses a WSL interpreter with "Attach Python" on, a Python line breakpoint is set in a library keyword that a test calls, and the test is started with Debug
- **THEN** the run stops at the breakpoint in the tab of the Python session, and its top frame opens the library below `\\wsl.localhost\Ubuntu\` at the breakpoint's line

#### Scenario: Python breakpoint in a project on a Windows drive

- **WHEN** a project in `C:\work\robot-project` uses a WSL interpreter with "Attach Python" on and a Python breakpoint is set in one of its libraries
- **THEN** the run stops at the breakpoint, and the frame opens the library below `C:\work\robot-project`

#### Scenario: Stop while paused in Python code

- **WHEN** the run is paused at a Python breakpoint and the user presses Stop once in either tab
- **THEN** the robot process inside the distribution ends, the stopped test fails, and the output, log and report files of the run are written

#### Scenario: Python debugging in mirrored networking

- **WHEN** WSL runs in mirrored networking mode and the user debugs a test with a WSL interpreter and "Attach Python" on
- **THEN** the run stops at a Python breakpoint in a library as in WSL's default networking mode
