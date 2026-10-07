# Spec Delta

## Purpose

Defines what a Robot Framework run configuration of the IntelliJ plugin runs, how it is stored, edited, shared and reused, and which arguments its runs pass to `robotcode` and Robot Framework.

## ADDED Requirements

### Requirement: A run of selected items selects them by name

When a Robot Framework run covers selected tests, tasks, file suites or folder suites instead of the whole project, the plugin SHALL pass Robot Framework:

- `-N` with the name of the top-level suite as discovery reports it;
- `-s` with the full name of each selected suite and of the suite that contains each selected test or task, each name once;
- `-bl` with the full name of each selected item.

#### Scenario: Running a single test from the gutter

- **WHEN** the project uses Robot Framework 7.5, another suite file in the project contains a syntax error, and the user runs the test "First Test Passes" of `tests/sample.robot` from the gutter
- **THEN** the run passes `-I tests/sample.robot`, `-N` with the top-level suite name, `-s` with the full name of the suite `Sample` and `-bl` with the full name of the test
- **AND** the run shows no error from the other suite file

### Requirement: A run of selected items parses only their files

When a Robot Framework run covers selected tests, tasks, file suites or folder suites instead of the whole project, the plugin SHALL pass Robot Framework `-I` with the file or folder of each suite passed with `-s`, each path once, but only when discovery reports that the project's Robot Framework supports `--parseinclude`.

Values passed with `-I` and `-s` SHALL have the glob characters `*`, `?`, `[` and `]` escaped, as in VS Code.

#### Scenario: Running a folder suite

- **WHEN** the user runs the folder `tests` from the Project view
- **THEN** the run passes `-I tests` together with `-s` and `-bl` for the full name of the folder suite, and Robot Framework parses no file outside `tests`

#### Scenario: Robot Framework without parse-include support

- **WHEN** discovery reports that the project's Robot Framework does not support `--parseinclude`, and the user runs a single test
- **THEN** the run passes `-N`, `-s` and `-bl` but no `-I`

#### Scenario: Glob characters in a file name

- **WHEN** the user runs a test of the suite file `tests/[draft] cases.robot`
- **THEN** the run passes `-I` with the value `tests/[[]draft[]] cases.robot`, `-s` with the suite's full name with its glob characters escaped the same way, and `-bl` with the unescaped full name of the test

### Requirement: A run that limits parsing tolerates empty top-level suites

A run that passes `-I` SHALL also pass `--runemptysuite`, so that Robot Framework does not reject the run when a top-level path of the project contains no file to parse. A run without `-I` SHALL NOT pass `--runemptysuite` for this reason.

#### Scenario: Several paths in robot.toml

- **WHEN** `robot.toml` sets `paths = ["folder1", "folder2"]`, the project uses Robot Framework 7.5, and the user runs a test of a suite in `folder2` from the gutter
- **THEN** the run passes `--runemptysuite` together with `-I`, the test runs and passes, and the run does not end with "Suite 'Folder1' contains no tests or tasks"

#### Scenario: Selected test no longer exists

- **WHEN** the user renames a test and reruns the run configuration that was created for its old name
- **THEN** the run ends with Robot Framework's summary "0 tests" instead of the error that the suite contains no tests

### Requirement: A run of the whole project gets no selection arguments

When a run covers the whole project, the plugin SHALL pass none of `-I`, `-N`, `-s`, `-bl` and `--runemptysuite`, so that Robot Framework runs every suite of the configured paths.

#### Scenario: Running the project folder

- **WHEN** the user runs the project's root folder from the Project view
- **THEN** the run passes no selection arguments and runs every test of the project

### Requirement: Robot Framework arguments follow a separator

The plugin SHALL place every argument meant for Robot Framework after a `--` separator, and the options of the `robotcode debug` command, such as `--no-debug` and `--tcp`, before it. Without arguments for Robot Framework, the command line SHALL contain no separator.

#### Scenario: Running a test

- **WHEN** the user runs a single test with Run
- **THEN** the command line contains `debug --no-debug`, then `--tcp` with the port if it is not the default port, then `--` and then the selection arguments

#### Scenario: Running the whole project

- **WHEN** the user runs the project's root folder with Debug
- **THEN** the command line ends with the options of `robotcode debug` and contains no `--`
