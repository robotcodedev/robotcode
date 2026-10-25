## ADDED Requirements

### Requirement: A selected profile that does not exist stops the start

When the folder's `robotcode.profiles` names a profile or pattern that selects no profile of the folder's configuration, the command SHALL show the error notification that appears for these names after the start of the folder's language server, with **Remove from Selection** and **Select Configuration Profiles**, and SHALL NOT open a terminal.

#### Scenario: Mistyped profile in the folder settings

- **WHEN** the folder settings set `robotcode.profiles` to `["typo"]`, the folder's `robot.toml` defines no profile `typo`, and the user runs the command
- **THEN** an error notification names `typo` and the folder, with **Remove from Selection** and **Select Configuration Profiles**, and no terminal opens

#### Scenario: Selection fixed

- **WHEN** the user clicks **Remove from Selection** in that notification and runs the command again
- **THEN** the REPL starts, without `-p typo`
