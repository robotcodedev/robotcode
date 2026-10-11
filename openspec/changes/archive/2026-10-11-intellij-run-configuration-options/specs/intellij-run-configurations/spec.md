# Spec Delta

## Purpose

Defines what a Robot Framework run configuration of the IntelliJ plugin runs, how it is stored, edited, shared and reused, and which arguments its runs pass to `robotcode` and Robot Framework.

## ADDED Requirements

### Requirement: Robot arguments per configuration

A Robot Framework run configuration SHALL offer a "Robot arguments" field. Its text SHALL be split like a command line, with quotes grouping words, and passed to Robot Framework.

#### Scenario: Log level

- **WHEN** the robot arguments are `--loglevel DEBUG` and the user runs a test that calls a keyword which logs on level DEBUG
- **THEN** the run's command line contains `--loglevel DEBUG`, and the log of the run contains the DEBUG message

#### Scenario: Quoted value

- **WHEN** the robot arguments are `--metadata "Build:1 2"`
- **THEN** the run passes `Build:1 2` as one argument after `--metadata`

### Requirement: Typed Robot Framework options

A Robot Framework run configuration SHALL offer, behind "Modify options", these options and SHALL pass each one that is set:

- variables as name and value pairs, each as `-v name:value`;
- variable files, each as `-V`;
- Robot Framework Python path entries, each as `-P`;
- the output directory as `-d`.

The editor SHALL keep showing the options a configuration uses when it is opened again.

#### Scenario: Variable

- **WHEN** the configuration sets the variable `NAME` to `x` and runs a test that executes `Log    ${NAME}`
- **THEN** the log of the run contains `x`

#### Scenario: Output directory

- **WHEN** the configuration sets the output directory `out2` and the user runs it
- **THEN** `output.xml`, `log.html` and `report.html` are written to `out2` below the project folder

#### Scenario: Options are shown again

- **WHEN** the user shows the variables and the output directory through "Modify options", fills them in, applies, and opens the dialog again
- **THEN** both fields are shown with their values

### Requirement: Mode, language and dry run options

A Robot Framework run configuration SHALL also offer, behind "Modify options", these options and SHALL pass each one that is set:

- the mode: "Inherit" passes nothing, "RPA" passes `--rpa`, "Test automation" passes `--norpa`; new configurations use "Inherit";
- languages, each as `--language`, on every Robot Framework version;
- dry run as `--dryrun`.

#### Scenario: Mode

- **WHEN** the mode is "Inherit"
- **THEN** the run passes neither `--rpa` nor `--norpa`, and when the user switches the mode to "RPA", the next run passes `--rpa`

#### Scenario: Dry run

- **WHEN** dry run is on and the user runs a test that executes `Log    executed`
- **THEN** the run passes `--dryrun`, and the log of the run contains no message `executed`

### Requirement: Tag selection

A Robot Framework run configuration SHALL offer include tags and exclude tags behind "Modify options", and SHALL pass each include tag as `-i` and each exclude tag as `-e`.

#### Scenario: Include tag

- **WHEN** the configuration's target is "Files and folders" with an empty list, its include tags are `smoke`, and one of the project's tests has the tag `smoke`
- **THEN** only that test runs

#### Scenario: Exclude tag

- **WHEN** the configuration's exclude tags are `slow`
- **THEN** no test with the tag `slow` runs

### Requirement: Order of the configuration options

A run SHALL pass the configuration's Robot Framework options after `--` in this order: languages, mode, dry run, output directory, Robot Framework Python path, variable files, variables, include tags, exclude tags, robot arguments; then the selection arguments and the paths of the target.

#### Scenario: Order on the command line

- **WHEN** a configuration sets the mode "RPA", the output directory `out2` and the variable `NAME` to `x`, and the user runs it
- **THEN** the command line passes, after `--`, `--rpa`, then `-d out2`, then `-v NAME:x`, followed by the selection arguments and the paths of the target

### Requirement: Configuration options follow the options of robot.toml

Because `robotcode` places the options of `robot.toml` before the configuration's options, an option with a single value set in the configuration SHALL replace the value from `robot.toml`, and options with several values SHALL add to it. The editor SHALL say this for the output directory, the variables and the lists.

#### Scenario: Output directory set in robot.toml

- **WHEN** `robot.toml` sets `output-dir = "results"` and the configuration sets the output directory `out2`
- **THEN** the run writes its output files to `out2`

#### Scenario: Variable set in both places

- **WHEN** `robot.toml` sets the variable `NAME` to `1` and the configuration sets it to `2`
- **THEN** `Log    ${NAME}` in the run writes `2`

#### Scenario: Include tags in both places

- **WHEN** `robot.toml` sets the include tag `a` and the configuration sets the include tag `b`
- **THEN** the run includes the tests tagged `a` and the tests tagged `b`

### Requirement: Macros in path and argument fields

The robot arguments, the output directory, the variable files, the Robot Framework Python path and the files and folders of the target SHALL offer IntelliJ's macros through "Insert Macros", and the plugin SHALL expand the macros in these values at the start of each run.

#### Scenario: Project folder macro

- **WHEN** the output directory is `$ProjectFileDir$/out3` and the user runs the configuration
- **THEN** the output files are written to `out3` below the project folder

#### Scenario: Inserting a macro

- **WHEN** the user opens "Insert Macros" on the robot arguments field and chooses a macro
- **THEN** the macro is inserted into the field and expanded in the next run
