# Spec Delta

## ADDED Requirements

### Requirement: Robot settings are combined with every run

At the start of every run, the plugin SHALL combine the settings of the "Robot" page with the configuration's Robot Framework options:

- Python path entries, variable files and robot arguments: the values of the "Robot" page first, then the configuration's;
- variables: both, and the configuration's value wins for a name that both set.

#### Scenario: Variable set in both places

- **WHEN** "Variables" on the "Robot" page sets `NAME` to `1`, a configuration sets it to `2`, and the configuration runs a test that executes `Log    ${NAME}`
- **THEN** the log of the run contains `2`

#### Scenario: Python path in both places

- **WHEN** "Python path" on the "Robot" page is `libs` and the configuration's Python path is `more_libs`
- **THEN** the run passes `-P libs` before `-P more_libs`

### Requirement: Environment, output directory and languages of a run

At the start of every run, the plugin SHALL place the environment variables of the "Robot" page below the configuration's environment variables and `.env` files, which win for a name that both set, and above the environment the run inherits. For the output directory and the languages, it SHALL use the configuration's value when it sets one, otherwise the value of the "Robot" page.

#### Scenario: Environment variable in both places

- **WHEN** "Env" on the "Robot" page sets `STAGE=dev`, the configuration sets `STAGE=ci`, and a test executes `Log    %{STAGE}`
- **THEN** the log of the run contains `ci`, and without the configuration's variable it contains `dev`

### Requirement: Robot settings are not copied into configurations

The plugin SHALL NOT copy values of the "Robot" page into configurations, so a changed setting reaches existing and temporary configurations at their next run, and no value SHALL be passed twice. The console of a run SHALL show the command line the run started with.

#### Scenario: Existing temporary configuration

- **WHEN** a test was run from the gutter, the user then adds the variable `NAME` with the value `x` on the "Robot" page and runs the same temporary configuration again
- **THEN** the run passes `-v NAME:x` without the configuration being created again

### Requirement: Runs use the paths of the Robot settings

Every run SHALL pass `-dp` for each entry of "Paths" on the "Robot" page, or `-dp .` when there is none, the same arguments that discovery passes. The files and folders of a configuration's target SHALL stay positional paths, which Robot Framework runs instead of the default paths.

#### Scenario: Paths of the Robot page in a gutter run

- **WHEN** "Paths" on the "Robot" page is `tests` and the user runs a test from the gutter
- **THEN** the run's command line contains `-dp tests` and no `-dp .`, and the test runs

#### Scenario: Target with its own folder

- **WHEN** "Paths" on the "Robot" page is `tests` and a configuration's "Files and folders" target is `examples`
- **THEN** the run passes `-dp tests` and `examples` as its path, and runs the suites below `examples`

## MODIFIED Requirements

### Requirement: Mode, language and dry run options

A Robot Framework run configuration SHALL also offer, behind "Modify options", these options and SHALL pass each one that is set:

- the mode: "Inherit" takes "Mode" of the "Robot" settings page, which passes nothing while it is "Default"; "RPA" passes `--rpa`, "Test automation" passes `--norpa`; new configurations use "Inherit";
- languages, each as `--language`, on every Robot Framework version;
- dry run as `--dryrun`.

#### Scenario: Mode

- **WHEN** the mode is "Inherit" and "Mode" on the "Robot" page is "Default"
- **THEN** the run passes neither `--rpa` nor `--norpa`, and when the user switches the configuration's mode to "RPA", the next run passes `--rpa`

#### Scenario: Mode from the Robot page

- **WHEN** "Mode" on the "Robot" page is "RPA" and the configuration's mode is "Inherit"
- **THEN** the run passes `--rpa`, and when the configuration's mode is "Test automation", it passes `--norpa` and no `--rpa`

#### Scenario: Dry run

- **WHEN** dry run is on and the user runs a test that executes `Log    executed`
- **THEN** the run passes `--dryrun`, and the log of the run contains no message `executed`
