# vscode-configuration-profiles Specification

## Purpose

Defines what the VS Code extension does when its selection of configuration profiles in `robotcode.profiles` names a profile that the configuration of a workspace folder does not define.

## Requirements

### Requirement: A selected profile that does not exist is reported

When the language server of a workspace folder has started, and the folder's `robotcode.profiles` names a profile or pattern that selects no profile of the folder's configuration, the extension SHALL show an error notification that names these names and the folder, with the actions **Remove from Selection** and **Select Configuration Profiles**. It SHALL show it once per start of the folder's language server.

#### Scenario: Mistyped profile in the folder settings

- **WHEN** the folder settings set `robotcode.profiles` to `["typo"]` and the folder's `robot.toml` defines no profile `typo`
- **THEN** after the language server has started, an error notification names `typo` and the folder, with **Remove from Selection** and **Select Configuration Profiles**

#### Scenario: Valid selection

- **WHEN** every name in `robotcode.profiles` selects a profile of the folder's configuration
- **THEN** no notification about the selection appears

### Requirement: Only names of the selection are reported

The extension SHALL report only names that the folder's `robotcode.profiles` contains. A name from elsewhere, such as a `-p` in `robotcode.extraArgs`, SHALL NOT be reported as a name of the selection.

#### Scenario: Profile in the extra arguments

- **WHEN** `robotcode.extraArgs` is `["-p", "typo"]`, `robotcode.profiles` is `["ci"]`, and the folder's `robot.toml` defines `ci` but no `typo`
- **THEN** no notification about the selection appears

### Requirement: Remove from Selection removes the names for the folder

**Remove from Selection** SHALL set the folder's `robotcode.profiles` to the selection without the reported names, at the scope of the workspace folder, as **RobotCode: Select Configuration Profiles** does. When the folder settings cannot be written, the extension SHALL show an error message.

#### Scenario: Remove from Selection

- **WHEN** the user clicks **Remove from Selection** in the notification about `typo`
- **THEN** the folder's `robotcode.profiles` no longer contains `typo`, the language server starts again without `-p typo`, and the tests of the folder appear in the Test Explorer

#### Scenario: Profile in the user settings

- **WHEN** the user settings set `robotcode.profiles` to `["ci"]`, one workspace folder defines `ci` and another does not, and the user clicks **Remove from Selection** in the notification for the other folder
- **THEN** only that folder's settings get a `robotcode.profiles` without `ci`, and the user settings stay as they were

#### Scenario: Folder settings that cannot be written

- **WHEN** the folder settings cannot be written, and the user clicks **Remove from Selection**
- **THEN** an error message says so, and the selection stays as it was

### Requirement: Select Configuration Profiles keeps the valid names

**RobotCode: Select Configuration Profiles** SHALL remove from the folder's selection only the names that `robotcode profiles list` reports as selecting no profile, and SHALL store the names of the chosen profiles, whatever their length.

#### Scenario: Pattern in the selection

- **WHEN** `robotcode.profiles` is `["ci-*", "typo"]`, the folder's `robot.toml` defines `ci-linux` and `ci-win`, and the user runs the command
- **THEN** only `typo` leaves the selection, the message names only `typo`, and the list shows `ci-linux` and `ci-win` checked

#### Scenario: Long profile name

- **WHEN** the folder's `robot.toml` defines a profile with a name of 60 characters and the user chooses it in the list
- **THEN** `robotcode.profiles` contains the full name of the profile
