# Spec Delta

## MODIFIED Requirements

### Requirement: A switched-off integration says so

When the Test Explorer integration is switched off for every workspace folder, by `robotcode.testExplorer.enabled`, by `robotcode.disableExtension` or for this session from RobotCode's message about the Python environment, the Testing view SHALL show a RobotCode hint that names the settings and the session case, with an action that opens the settings at `robotcode.testExplorer`.

#### Scenario: Integration switched off

- **WHEN** `robotcode.testExplorer.enabled` is `false` for the only workspace folder
- **THEN** the Testing view shows the hint that names the setting, and its action opens the settings filtered to `robotcode.testExplorer`

#### Scenario: Switched on again

- **WHEN** the user sets `robotcode.testExplorer.enabled` back to `true`
- **THEN** the hint disappears and the tests of the folder appear in the tree

#### Scenario: Switched off for the session

- **WHEN** the user answers **For this session** to RobotCode's question after cancelling the environment message of the only workspace folder
- **THEN** the Testing view shows the switched-off hint until the window is reloaded or **RobotCode: Restart Language Servers** runs

### Requirement: A missing Python environment says so

When an enabled workspace folder has no valid Python environment with Robot Framework, so that RobotCode cannot look for tests, and the tree is empty, the Testing view SHALL show a hint that RobotCode needs a Python environment with Robot Framework for the folder, with the action **Select Python Environment**, instead of the hint for a discovery without tests.

#### Scenario: Invalid interpreter

- **WHEN** the folder's Python interpreter does not exist or has no Robot Framework, and the folder contains Robot Framework files
- **THEN** the Testing view shows the environment hint, and its action opens the environment picker of the Python side for the folder

#### Scenario: Invalid interpreter and no Robot Framework files

- **WHEN** the folder has a `robot.toml` but no Robot Framework file, and its Python interpreter is invalid
- **THEN** the Testing view shows the environment hint, not the hint for a discovery without tests

#### Scenario: Environment selected

- **WHEN** the user selects a Python environment with Robot Framework
- **THEN** the tests of the folder appear in the tree, or the hint for a discovery without tests takes over when there are none
