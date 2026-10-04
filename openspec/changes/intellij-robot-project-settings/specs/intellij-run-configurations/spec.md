# Spec Delta

## Purpose

Defines what a Robot Framework run configuration of the IntelliJ plugin runs, how it is stored, edited, shared and reused, and which arguments its runs pass to `robotcode` and Robot Framework.

## ADDED Requirements

### Requirement: Project settings are combined with every run

At the start of every run, the plugin SHALL combine the project's Robot Framework environment and run options with the configuration's Robot Framework options:

- Python path entries, variable files and robot arguments: the project's values first, then the configuration's;
- variables: both, and the configuration's value wins for a name that both set;
- environment variables: the project's below the configuration's environment variables and `.env` files, which win for a name that both set, and above the environment the run inherits;
- mode, output directory and languages: the configuration's value when it sets one, otherwise the project's.

The plugin SHALL NOT copy project values into configurations, so a changed setting reaches existing and temporary configurations at their next run, and no value SHALL be passed twice. The console of a run SHALL show the command line the run started with.

#### Scenario: Variable set in both places

- **WHEN** the project sets the variable `NAME` to `1`, a configuration sets it to `2`, and the configuration runs a test that executes `Log    ${NAME}`
- **THEN** the log of the run contains `2`

#### Scenario: Python path in both places

- **WHEN** the project's Python path is `libs` and the configuration's Robot Framework Python path is `more_libs`
- **THEN** the run passes `-P libs` before `-P more_libs`

#### Scenario: Mode from the project

- **WHEN** the project's mode is "RPA" and the configuration's mode is "Inherit"
- **THEN** the run passes `--rpa`, and when the configuration's mode is "Test automation", it passes `--norpa` and no `--rpa`

#### Scenario: Environment variable in both places

- **WHEN** the project sets the environment variable `STAGE=dev`, the configuration sets `STAGE=ci`, and a test executes `Log    %{STAGE}`
- **THEN** the log of the run contains `ci`, and without the configuration's variable it contains `dev`

#### Scenario: Existing temporary configuration

- **WHEN** a test was run from the gutter, the user then adds the variable `NAME` with the value `x` to the project settings and runs the same temporary configuration again
- **THEN** the run passes `-v NAME:x` without the configuration being created again

### Requirement: Default paths per configuration

A Robot Framework run configuration SHALL offer "Default paths" under "Modify options", a list of files and folders. A run SHALL pass `-dp` for each default path of the configuration followed by each default path of the project's run options, or `-dp .` when neither sets any. The editor SHALL say that default paths are used only when `robot.toml` sets no paths and the target names no files or folders. The default paths SHALL be stored with the configuration like its other options.

#### Scenario: Project default paths in a gutter run

- **WHEN** the project's default paths are `tests` and the user runs a test from the gutter
- **THEN** the run's command line contains `-dp tests` and no `-dp .`

#### Scenario: Configuration and project default paths

- **WHEN** the configuration's default paths are `smoke` and the project's are `tests`
- **THEN** the run passes `-dp smoke -dp tests`
