# Spec Delta

## Purpose

Defines how users of the IntelliJ plugin select `robot.toml` configuration profiles, and how the selected profiles reach the language server, test discovery and runs.

## ADDED Requirements

### Requirement: Profile selection on the settings page

The "Robot Framework" settings page SHALL show "Configuration profiles": the names of the selected profiles, or, when none are selected, that the `default-profiles` of `robot.toml` apply. A "Select..." button SHALL open the profile list. A choice made there SHALL take effect when the user applies the page: the selection is stored, the language server restarts, and test discovery runs again.

#### Scenario: Selecting a profile on the settings page

- **WHEN** the user opens the profile list from the settings page, checks `dev`, confirms and applies
- **THEN** the page shows `dev`, the language server restarts with `-p dev`, and test discovery runs again with `-p dev`

#### Scenario: No selection

- **WHEN** no profile is selected
- **THEN** the page says that the `default-profiles` of `robot.toml` apply

### Requirement: Select Configuration Profiles action

Tools | RobotCode | Select Configuration Profiles... SHALL open the same profile list. Confirming the list SHALL store the selection at once, restart the language server and run test discovery again. The action SHALL be disabled when no project is open.

#### Scenario: Selecting a profile from the Tools menu

- **WHEN** the user chooses Tools | RobotCode | Select Configuration Profiles..., checks `ci` and confirms
- **THEN** the selection is `ci`, the language server restarts with `-p ci`, and test discovery runs again with `-p ci`

### Requirement: The profile list

The profile list SHALL be read with `robotcode profiles list` in the background, without blocking the IDE, with the current selection passed as `-p`. The profile list SHALL offer every profile that `robotcode` lists without its option for hidden profiles, with the profile's description.

#### Scenario: Hidden profiles

- **WHEN** `robot.toml` defines the profiles `dev`, `ci` and the hidden profile `_base`
- **THEN** the list offers `dev` and `ci` with their descriptions, and not `_base`

### Requirement: Checked profiles in the profile list

The profile list SHALL check the selected profiles, or, without a selection, the profiles that `robot.toml` selects by default. Confirming the list without changing the checks while nothing is selected SHALL keep the empty selection. Unchecking every profile SHALL store an empty selection.

#### Scenario: Default profiles are checked

- **WHEN** nothing is selected and `robot.toml` sets `default-profiles = ["dev"]`
- **THEN** the list opens with `dev` checked, and confirming it unchanged keeps the selection empty

### Requirement: Messages and errors in the profile list

When `robotcode` reports messages instead of profiles, such as that no configuration file was found, the profile list SHALL show them; when `robotcode` fails, the list SHALL show the beginning of its error output.

#### Scenario: Project without profiles

- **WHEN** the project's `robot.toml` defines no profiles
- **THEN** the list shows the message from `robotcode` that no profiles are defined, and nothing can be checked

#### Scenario: Broken configuration file

- **WHEN** `robot.toml` contains a TOML syntax error and the user opens the list
- **THEN** the list shows the beginning of the error output of `robotcode`, and the selection stays unchanged

### Requirement: Profiles that no longer exist

When the profile list opens, it SHALL remove from the choice every selected profile that `robotcode profiles list` does not report, and SHALL name the removed profiles. It SHALL NOT remove anything when `robotcode` reported neither profiles nor messages, so that a selection is not lost when the list cannot be read.

#### Scenario: Renamed profile

- **WHEN** `dev` is selected, `robot.toml` renames it to `development`, and the user opens the list
- **THEN** the list says that `dev` was removed because `robot.toml` no longer defines it, `dev` is not checked, and confirming the list stores the selection without `dev`

### Requirement: Selected profiles reach every robotcode process

The language server, both kinds of test discovery, the profile list and runs SHALL get `-p <name>` for each selected profile, after the plugin's own global options of the `robotcode` command line. Without a selection, they SHALL get no `-p`, so that `robot.toml`'s `default-profiles` apply.

#### Scenario: Selected profile in a run

- **WHEN** `dev` is selected and the user runs a test from its gutter icon, and the test logs a variable that only profile `dev` sets
- **THEN** the run's command line contains `-p dev`, and the log shows the value from profile `dev`

#### Scenario: No selection uses default-profiles

- **WHEN** nothing is selected and `robot.toml` sets `default-profiles = ["dev"]`
- **THEN** the command lines of the language server, test discovery and runs contain no `-p`, and the run uses the values of profile `dev`

### Requirement: The selection is personal

The profile selection SHALL be stored for the current user, in the project's workspace file `.idea/workspace.xml`. It SHALL NOT be written to the shared settings file `.idea/robotcodeSettings.xml`.

#### Scenario: Selection survives a restart

- **WHEN** the user selects `dev` and restarts the IDE
- **THEN** the settings page shows `dev`, `.idea/workspace.xml` holds it, and `.idea/robotcodeSettings.xml` does not
