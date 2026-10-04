# Spec Delta

## Purpose

Defines how users of the IntelliJ plugin select `robot.toml` configuration profiles, and how the selected profiles reach the language server, test discovery and runs.

## ADDED Requirements

### Requirement: Profiles per run configuration

Every Robot Framework run configuration SHALL have one of three profile choices: "Project selection", "Default profiles of robot.toml", or "Custom" with a list of profile names. New configurations and the configuration template SHALL start with "Project selection". At the start of every run, the plugin SHALL resolve the choice and pass `-p` for each resolved profile:

- "Project selection": the profiles selected for the project at that moment;
- "Default profiles of robot.toml": none, so that `default-profiles` applies;
- "Custom": each listed profile, and none when the list is empty.

#### Scenario: Custom profile instead of the project selection

- **WHEN** the project selection is `dev`, a configuration's choice is "Custom" with `ci`, and the configuration runs a test that logs a variable that only profile `ci` sets
- **THEN** the run's command line contains `-p ci` and no `-p dev`, and the log shows the value from profile `ci`

#### Scenario: Gutter runs follow the project selection

- **WHEN** the project selection is `dev` and the template is unchanged, and the user runs a test from the gutter
- **THEN** the run's command line contains `-p dev`

#### Scenario: Changed project selection reaches an existing configuration

- **WHEN** a saved configuration's choice is "Project selection", and the user changes the project selection from `dev` to `ci` and runs the configuration without editing it
- **THEN** the run's command line contains `-p ci`

#### Scenario: Default profiles of robot.toml

- **WHEN** the project selection is `dev`, `robot.toml` sets `default-profiles = ["ci"]`, and a configuration's choice is "Default profiles of robot.toml"
- **THEN** the run's command line contains no `-p`, and the run uses the values of profile `ci`

### Requirement: Warning for profiles that no longer exist

When the custom profiles of a configuration include a name that the last read profile list of `robot.toml` does not contain, the run configuration dialog and the run widget SHALL show a warning that names it. The check SHALL NOT start a process, and the warning SHALL NOT prevent the run.

#### Scenario: Renamed profile

- **WHEN** a configuration's choice is "Custom" with `dev`, and `robot.toml` renames `dev` to `development`
- **THEN** the run configuration dialog shows a warning that `robot.toml` no longer defines `dev`, and the configuration can still be run

### Requirement: Run or debug once with a chosen profile

"Run with Profile..." and "Debug with Profile..." SHALL be offered in the context menus of the editor and the Project view and in the gutter menu wherever the plugin offers to run a Robot Framework test, task, suite or folder. Each SHALL offer the profiles that `robot.toml` defines, without hidden profiles, and then run or debug what a context run of the same place runs, once, with `-p` for the chosen profile only. The tab of the run SHALL name the chosen profile. Saved and temporary configurations SHALL stay unchanged, and the run SHALL NOT add a configuration to the run widget.

#### Scenario: Run a test once with a profile

- **WHEN** the project selection is `dev`, a saved configuration runs "First Test Passes", and the user chooses Run with Profile... > `ci` in the gutter menu of that test
- **THEN** the test runs with `-p ci` in a tab whose title names `ci`, and the saved configuration still has its own profile choice

#### Scenario: Debug a suite once with a profile

- **WHEN** the user chooses Debug with Profile... > `ci` in the Project view context menu of `tests/sample.robot`, which holds a Robot Framework breakpoint
- **THEN** the RobotCode debugger stops at the breakpoint in a run with `-p ci`

#### Scenario: Later gutter runs follow the project again

- **WHEN** the user ran a test once with `ci` and then runs it from the gutter with Run
- **THEN** the run's command line contains the project selection, not `-p ci`

#### Scenario: Hidden profiles

- **WHEN** `robot.toml` defines the hidden profile `_base`
- **THEN** Run with Profile... and Debug with Profile... do not offer `_base`

### Requirement: The profile list stays current

The profile list offered for run configurations and for running once SHALL be read in the background without blocking the IDE, and SHALL be read again after the language server has restarted, for example after a change to `robot.toml`.

#### Scenario: New profile in robot.toml

- **WHEN** the user adds the profile `staging` to `robot.toml` and the language server restarts because of the change
- **THEN** Run with Profile... offers `staging`, without an IDE restart
