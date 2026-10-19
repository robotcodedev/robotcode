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

### Requirement: One entry per failure of a test

When a test or task fails in its keywords, the Test Explorer SHALL show one entry for each of its failures, in the order they occurred. Each entry SHALL carry the failure's message and sit at the call in the test that led to it: a step, or the test's setup or teardown. It SHALL list the deeper calls from the outside in, as Python does, so that the call that failed comes last, each with its file and line, without a call on the same line as the call it ran in.

#### Scenario: Failure in a keyword of a resource file

- **WHEN** the test `Login Works` in `tests/login.robot` calls `Welcome Message Should Be` of `resources/shop.resource` in line 16, and `Should Be Equal` fails inside it
- **THEN** Test Results shows one entry for `Login Works`, with the message of `Should Be Equal`, which sits at line 16 of `login.robot` and lists the call of `Should Be Equal` in `shop.resource` with its line

#### Scenario: Opening the entry from the test file

- **WHEN** the user clicks the marker of this entry at line 16 of `login.robot`
- **THEN** the view of the entry opens below line 16, with the message and, below it, the call of `Should Be Equal` with a few lines of the code of `shop.resource`

#### Scenario: Opening the entry from the resource file

- **WHEN** the user clicks the marker of this entry at the call of `Should Be Equal` in `shop.resource`
- **THEN** `login.robot` opens with the view of the entry below line 16

#### Scenario: Going to the error from Test Results

- **WHEN** the user clicks **Go to Error** at this entry in Test Results
- **THEN** `login.robot` opens at line 16

#### Scenario: Several failures collected

- **WHEN** a test runs `Check Value    1` and `Check Value    2` with `Run Keyword And Continue On Failure`, and both fail
- **THEN** Test Results shows two entries for the test, first the one of `Check Value    1`, each with the message of its own failure and at the line of its own step

#### Scenario: Failure in the body and in the teardown

- **WHEN** a step of a test fails, and then its teardown fails as well
- **THEN** the test has two entries, the first at the failed step and the second at the line of `[Teardown]`, each with the message of its own failure

#### Scenario: Failure in a step

- **WHEN** a step of the test calls `Should Be Equal` itself, and it fails
- **THEN** the entry sits at that step and lists no deeper calls

#### Scenario: Keyword run by a Run Keyword variant

- **WHEN** the step `Run Keyword And Continue On Failure    Check Value    1` in line 9 of a test fails in `Should Be Equal` inside `Check Value`
- **THEN** its entry sits at line 9 and lists the call of `Should Be Equal`, but not the call of `Check Value`, which has line 9 as well

### Requirement: A keyword that turns failures into its own is one failure

When a keyword fails with a message of its own after failures inside it, as Wait Until Keyword Succeeds does after its last attempt or Run Keyword And Expect Error after another error, the Test Explorer SHALL show it as one failure: one entry with that keyword's message, listing the calls of the last failure inside it. The failures inside it SHALL get no entries of their own.

#### Scenario: Retried keyword

- **WHEN** the step `Wait Until Keyword Succeeds    3x    10ms    Should Be Equal    a    b` of a test fails
- **THEN** the test has one entry, `Keyword 'Should Be Equal' failed after retrying 3 times. The last error was: a != b`, at that step

#### Scenario: Another error than expected

- **WHEN** the step `Run Keyword And Expect Error    Wrong*    Should Be Equal    a    b` of a test fails
- **THEN** the test has one entry, `Expected error 'Wrong*' but got 'a != b'.`, at that step

#### Scenario: Retries in a keyword of a resource file

- **WHEN** a test calls `Retry Check` of `shop.resource`, whose step `Wait Until Keyword Succeeds    2x    10ms    Check Value    1` fails because `Should Be Equal` in `Check Value` fails each time
- **THEN** the test has one entry with the message of `Wait Until Keyword Succeeds`, at the call of `Retry Check`, which lists the call of `Wait Until Keyword Succeeds`, then the call of `Should Be Equal` of the last attempt

#### Scenario: Failure caught later in the keyword's teardown

- **WHEN** a keyword fails in `Should Be Equal    a    b`, and its teardown catches the failure of `Fail    cleanup failed` with `Run Keyword And Ignore Error`
- **THEN** the test has the entry `a != b`, then the entry `Caught: cleanup failed`

#### Scenario: Failures collected before a caught one

- **WHEN** a keyword under `robot:continue-on-failure` fails in `Should Be Equal    c    d` and `Should Be Equal    e    f`, and then catches the failure of `Fail    ignored` with `Run Keyword And Ignore Error`
- **THEN** the test has the entries `c != d` and `e != f`, then the entry `Caught: ignored`

### Requirement: Caught failures are marked

When a failed test or task caught a failure, with `TRY`/`EXCEPT` or with a BuiltIn keyword that handles failures such as `Run Keyword And Ignore Error`, the Test Explorer SHALL show the caught failure as an entry of its own, after the entries of the failures that made the test fail. The entry's text SHALL be `Caught: ` followed by the failure's message; it SHALL sit at and list its calls like the other entries.

#### Scenario: Failure caught by TRY/EXCEPT

- **WHEN** a test catches the failure of `Should Be Equal    a    b` in a `TRY` branch with `EXCEPT`, and later fails in `Check Value`
- **THEN** the test has the entry of the failure in `Check Value` first, then the entry `Caught: a != b` at the line of the `Should Be Equal` step

#### Scenario: EXCEPT branch that fails

- **WHEN** a step in a `TRY` branch fails, and the step in its `EXCEPT` branch fails as well
- **THEN** the test has two entries, neither of them starting with `Caught: `

#### Scenario: Attempt of a keyword that was retried until it passed

- **WHEN** `Wait Until Keyword Succeeds` passes on its second attempt in a test that fails later
- **THEN** the failure of the first attempt is an entry of its own, starting with `Caught: `

#### Scenario: Passed test

- **WHEN** a test catches a failure with `Run Keyword And Ignore Error` and passes
- **THEN** Test Results shows the test as passed, without an entry

### Requirement: Calls without a marker show the failure inline

VS Code marks an entry in the editor once in each file: at the line where it sits, and in every other file at the first of its calls there, the outermost one. Every other line of the calls that an entry lists SHALL show the entry's text as inline output at its end while VS Code shows inline test output, and the test's output SHALL contain the entry's text once for each of these lines.

#### Scenario: Nested calls in one resource file

- **WHEN** the test `Nested` calls `Outer In Resource` in line 6 of `suite.robot`, which calls `Inner In Resource` in line 3 of `shop.resource`, which calls `Check Value` in line 6, in which `Should Be Equal` in line 10 fails with `0 != ok`
- **THEN** the editor marks line 6 of `suite.robot` and line 3 of `shop.resource` with `0 != ok`, and lines 6 and 10 of `shop.resource` show `0 != ok` as inline output

#### Scenario: Inline test output switched off

- **WHEN** the user switches the inline test output off with **Test: Toggle Inline Test Output** and runs the test `Nested` again
- **THEN** only line 6 of `suite.robot` and line 3 of `shop.resource` show `0 != ok`

### Requirement: A failed test without a failed keyword shows its message

When a test or task fails without a failure in one of its keywords, the Test Explorer SHALL show the test's message as an entry at the test's own line.

#### Scenario: Failed suite setup

- **WHEN** the suite setup of `login.robot` fails
- **THEN** each test of the suite has one entry, with its message that the parent suite setup failed, at the line of the test
