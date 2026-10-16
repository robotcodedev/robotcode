# vscode-test-explorer Specification

## Purpose

Defines how RobotCode's Test Explorer in VS Code shows the discovered suites, tests and tasks and keeps the tree current with the files and folders on disk, without a manual refresh.

## Requirements

### Requirement: Robot Framework files followed on disk

When a Robot Framework file is created in a workspace folder or deleted from it, also outside VS Code, the Test Explorer SHALL add or remove its suite without a manual refresh.

#### Scenario: Suite file created in a terminal

- **WHEN** a file `tests/refunds.robot` with one test is created outside VS Code
- **THEN** within a few seconds the tree shows the suite "Refunds" with that test

#### Scenario: Suite file deleted in a terminal

- **WHEN** the file `tests/refunds.robot`, shown in the tree, is deleted outside VS Code
- **THEN** within a few seconds the tree no longer shows the suite "Refunds"

### Requirement: Deleted folders leave the tree

When a folder that the Test Explorer shows as a suite, or a folder that contains suites it shows, is deleted, renamed or moved away, the Test Explorer SHALL remove these suites and everything below them from the tree without a manual refresh, also when this happens outside VS Code.

#### Scenario: Folder deleted in a terminal

- **WHEN** the folder `tests/checkout` with two suite files, shown in the tree as the suite "Checkout", is deleted with `rm -rf`
- **THEN** within a few seconds the tree no longer shows "Checkout" or any suite below it

#### Scenario: Folder deleted in VS Code

- **WHEN** the folder `tests/checkout` is deleted in VS Code's Explorer
- **THEN** within a few seconds the tree no longer shows "Checkout" or any suite below it

#### Scenario: Folder renamed

- **WHEN** the folder `tests/checkout` is renamed to `tests/payment` outside VS Code
- **THEN** within a few seconds the tree shows the suite "Payment" with the same suites and tests, and no longer shows "Checkout"

#### Scenario: Parent folder of the test paths deleted

- **WHEN** `robot.toml` sets `paths = ["src/tests"]`, the tree shows the suite "Tests" of `src/tests`, and the folder `src` is deleted outside VS Code
- **THEN** within a few seconds the tree no longer shows "Tests" or any suite below it

### Requirement: New folders join the tree

When a folder that contains Robot Framework files appears in a workspace folder together with its files, for example copied, moved in or checked out, the Test Explorer SHALL show its suites without a manual refresh, also when this happens outside VS Code.

#### Scenario: Folder copied in

- **WHEN** a folder `invoices` with a suite file is copied into `tests/` with `cp -r`
- **THEN** within a few seconds the tree shows the suite "Invoices" with its suite file below it

#### Scenario: Folder moved in

- **WHEN** a folder with a suite file is moved from outside the workspace folder into `tests/` with `mv`
- **THEN** within a few seconds the tree shows its suites

### Requirement: Deleted suite files leave the tree whatever their extension

When a file that the Test Explorer shows as a suite is deleted, renamed or moved away, the Test Explorer SHALL remove its suite without a manual refresh, whatever the file's extension, for example a file read by a custom parser that `robot.toml` configures.

#### Scenario: Suite of a custom parser deleted

- **WHEN** `robot.toml` configures a custom parser for `.custom` files and the file `tests/orders.custom`, shown in the tree as the suite "Orders", is deleted outside VS Code
- **THEN** within a few seconds the tree no longer shows "Orders"

#### Scenario: Suite of a custom parser renamed

- **WHEN** the file `tests/orders.custom` is renamed to `tests/billing.custom` outside VS Code
- **THEN** within a few seconds the tree shows the suite "Billing" with the same tests, and no longer shows "Orders"

### Requirement: Other files start no discovery

Creating, changing or deleting a file or folder that is neither a Robot Framework file, nor a folder with Robot Framework files, nor shown in the tree SHALL NOT start a discovery of tests. Configuration files of the language server are not covered: `robot.toml`, `.robot.toml`, `pyproject.toml`, `robocop.toml`, `.gitignore` and `.robotignore` restart the language server of their workspace folder, and the restart reads the tests again.

#### Scenario: Output files of a run

- **WHEN** a run writes `output.xml`, `log.html` and `report.html` into the folder `results`
- **THEN** no discovery of tests starts because of these files

#### Scenario: Folder without Robot Framework files

- **WHEN** a folder that contains only a text file is created in a workspace folder
- **THEN** no discovery of tests starts and the tree does not change

### Requirement: Many folder changes lead to one discovery

Folder changes that arrive within a short time SHALL lead to one discovery of the workspace folder, for example when a branch switch or a single command deletes or adds several suite folders.

#### Scenario: Three folders deleted with one command

- **WHEN** three folders that the tree shows as suites are deleted with one `rm -rf` command
- **THEN** the Test Explorer runs one discovery of the workspace folder, and none of the three folders remains in the tree

### Requirement: A failed discovery replaces the shown suites

When the discovery of a workspace folder fails, the Test Explorer SHALL show the error at the workspace folder and SHALL NOT keep the suites, tests and tasks of an earlier discovery of that folder in the tree.

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
