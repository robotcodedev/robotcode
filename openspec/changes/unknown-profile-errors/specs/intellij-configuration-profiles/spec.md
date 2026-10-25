## ADDED Requirements

### Requirement: A selected profile that does not exist is reported

When the language server has started and the project's selection names a profile or pattern that selects no profile of `robot.toml`, the plugin SHALL show an error notification that names them, with the actions "Remove from Selection" and "Select Configuration Profiles...", once per start of the language server. "Remove from Selection" SHALL remove these names from the selection, which restarts the language server and the discovery as a change on the General page does.

#### Scenario: Profile renamed in robot.toml

- **WHEN** `dev` is selected and `robot.toml` renames it to `development`
- **THEN** after the language server has started again, an error notification names `dev`, with "Remove from Selection" and "Select Configuration Profiles..."

#### Scenario: Remove from Selection

- **WHEN** the user clicks "Remove from Selection" in that notification
- **THEN** the selection no longer contains `dev`, the language server starts again without `-p dev`, and the run markers of the tests come back

#### Scenario: Valid selection

- **WHEN** every selected name selects a profile of `robot.toml`
- **THEN** no notification about the selection appears

### Requirement: The notification follows the selection

The notification SHALL name only names that the project's selection contains, and it SHALL expire once every selected name selects a profile again.

#### Scenario: Selection valid again

- **WHEN** the notification names `dev`, and `robot.toml` defines `dev` again
- **THEN** after the language server has started again, the notification is gone

#### Scenario: Profile in the extra arguments

- **WHEN** the extra arguments of the project's RobotCode settings contain `-p typo`, `dev` is selected, and `robot.toml` defines `dev` but no `typo`
- **THEN** no notification about the selection appears

## MODIFIED Requirements

### Requirement: Profiles that no longer exist

When the profile list opens, every selected name or pattern that `robotcode profiles list` reports as selecting no profile SHALL leave the selection at once, also when the user then cancels the list, and the list SHALL name them. Opened from the General page or from the editor of a run configuration, they SHALL leave the choice shown there, which Apply stores. Patterns and hidden profiles that select a profile SHALL stay. Nothing SHALL be removed when the list cannot be read, so that a selection is not lost.

#### Scenario: Renamed profile

- **WHEN** `dev` is selected, `robot.toml` renames it to `development`, and the user opens the list from the Tools menu and cancels it
- **THEN** the list said that `dev` was removed because `robot.toml` no longer defines it, the selection no longer contains `dev`, and the language server restarts without `-p dev`

#### Scenario: Renamed profile of a run configuration

- **WHEN** a configuration's choice is "Custom" with `dev`, `robot.toml` renames `dev` to `development`, and the user opens the list with "Select..." in the configuration's editor and cancels it
- **THEN** the list said that `dev` was removed, the editor no longer shows `dev`, and applying the configuration stores its names without `dev`

#### Scenario: Pattern in the selection

- **WHEN** `ci-*` and `typo` are selected, `robot.toml` defines `ci-linux` and `ci-win`, and the user opens the list from the Tools menu
- **THEN** only `typo` leaves the selection, and the list names only `typo`
