# Spec Delta

## Purpose

Defines how RobotCode's Test Explorer in VS Code keeps its tree of suites, tests and tasks current with the files and folders on disk, without a manual refresh.

## ADDED Requirements

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

Creating, changing or deleting a file or folder that is neither a Robot Framework file, nor a folder with Robot Framework files, nor shown in the tree SHALL NOT start a discovery of tests.

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
