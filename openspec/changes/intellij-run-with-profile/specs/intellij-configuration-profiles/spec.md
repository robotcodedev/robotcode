# Spec Delta

## ADDED Requirements

### Requirement: Profiles per run configuration

Every Robot Framework run configuration SHALL have one of three profile choices: "Project selection", "Default profiles of robot.toml", or "Custom" with a list of profile names. New configurations and the configuration template SHALL start with "Project selection".

#### Scenario: Gutter runs follow the project selection

- **WHEN** the project selection is `dev` and the template is unchanged, and the user runs a test from the gutter
- **THEN** the run's command line contains `-p dev`

### Requirement: The profile choice is resolved at the start of every run

At the start of every run, the plugin SHALL resolve the profile choice of the run configuration and pass `-p` for each resolved profile:

- "Project selection": the profiles selected for the project at that moment;
- "Default profiles of robot.toml": none, so that `default-profiles` applies;
- "Custom": each listed profile, and none when the list is empty.

#### Scenario: Custom profile instead of the project selection

- **WHEN** the project selection is `dev`, a configuration's choice is "Custom" with `ci`, and the configuration runs a test that logs a variable that only profile `ci` sets
- **THEN** the run's command line contains `-p ci` and no `-p dev`, and the log shows the value from profile `ci`

#### Scenario: Changed project selection reaches an existing configuration

- **WHEN** a saved configuration's choice is "Project selection", and the user changes the project selection from `dev` to `ci` and runs the configuration without editing it
- **THEN** the run's command line contains `-p ci`

#### Scenario: Default profiles of robot.toml

- **WHEN** the project selection is `dev`, `robot.toml` sets `default-profiles = ["ci"]`, and a configuration's choice is "Default profiles of robot.toml"
- **THEN** the run's command line contains no `-p`, and the run uses the values of profile `ci`

### Requirement: Warning for profiles that no longer exist

When the custom profiles of a configuration include a name that the last read profile list of `robot.toml` does not contain, the run configuration dialog SHALL show a warning that names it, and the run widget SHALL mark the configuration's icon as it does for other problems. The check SHALL NOT start a process, and the warning SHALL NOT prevent the run.

#### Scenario: Renamed profile

- **WHEN** a configuration's choice is "Custom" with `dev`, and `robot.toml` renames `dev` to `development`
- **THEN** the run widget marks the configuration's icon, the run configuration dialog opened afterwards shows a warning that `robot.toml` no longer defines `dev`, and the configuration can still be run

### Requirement: Run or debug once with a chosen profile

"Run with Profile..." and "Debug with Profile..." SHALL be offered in the context menus of the editor and the Project view and in the gutter menu wherever the plugin offers to run a Robot Framework test, task, suite or folder. Each SHALL offer the profiles that `robot.toml` defines, without hidden profiles, and then run or debug what a context run of the same place runs, once, with `-p` for the chosen profile only.

#### Scenario: Debug a suite once with a profile

- **WHEN** the user chooses Debug with Profile... > `ci` in the Project view context menu of `tests/sample.robot`, which holds a Robot Framework breakpoint
- **THEN** the RobotCode debugger stops at the breakpoint in a run with `-p ci`

#### Scenario: Hidden profiles

- **WHEN** `robot.toml` defines the hidden profile `_base`
- **THEN** Run with Profile... and Debug with Profile... do not offer `_base`

### Requirement: A run with a chosen profile leaves the configurations unchanged

The tab of a run started with "Run with Profile..." or "Debug with Profile..." SHALL name the chosen profile. Saved and temporary configurations SHALL stay unchanged, and the run SHALL NOT add a configuration to the run widget.

#### Scenario: Run a test once with a profile

- **WHEN** the project selection is `dev`, a saved configuration runs "First Test Passes", and the user chooses Run with Profile... > `ci` in the gutter menu of that test
- **THEN** the test runs with `-p ci` in a tab whose title names `ci`, and the saved configuration still has its own profile choice

#### Scenario: Later gutter runs follow the project again

- **WHEN** the user ran a test once with `ci` and then runs it from the gutter with Run
- **THEN** the run's command line contains the project selection, not `-p ci`

### Requirement: The profile list stays current

The profiles that "Run with Profile..." and "Debug with Profile..." offer, and the list that the warning for profiles that no longer exist checks against, SHALL be read in the background without blocking the IDE, and SHALL be read again as soon as the language server has started, for example after a change to `robot.toml`.

#### Scenario: New profile in robot.toml

- **WHEN** the user adds the profile `staging` to `robot.toml` and the language server restarts because of the change
- **THEN** Run with Profile... offers `staging`, without an IDE restart

## MODIFIED Requirements

### Requirement: Profiles that no longer exist

When the profile list opens, every selected profile that `robotcode profiles list` does not report SHALL leave the selection at once, also when the user then cancels the list, and the list SHALL name them. Opened from the General page or from the editor of a run configuration, they SHALL leave the choice shown there, which Apply stores. Nothing SHALL be removed when `robotcode` reported neither profiles nor messages, so that a selection is not lost when the list cannot be read.

#### Scenario: Renamed profile

- **WHEN** `dev` is selected, `robot.toml` renames it to `development`, and the user opens the list from the Tools menu and cancels it
- **THEN** the list said that `dev` was removed because `robot.toml` no longer defines it, the selection no longer contains `dev`, and the language server restarts without `-p dev`

#### Scenario: Renamed profile of a run configuration

- **WHEN** a configuration's choice is "Custom" with `dev`, `robot.toml` renames `dev` to `development`, and the user opens the list with "Select..." in the configuration's editor and cancels it
- **THEN** the list said that `dev` was removed, the editor no longer shows `dev`, and applying the configuration stores its names without `dev`

### Requirement: Selected profiles reach every robotcode process

The language server, both kinds of test discovery, the profile list of the General page and of the Tools menu, and runs whose configuration uses "Project selection" SHALL get `-p <name>` for each selected profile, after the plugin's own global options of the `robotcode` command line. Without a selection, they SHALL get no `-p`, so that `robot.toml`'s `default-profiles` apply.

#### Scenario: Selected profile in a run

- **WHEN** `dev` is selected and the user runs a test from its gutter icon, and the test logs a variable that only profile `dev` sets
- **THEN** the run's command line contains `-p dev`, and the log shows the value from profile `dev`

#### Scenario: No selection uses default-profiles

- **WHEN** nothing is selected and `robot.toml` sets `default-profiles = ["dev"]`
- **THEN** the command lines of the language server, test discovery and runs contain no `-p`, and the run uses the values of profile `dev`
