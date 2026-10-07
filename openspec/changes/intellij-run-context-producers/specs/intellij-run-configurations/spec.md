# Spec Delta

## Purpose

Defines what a Robot Framework run configuration of the IntelliJ plugin runs, how it is stored, edited, shared and reused, and which arguments its runs pass to `robotcode` and Robot Framework.

## ADDED Requirements

### Requirement: Context runs follow the caret

Run and Debug from the editor's context menu, and the shortcuts for running and debugging the context configuration, SHALL run the discovered test or task whose body holds the caret in a suite file. That is the discovered test or task of the file that starts on the caret's line or on the closest line above it, provided that no section header row, a row whose first cell starts with `*`, lies between its start and the caret.

#### Scenario: Caret in a test body

- **WHEN** the caret is on a keyword call inside the body of the test "First Test Passes" and the user presses Ctrl+Shift+F10
- **THEN** only "First Test Passes" runs, in a configuration named "Test First Test Passes"

#### Scenario: Caret in a keyword after the tests

- **WHEN** the caret is inside the body of the keyword "Build Greeting" in the `*** Keywords ***` section that follows the tests, and the user presses Ctrl+Shift+F10
- **THEN** the suite of the file runs

#### Scenario: Translated section headers

- **WHEN** a suite file starts with `Language: de`, its tests are in a `*** Testfälle ***` section, and the caret is in the body of one of them
- **THEN** Ctrl+Shift+F10 runs that test

### Requirement: Context runs outside a test or task

At any other position in a suite file, Run and Debug from the editor's context menu, and the shortcuts for running and debugging the context configuration, SHALL run the suite of the file.

#### Scenario: Caret in the settings

- **WHEN** the caret is on line 1 of a suite file and the user chooses Run from the editor's context menu
- **THEN** the suite of the file runs

### Requirement: Several selected items run together

When several suite files, folders or results-tree nodes are selected and the user chooses Run or Debug, the plugin SHALL create one configuration for all of them. It SHALL leave out duplicates and items whose parent is also selected. The configuration SHALL be named after the number of items, for example "Robot: 2 items".

#### Scenario: Two suite files

- **WHEN** the user selects `tests/sample.robot` and `tests/other.robot` in the Project view and chooses Run
- **THEN** one run executes the tests of both files, in a configuration named "Robot: 2 items"

#### Scenario: Folder and a file inside it

- **WHEN** the user selects the folder `tests` and the file `tests/sample.robot` and chooses Run
- **THEN** the run's configuration selects only the folder suite `tests`

### Requirement: Target of a configuration for several items

When discovery knows every selected item, the configuration for several selected items SHALL have the "Tests and suites" target; when every selected item is a file or folder and discovery does not know all of them, it SHALL have the "Files and folders" target.

#### Scenario: Items that discovery knows

- **WHEN** the user selects `tests/sample.robot` and `tests/other.robot`, which discovery knows, and chooses Run
- **THEN** the run's configuration has the "Tests and suites" target

### Requirement: Suite nodes in the results tree

File suite and folder suite nodes in the results tree SHALL offer Jump to Source, Run and Debug. Jump to Source SHALL open the suite file or select the folder in the Project view. Run and Debug SHALL run that suite. A result whose line lies beyond the end of the edited file SHALL open the file instead of failing.

#### Scenario: Rerunning a file suite

- **WHEN** the user right-clicks the node of the suite `Sample` in the results tree and chooses Run
- **THEN** the tests of `tests/sample.robot` run

#### Scenario: Folder suite

- **WHEN** the user selects the node of the folder suite `Tests` and chooses Jump to Source
- **THEN** the folder `tests` is selected in the Project view, and Run from the same node runs that folder suite

#### Scenario: Line beyond the end of the file

- **WHEN** lines were deleted from a suite file after a run and the user chooses Jump to Source on a test node whose line no longer exists
- **THEN** the suite file opens and no error is reported

### Requirement: Files that discovery does not know run by path

When Run or Debug is chosen for a suite file or a folder with suite files that discovery does not know, the plugin SHALL create a configuration with the "Files and folders" target for that path, named "Robot <name>", and SHALL reuse it for the same path. An initialization file `__init__.robot` SHALL stand for its folder.

#### Scenario: File outside the configured paths

- **WHEN** `robot.toml` sets `paths = ["tests"]` and the user chooses Run in the context menu of `extra/other.robot`
- **THEN** the tests of `extra/other.robot` run in a configuration named "Robot other.robot"

#### Scenario: Before discovery has a result

- **WHEN** the user runs a suite file from the editor's tab context menu before discovery has a result
- **THEN** the file runs by its path

### Requirement: Robot Framework folders rank before pytest

For a folder that discovery reports as a Robot Framework suite, the Robot Framework configuration SHALL rank first among the configurations created from that context. Configurations of other producers SHALL remain available in the context menu.

#### Scenario: Folder with Robot Framework suites

- **WHEN** the user opens the Run submenu of the folder `tests`, which holds Robot Framework suites
- **THEN** the Robot Framework configuration for the folder suite is listed first, and the pytest configuration is still listed

### Requirement: Context configurations keep the template's values

A configuration created from the gutter or from a context SHALL take every value from the template of Robot Framework run configurations, except its target and its name.

#### Scenario: Values set in the template

- **WHEN** the template has a Before launch task, "Allow multiple instances" and the environment variable `FOO=bar`, and the user runs a test that executes `Log    %{FOO}` from the gutter
- **THEN** the new temporary configuration has the Before launch task and "Allow multiple instances", and the log of the run contains `bar`

### Requirement: Generated configuration names

A configuration created from the gutter or from a context SHALL get a generated name: "<Type> <name>" for one discovered item, such as "Test First Test Passes" or "Suite Sample"; "Robot <name>" for one file or folder; "Robot: <n> items" for several items. A configuration that the user renamed SHALL keep its name. When a file or folder of a "Files and folders" target is renamed or moved in the IDE, the target SHALL follow, and so SHALL a generated name.

#### Scenario: Renamed file

- **WHEN** a configuration named "Robot other.robot" runs `extra/other.robot` and the user renames the file to `extra/more.robot` in the Project view
- **THEN** the configuration runs `extra/more.robot` and is named "Robot more.robot"

#### Scenario: Name chosen by the user

- **WHEN** the user renames the configuration "Test First Test Passes" to "Smoke" and runs the test from the gutter again
- **THEN** the configuration "Smoke" runs and keeps its name

### Requirement: Context runs and the editor while indexing

Context runs from the editor, the Project view, the gutter and the results tree, and the editor of Robot Framework run configurations, SHALL stay available while the IDE indexes the project.

#### Scenario: Run during indexing

- **WHEN** the IDE indexes the project after the Python interpreter changed, and the user runs a test from the gutter
- **THEN** the test runs, and the run configuration dialog can be opened and edited at the same time
