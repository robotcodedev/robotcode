# Spec Delta

## MODIFIED Requirements

### Requirement: Exception breakpoints per kind of failure

The IDE SHALL show the Robot Framework exception breakpoints as one group in the Breakpoints dialog. The group SHALL always hold "Uncaught Failed Keywords", enabled by default, which SHALL keep the enabled state and settings stored for the exception breakpoint of earlier plugin versions. The user SHALL be able to add "Failed Keywords", "Failed Tests" and "Failed Suites" to the group, each at most once and with settings of its own, and to remove them again.

#### Scenario: Setting stored by an earlier version

- **WHEN** a project's workspace stores the former "Any Exception" breakpoint as disabled
- **THEN** "Uncaught Failed Keywords" is shown disabled, and the debugger does not stop at uncaught keyword failures

#### Scenario: One group

- **WHEN** the user opens the Breakpoints dialog in a project that has stored no Robot Framework exception breakpoints
- **THEN** the dialog shows one "Robot Framework Exception Breakpoints" group, which holds "Uncaught Failed Keywords", enabled, and offers no way to remove it

#### Scenario: Add a kind

- **WHEN** the user adds "Failed Tests" with the dialog's add button
- **THEN** the group holds "Failed Tests" as an enabled breakpoint of its own, and the add button then offers only "Failed Keywords" and "Failed Suites"

#### Scenario: Remove an added kind

- **WHEN** the user removes "Failed Tests" from the group and starts a failing test with Debug
- **THEN** the run does not stop when the test fails, and the add button offers "Failed Tests" again

#### Scenario: Added kinds survive a restart

- **WHEN** the user has added "Failed Tests" with the suspend policy None and restarts the IDE
- **THEN** the group still holds "Failed Tests" with the suspend policy None
