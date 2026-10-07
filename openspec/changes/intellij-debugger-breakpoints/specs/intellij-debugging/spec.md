# Spec Delta

## ADDED Requirements

### Requirement: Line breakpoints take effect as shown

In a debug session, the RobotCode debugger SHALL stop only at Robot Framework line breakpoints that the IDE shows as enabled and that are not muted, at the line where the IDE shows them. Adding, removing, disabling, enabling, muting, unmuting and moving a breakpoint, by dragging it or by editing the lines above it, SHALL take effect at once, also for the last breakpoint of a file and also while the run is paused.

#### Scenario: Disable the only breakpoint of a file while paused

- **WHEN** the run is paused at the only breakpoint of a file, inside a loop that reaches that line again, and the user disables the breakpoint and resumes
- **THEN** the run does not stop at that line again

#### Scenario: Remove all breakpoints while paused

- **WHEN** the run is paused at a breakpoint, the user removes every Robot Framework breakpoint and resumes
- **THEN** the run does not stop at any of the removed lines

#### Scenario: Mute breakpoints

- **WHEN** the user mutes breakpoints while the run is paused in a loop and resumes
- **THEN** the run does not stop at any line breakpoint until breakpoints are unmuted

#### Scenario: Move a breakpoint

- **WHEN** the user drags a breakpoint to another line, or inserts a line above it, and the run reaches the old line and then the new one
- **THEN** the run stops only at the line where the IDE now shows the breakpoint

### Requirement: Force actions ignore breakpoints

Force Step Over and Force Run to Cursor SHALL ignore all breakpoints until they have reached their target.

#### Scenario: Force Step Over

- **WHEN** the run is paused on a line that calls a keyword whose body has a breakpoint and the user chooses Force Step Over
- **THEN** the run stops at the next line of the current body, not at the breakpoint inside the keyword

### Requirement: Run to Cursor always continues to the target line

Run to Cursor SHALL continue the paused run and stop it at the target line, whether or not that line has a breakpoint. The temporary stop SHALL not remain in effect after the run has stopped again, at the target line or anywhere else.

#### Scenario: Target line with a breakpoint

- **WHEN** the run is paused and the user runs to the cursor on a later line that has a breakpoint
- **THEN** the run continues and stops at that line, and the session shows it as paused there

#### Scenario: Temporary stop does not remain

- **WHEN** the user runs to the cursor on a line without a breakpoint, the run stops there, and the run reaches that line again after resuming
- **THEN** the run does not stop at that line again

### Requirement: Breakpoints are in effect from the first keyword

The line breakpoints and exception breakpoints that exist when a debug session starts SHALL be in effect before Robot Framework runs its first keyword, and a stop at the first keyword SHALL pause the run.

#### Scenario: Breakpoint on the first keyword

- **WHEN** a breakpoint is set on the first keyword call of the first test and the test is started with Debug ten times in a row
- **THEN** every run stops at that breakpoint

### Requirement: Exception breakpoints per kind of failure

The IDE SHALL offer one Robot Framework exception breakpoint for each kind of failure the RobotCode debugger stops on: "Uncaught Failed Keywords", "Failed Keywords" and "Failed Suites". Only "Uncaught Failed Keywords" SHALL be enabled by default, and it SHALL keep the enabled state and settings stored for the exception breakpoint of earlier plugin versions.

#### Scenario: Setting stored by an earlier version

- **WHEN** a project's workspace stores the former "Any Exception" breakpoint as disabled
- **THEN** "Uncaught Failed Keywords" is shown disabled, and the debugger does not stop at uncaught keyword failures

### Requirement: What each exception breakpoint stops at

"Uncaught Failed Keywords" SHALL stop at keyword failures that are not handled by `TRY/EXCEPT` or by BuiltIn's error-handling keywords, "Failed Keywords" at every keyword failure, and "Failed Suites" when a suite fails. The debugger SHALL stop at a failure only while the matching exception breakpoint is enabled and breakpoints are not muted.

#### Scenario: All exception breakpoints disabled

- **WHEN** all Robot Framework exception breakpoints are disabled and a failing test is started with Debug
- **THEN** the test fails without the run stopping, and the run ends normally

#### Scenario: Failed keywords

- **WHEN** "Failed Keywords" is enabled and a test runs `Fail    expected` inside `TRY/EXCEPT`
- **THEN** the run stops after that keyword and shows the failure message `expected`

#### Scenario: Caught failure with uncaught failed keywords

- **WHEN** only "Uncaught Failed Keywords" is enabled and a test runs `Fail    expected` inside `TRY/EXCEPT` and inside `Run Keyword And Ignore Error`
- **THEN** the run does not stop at these failures

#### Scenario: Failed suites

- **WHEN** only "Failed Suites" is enabled and a test of a suite file fails
- **THEN** the run stops when that suite ends and shows the suite's failure message

### Requirement: Stops at exception breakpoints

A stop at an exception breakpoint SHALL apply that breakpoint's suspend policy and show the failure message. A failure stop that matches no enabled exception breakpoint SHALL be shown as paused instead of leaving the run waiting unseen.

#### Scenario: Suspend policy None

- **WHEN** "Uncaught Failed Keywords" is enabled with the suspend policy None and a failing test is started with Debug
- **THEN** the run finishes without a visible stop and the IDE logs no error

### Requirement: Robot Framework line breakpoints only in Robot Framework files

The plugin SHALL offer Robot Framework line breakpoints only in Robot Framework suite and resource files. In all other files, toggling a breakpoint SHALL create the breakpoint type that the IDE would create without the plugin, or none.

#### Scenario: Python file

- **WHEN** the user clicks the gutter of a line in a Python file
- **THEN** a Python line breakpoint is created, not a Robot Framework breakpoint

#### Scenario: Plain text file

- **WHEN** the user clicks the gutter of a line in a `.txt` or `.toml` file
- **THEN** no Robot Framework breakpoint is created
