## ADDED Requirements

### Requirement: Tests keep their IDs when a single file is read again

When the Test Explorer reads a suite file again, after an edit or a save, its suites, tests and tasks SHALL keep the IDs that the discovery of the workspace folder gave them, also when `robot.toml` sets several paths. They SHALL keep their last results, and running them from the tree or the editor SHALL run them.

#### Scenario: Save in a project with several paths

- **WHEN** `robot.toml` sets `paths = ["electron", "vscode"]` and `run-empty-suite = true`, the test "Opens Terminal" in `vscode/open_vs_code.robot` passed, and the user changes an argument of a keyword call in that file and saves it
- **THEN** the test still shows its passed result, and **Run Test** at the test runs that one test

#### Scenario: Test added in a project with several paths

- **WHEN** in that project the user adds a test to `vscode/open_vs_code.robot` and saves it
- **THEN** the tree shows the new test in the suite "Open Vs Code", and the other tests of the file keep their results

### Requirement: Tasks stay when a single file is read again

When the Test Explorer reads a suite file with tasks again, after an edit or a save, it SHALL keep showing the file's tasks, as it does for the tests of a suite file.

#### Scenario: Argument changed in a file with tasks

- **WHEN** `tasks/cleanup.robot` has a `*** Tasks ***` section with the tasks "Clean Up" and "Archive Files", and the user changes an argument of a keyword call in it
- **THEN** within a few seconds the tree still shows both tasks, also after **Refresh Tests**

#### Scenario: Task added

- **WHEN** the user adds a task to `tasks/cleanup.robot`
- **THEN** within a few seconds the tree shows the new task next to the other two

### Requirement: The tree matches each discovery of the workspace folder

After a discovery of a workspace folder, the tree SHALL show exactly the suites, tests and tasks of its result, also when single files were read again since the discovery before. **Refresh Tests** SHALL rebuild the tree of every workspace folder from a new discovery.

#### Scenario: Refresh Tests after a change the file watcher missed

- **WHEN** a test is appended to `tests/orders.robot` outside VS Code while VS Code's file watcher does not report that file, for example because `files.watcherExclude` excludes it or the system's limit of watched files is reached, and the user runs **Refresh Tests**
- **THEN** the tree shows the new test in the suite "Orders"

#### Scenario: Discovery with the same result as before a save

- **WHEN** a suite file was read again after a save, and the next discovery of the workspace folder returns the same suites and tests as the discovery before the save
- **THEN** the tree shows the suites and tests of that discovery, and running a test from the tree runs it

### Requirement: Suite files changed on disk are read again

When a suite file that the tree shows changes on disk while no editor has it open, for example by `git checkout` or another program, the Test Explorer SHALL read it again from disk without a manual refresh.

#### Scenario: Test appended outside VS Code

- **WHEN** `tests/orders.robot` is not open in VS Code, and a test is appended to it outside VS Code
- **THEN** within a few seconds the tree shows the new test in the suite "Orders"

### Requirement: A suite file restored while its tab is open comes back

When a suite file is deleted and appears again while an editor tab for it stays open, the Test Explorer SHALL show its suite again without a manual refresh, also when the file comes back with the content that the tab shows.

#### Scenario: Deleted file restored with the same content

- **WHEN** `tests/orders.robot` is open in an editor tab, is deleted outside VS Code, and is restored with the same content, for example with `git checkout -- tests/orders.robot`
- **THEN** within a few seconds the tree shows the suite "Orders" with its tests again

### Requirement: Files changed together are all read again

When several suite files change at about the same time, for example by one edit across files such as **Replace All** or a rename, the Test Explorer SHALL read each of them again; reading one file SHALL NOT cancel reading another. From six files on, it SHALL run one discovery of the workspace folder instead.

#### Scenario: One edit in two suite files

- **WHEN** one edit adds a test to each of the suite files `tests/orders.robot` and `tests/refunds.robot`
- **THEN** within a few seconds the tree shows both new tests

#### Scenario: One edit in six suite files

- **WHEN** one edit changes six suite files
- **THEN** the Test Explorer runs one discovery of the workspace folder, and the tree shows the changes of all six files

### Requirement: A changed initialization file updates the suites below it

When a suite initialization file such as `__init__.robot` changes, in the editor or on disk, the Test Explorer SHALL update the suite of its folder and the suites, tests and tasks below it without a manual refresh.

#### Scenario: Suite renamed in the initialization file

- **WHEN** with Robot Framework 6.1 or later the user adds `Name    Shop` to the `*** Settings ***` of `tests/__init__.robot`, whose folder the tree shows as the suite "Tests"
- **THEN** within a few seconds the tree shows the suite as "Shop", with the same suites and tests below it

### Requirement: Resource files start no discovery

Creating, changing or deleting a resource file, a file with the extension `.resource`, SHALL NOT start a discovery of tests, because Robot Framework never builds a suite from a resource file.

#### Scenario: Resource file edited

- **WHEN** the user edits `resources/shop.resource` and pauses typing
- **THEN** no discovery of tests starts

#### Scenario: Resource file deleted outside VS Code

- **WHEN** `resources/shop.resource` is deleted outside VS Code
- **THEN** no discovery of tests starts, and the tree stays as it was

### Requirement: The top-level suite of several paths can be run

When `robot.toml` sets several paths, the Test Explorer SHALL offer **Run** and **Debug** at the top-level suite that Robot Framework creates for them. Running that suite, its workspace folder or **Run Tests** in the view's title bar SHALL run the tests of all paths.

#### Scenario: Run at the top-level suite

- **WHEN** `robot.toml` sets `paths = ["electron", "vscode"]`, and the user runs the suite "Electron & Vscode" from the tree
- **THEN** one run starts and runs the tests of both paths

#### Scenario: Run Tests in a project with several paths

- **WHEN** in that project the user clicks **Run Tests** in the title bar of the Testing view
- **THEN** one run starts and runs the tests of both paths

### Requirement: Run Tests runs every workspace folder

In a workspace with several folders, **Run Tests** and **Debug Tests** in the title bar of the Testing view SHALL run the tests and tasks of every folder. A folder that the chosen profile does not belong to SHALL run as its own Run or Debug profile runs it.

#### Scenario: Two workspace folders

- **WHEN** a workspace has the folders `robotcode-demo` with tests and `rpa` with tasks, and the user clicks **Run Tests**
- **THEN** a run starts for each folder, and the tasks of `rpa` run as well as the tests of `robotcode-demo`

#### Scenario: A profile of robot.toml as the default profile

- **WHEN** in that workspace the user chose "Run ci - Staging shop [robotcode-demo]" as the default profile, and clicks **Run Tests**
- **THEN** `robotcode-demo` runs with the profile `ci` of its `robot.toml`, and `rpa` runs without it
