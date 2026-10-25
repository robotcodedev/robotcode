## MODIFIED Requirements

### Requirement: A failed discovery replaces the shown suites

When the discovery of a workspace folder fails, the Test Explorer SHALL NOT keep the suites, tests and tasks of an earlier discovery of that folder in the tree, and SHALL show the error at the workspace folder, unless the discovery failed because the folder's `robotcode.profiles` names a profile that its configuration does not define.

#### Scenario: Test path that does not exist

- **WHEN** the tree shows the suite "Tests" of `src/tests`, and `robot.toml` is changed to `paths = ["missing"]`, a folder that does not exist
- **THEN** within a few seconds the tree shows the workspace folder with the error of the discovery and no longer shows "Tests" or any suite below it

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

- **WHEN** the workspace folder contains Robot Framework files and discovery fails for another reason than a selected profile that does not exist, for example because `paths` in `robot.toml` names a folder that does not exist or `robot.toml` is not valid TOML
- **THEN** the tree shows the workspace item with the error, as before, and no hint is shown

#### Scenario: Several folders

- **WHEN** the workspace has two folders, one with tests and one without
- **THEN** the tree shows the tests of the first folder and no hint is shown

## ADDED Requirements

### Requirement: A selected profile that does not exist says so

When the discovery of an enabled workspace folder fails because the folder's `robotcode.profiles` names a profile or pattern that selects no profile of its configuration, the folder SHALL leave the tree, as a folder without a valid Python environment does. While the tree is empty, the Testing view SHALL show a hint that a profile selected for the folder is not defined in its configuration, with the action **Select Configuration Profiles**, instead of the hint for a discovery without tests.

#### Scenario: Mistyped profile in the only folder

- **WHEN** the only workspace folder sets `robotcode.profiles` to `["typo"]` and its `robot.toml` defines no profile `typo`
- **THEN** the tree shows no item for the folder, and the Testing view shows the hint with **Select Configuration Profiles**

#### Scenario: Select Configuration Profiles

- **WHEN** the user clicks **Select Configuration Profiles** in the hint
- **THEN** the profile list of the folder opens and says that `typo` was removed from the selection, and after the list is closed the tests of the folder appear in the tree

#### Scenario: Several folders

- **WHEN** the workspace has two folders, one with tests and one whose `robotcode.profiles` names a profile that its `robot.toml` does not define
- **THEN** the tree shows the tests of the first folder and no item for the second, and no hint is shown
