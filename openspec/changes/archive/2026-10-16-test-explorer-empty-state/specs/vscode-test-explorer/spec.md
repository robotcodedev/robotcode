# Spec Delta

## ADDED Requirements

### Requirement: An empty tree after a discovery explains itself

When the discovery of every enabled workspace folder has ended without an error and without tests or tasks, the Testing view SHALL show, next to VS Code's own text, a RobotCode hint that no tests or tasks were found, where tests are looked for (the `paths`, profiles and `.robotignore` of the folder's `robot.toml`) and that problems while reading them appear in the Problems view, with the actions **Refresh Tests** and **Troubleshooting**.

#### Scenario: Project without tests

- **WHEN** the workspace folder has a `robot.toml` whose `paths` point to a folder without suite files, and discovery has ended
- **THEN** the Testing view shows the RobotCode hint with both actions

#### Scenario: Folder without Robot Framework files

- **WHEN** the workspace folder has a `robot.toml` but no Robot Framework file at all, whatever its `paths` say
- **THEN** the Testing view shows the RobotCode hint, because there is nothing to discover

#### Scenario: Only resource files

- **WHEN** the workspace folder contains resource files but no suite file with tests or tasks
- **THEN** the Testing view shows the RobotCode hint

#### Scenario: Refresh Tests

- **WHEN** the user creates a suite file with a test and clicks **Refresh Tests** in the hint
- **THEN** the test appears in the tree and the hint disappears

#### Scenario: Troubleshooting

- **WHEN** the user clicks **Troubleshooting** in the hint
- **THEN** the troubleshooting page of the VS Code guide opens

#### Scenario: Project with tests

- **WHEN** the workspace folder has suites with tests
- **THEN** the tree shows them and no hint is shown

#### Scenario: Failed discovery

- **WHEN** the workspace folder contains Robot Framework files and discovery fails, for example because `paths` in `robot.toml` names a folder that does not exist or `robot.toml` is not valid TOML
- **THEN** the tree shows the workspace item with the error, as before, and no hint is shown

#### Scenario: Several folders

- **WHEN** the workspace has two folders, one with tests and one without
- **THEN** the tree shows the tests of the first folder and no hint is shown

### Requirement: A switched-off integration says so

When the Test Explorer integration is switched off for every workspace folder, by `robotcode.testExplorer.enabled` or `robotcode.disableExtension`, the Testing view SHALL show a RobotCode hint that names the setting, with an action that opens the settings at `robotcode.testExplorer`.

#### Scenario: Integration switched off

- **WHEN** `robotcode.testExplorer.enabled` is `false` for the only workspace folder
- **THEN** the Testing view shows the hint that names the setting, and its action opens the settings filtered to `robotcode.testExplorer`

#### Scenario: Switched on again

- **WHEN** the user sets `robotcode.testExplorer.enabled` back to `true`
- **THEN** the hint disappears and the tests of the folder appear in the tree

### Requirement: A missing Python environment says so

When an enabled workspace folder has no valid Python environment with Robot Framework, so that RobotCode cannot look for tests, and the tree is empty, the Testing view SHALL show a hint that RobotCode needs a Python environment with Robot Framework for the folder, with the action **Select Python Environment**, instead of the hint for a discovery without tests.

#### Scenario: Invalid interpreter

- **WHEN** the folder's Python interpreter does not exist or has no Robot Framework, and the folder contains Robot Framework files
- **THEN** the Testing view shows the environment hint, and its action opens RobotCode's environment selection

#### Scenario: Invalid interpreter and no Robot Framework files

- **WHEN** the folder has a `robot.toml` but no Robot Framework file, and its Python interpreter is invalid
- **THEN** the Testing view shows the environment hint, not the hint for a discovery without tests

#### Scenario: Environment selected

- **WHEN** the user selects a Python environment with Robot Framework
- **THEN** the tests of the folder appear in the tree, or the hint for a discovery without tests takes over when there are none
