# Spec Delta: vscode-test-explorer

## ADDED Requirements

### Requirement: The Test Explorer starts with the first Robot Framework project

The extension SHALL start its Test Explorer integration only once a workspace folder is a Robot Framework project, at startup or later in the session. Until then the Testing view SHALL show nothing of RobotCode: no tests, no run profiles and no hint. From then on, the extension SHALL discover tests and offer run profiles only for workspace folders that are Robot Framework projects.

#### Scenario: Workspace without a Robot Framework project

- **WHEN** RobotCode is active in a workspace whose only folder contains `package.json`, `README.md` and TypeScript files
- **THEN** the Testing view shows no RobotCode tests, run profiles or hint, also when it is opened

#### Scenario: Robot Framework file only in an installed package

- **WHEN** the only Robot Framework file of the only workspace folder is `node_modules/fake-pkg/fixtures/example.robot`, and the folder's Python environment has no Robot Framework
- **THEN** no discovery runs, no RobotCode message appears, and the Testing view shows nothing of RobotCode, also when it is opened

#### Scenario: Folder that becomes a project

- **WHEN** `tests/example.robot` with the test `Example` is created in the folder of the first scenario, and the folder's Python environment has Robot Framework
- **THEN** the Test Explorer starts and the tree shows `Example`

#### Scenario: A project and another folder

- **WHEN** the workspace has a folder with suites and a folder with only TypeScript files
- **THEN** the tree shows the tests of the first folder, and its run profiles are the only ones RobotCode offers

#### Scenario: Suites in a skipped folder of a configured project

- **WHEN** a workspace folder has a `robot.toml` whose `paths` name `build/suites`, and its only Robot Framework files are there
- **THEN** the discovery runs and the tree shows the suites in `build/suites`

## MODIFIED Requirements

### Requirement: Other files start no discovery

Creating, changing or deleting a file or folder that is neither a Robot Framework file, nor a folder with Robot Framework files, nor shown in the tree SHALL NOT start a discovery of tests. Configuration files of the language server are not covered: `robot.toml`, `.robot.toml`, `pyproject.toml`, `robocop.toml`, `.gitignore` and `.robotignore` restart the language server of a workspace folder that RobotCode has taken up, and the restart reads the tests again.

#### Scenario: Output files of a run

- **WHEN** a run writes `output.xml`, `log.html` and `report.html` into the folder `results`
- **THEN** no discovery of tests starts because of these files

#### Scenario: Folder without Robot Framework files

- **WHEN** a folder that contains only a text file is created in a workspace folder
- **THEN** no discovery of tests starts and the tree does not change

#### Scenario: Configuration file in a folder that is no Robot Framework project

- **WHEN** `.gitignore` is changed in a workspace folder that is no Robot Framework project and that RobotCode has not taken up
- **THEN** no discovery of tests starts and no language server starts

### Requirement: An empty tree after a discovery explains itself

When the discovery of every enabled workspace folder that is a Robot Framework project has ended without an error and without tests or tasks, the Testing view SHALL show, next to VS Code's own text, a RobotCode hint that no tests or tasks were found, where tests are looked for (the `paths`, profiles and `.robotignore` of the folder's `robot.toml`) and that problems while reading them appear in the Problems view, with the actions **Refresh Tests** and **Troubleshooting**.

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

- **WHEN** the workspace folder contains Robot Framework files and discovery fails for another reason than a selected profile that does not exist, for example because `paths` in `robot.toml` names a folder that does not exist or `robot.toml` is not valid TOML
- **THEN** the tree shows the workspace item with the error, as before, and no hint is shown

#### Scenario: Several folders

- **WHEN** the workspace has two folders, one with tests and one without
- **THEN** the tree shows the tests of the first folder and no hint is shown

#### Scenario: A project without tests and a folder without Robot Framework

- **WHEN** the workspace has a folder with a `robot.toml` and no suite file, and a folder with only TypeScript files
- **THEN** the Testing view shows the RobotCode hint

### Requirement: A switched-off integration says so

When the Test Explorer integration is switched off for every workspace folder that is a Robot Framework project, by `robotcode.testExplorer.enabled`, by `robotcode.disableExtension` or for this session from RobotCode's message about the Python environment, the Testing view SHALL show a RobotCode hint that names the settings and the session case, with an action that opens the settings at `robotcode.testExplorer`.

#### Scenario: Integration switched off

- **WHEN** `robotcode.testExplorer.enabled` is `false` for the only workspace folder
- **THEN** the Testing view shows the hint that names the setting, and its action opens the settings filtered to `robotcode.testExplorer`

#### Scenario: Switched on again

- **WHEN** the user sets `robotcode.testExplorer.enabled` back to `true`
- **THEN** the hint disappears and the tests of the folder appear in the tree

#### Scenario: Switched off for the session

- **WHEN** the user answers **For this session** to RobotCode's question after cancelling the environment message of the only workspace folder
- **THEN** the Testing view shows the switched-off hint until the window is reloaded or **RobotCode: Restart Language Servers** runs

#### Scenario: Switched off in a workspace without a Robot Framework project

- **WHEN** `robotcode.testExplorer.enabled` is `false`, and the only workspace folder contains only `package.json`, `README.md` and TypeScript files
- **THEN** the Testing view shows no RobotCode hint

### Requirement: A missing Python environment says so

When an enabled workspace folder that is a Robot Framework project has no valid Python environment with Robot Framework, so that RobotCode cannot look for tests, and the tree is empty, the Testing view SHALL show a hint that RobotCode needs a Python environment with Robot Framework for the folder, with the action **Select Python Environment**, instead of the hint for a discovery without tests.

#### Scenario: Invalid interpreter

- **WHEN** the folder's Python interpreter does not exist or has no Robot Framework, and the folder contains Robot Framework files
- **THEN** the Testing view shows the environment hint, and its action opens the environment picker of the Python side for the folder

#### Scenario: Invalid interpreter and no Robot Framework files

- **WHEN** the folder has a `robot.toml` but no Robot Framework file, and its Python interpreter is invalid
- **THEN** the Testing view shows the environment hint, not the hint for a discovery without tests

#### Scenario: Environment selected

- **WHEN** the user selects a Python environment with Robot Framework
- **THEN** the tests of the folder appear in the tree, or the hint for a discovery without tests takes over when there are none

#### Scenario: Folder that is no Robot Framework project

- **WHEN** the only workspace folder contains only `package.json`, `README.md` and TypeScript files, and its Python interpreter has no Robot Framework
- **THEN** the Testing view shows no RobotCode hint
