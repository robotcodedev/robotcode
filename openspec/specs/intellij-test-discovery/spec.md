# intellij-test-discovery Specification

## Purpose

Defines which discovered Robot Framework tests, tasks and suites the IntelliJ plugin marks in the editor gutter, and how it keeps that model current when a single suite file is rediscovered.

## Requirements

### Requirement: Run markers for tests and tasks

The plugin SHALL show a run marker in the editor gutter on the line of every discovered test and every discovered task of a suite file. A suite file SHALL show a run marker on line 1 while it contains at least one discovered test or task. The lines of keyword definitions SHALL show no run marker.

#### Scenario: Task file after the startup discovery

- **WHEN** a project contains a suite file with a `*** Tasks ***` section holding two tasks, and the discovery at project startup has finished
- **THEN** line 1 and the first line of each task show a run marker

#### Scenario: Keyword definitions

- **WHEN** a suite file with tasks also has a `*** Keywords ***` section
- **THEN** the lines of the keyword definitions show no run marker

### Requirement: Task markers act like test markers

A task's marker SHALL offer the same Run and Debug actions as a test's marker, and SHALL show the state of the task's last run with the same icons as a test. Run and Debug from a test's or task's marker SHALL run only that test or task.

#### Scenario: Running a task from its marker

- **WHEN** the user runs a task from its run marker
- **THEN** only that task runs, the results tree shows it as passed, and its marker then shows the passed state

#### Scenario: Failed task

- **WHEN** a task failed in its last run
- **THEN** its marker shows the same failed state icon as the marker of a failed test

### Requirement: Rediscovering a single suite file keeps its tests and tasks

When the plugin rediscovers a single suite file, for example after an edit, it SHALL keep the run markers of all its tests and tasks, whether the file has a `*** Test Cases ***` or a `*** Tasks ***` section and whether `robot.toml` sets `rpa = true`. The marker on line 1 of the file SHALL stay while the file contains a test or task. When the rediscovery of the file finds no suite with tests or tasks for it, the plugin SHALL rediscover the whole project.

#### Scenario: Editing a task file

- **WHEN** the user changes a line inside a task of a suite file with tasks and the rediscovery delay has passed
- **THEN** line 1 and the first line of every task still show a run marker

#### Scenario: Adding a task

- **WHEN** the user adds a task to a suite file with tasks and the rediscovery delay has passed
- **THEN** the new task shows a run marker, and line 1 and the other tasks keep theirs

#### Scenario: Project in RPA mode

- **WHEN** `robot.toml` sets `rpa = true` and the user edits a suite file with a `*** Test Cases ***` section
- **THEN** after the rediscovery delay, line 1 and every item of the file still show a run marker

#### Scenario: Last test deleted

- **WHEN** the user deletes the only test of a suite file and the rediscovery delay has passed
- **THEN** the plugin rediscovers the whole project, and the file shows no run marker

### Requirement: Discovery runs again when its inputs change

The plugin SHALL run a full discovery of a project when:

- a Robot Framework suite file or a folder in the project is created, deleted, moved or renamed;
- `robot.toml`, `.robot.toml`, `pyproject.toml`, `.gitignore` or `.robotignore` in the project is created, changed or deleted;
- a setting changes the command line, environment or working directory that discovery would run with, compared with the last discovery;
- the user chooses Tools | RobotCode | Refresh Robot Framework Tests.

#### Scenario: Profile selection

- **WHEN** the user selects another configuration profile
- **THEN** one full discovery runs with the new profile

#### Scenario: Ignore file

- **WHEN** the user adds a suite folder to `.robotignore` and saves it
- **THEN** one full discovery runs, and the tests in that folder lose their run markers

#### Scenario: Deleted suite folder

- **WHEN** the user deletes a folder with suite files
- **THEN** a full discovery runs, and run markers and context runs no longer know the suites of that folder

#### Scenario: Refresh action

- **WHEN** the user chooses Tools | RobotCode | Refresh Robot Framework Tests
- **THEN** a full discovery runs

### Requirement: Single-file and skipped discoveries

The plugin SHALL rediscover a single suite file when the file's content changes. It SHALL NOT start a discovery when a file is only opened or closed, when only a setting that discovery does not use changes, or for files of another open project. Several triggers within half a second SHALL lead to one full discovery.

#### Scenario: Opening and closing a file

- **WHEN** the user opens a suite file and closes it again without changing it
- **THEN** no discover process starts

#### Scenario: Setting used only by the language server

- **WHEN** the user changes "Header style" on the Editing page and applies
- **THEN** no discover process starts

#### Scenario: Another open project

- **WHEN** two projects are open and the user edits the robot.toml of the first one
- **THEN** no discovery runs in the second project

### Requirement: Discovery stays consistent

The plugin SHALL run at most one full discovery of a project at a time. A newer full discovery SHALL cancel a running one and end its process. Run markers and context runs SHALL always use one complete result of discovery, and a cancelled or failed discovery SHALL leave the previous result in place. Fields in robotcode's discovery output that the plugin does not know SHALL be ignored.

#### Scenario: Discovery cancelled by a newer one

- **WHEN** a full discovery is running and another trigger requests a full discovery
- **THEN** the process of the running discovery ends, the markers of the previous result stay until the new discovery has finished, and then show its result

#### Scenario: Unknown field in the output

- **WHEN** robotcode's discovery output contains a field that the plugin does not know
- **THEN** the run markers are shown as for the same output without that field

### Requirement: Discovery failures are reported

When discovery fails, because robotcode exits with an error or prints output that the plugin cannot read, the plugin SHALL keep the result of the last successful discovery, write the command line, the exit code and the complete output to idea.log, and not raise an IDE error. Unless the selection names a profile that `robot.toml` does not define, it SHALL show a RobotCode notification with the first lines of robotcode's error output and the actions "Retry" and, when the project folder has a `robot.toml`, "Open robot.toml".

#### Scenario: Syntax error in robot.toml

- **WHEN** the user saves robot.toml with a syntax error such as `output-dir = [`
- **THEN** one RobotCode notification shows robotcode's error about the invalid TOML file, the run markers of the last discovery stay, and idea.log gets no SEVERE entry from RobotCode

#### Scenario: Retry

- **WHEN** the user clicks "Retry" in the notification
- **THEN** a full discovery runs

### Requirement: Repeated and fixed discovery failures

While a notification for the same discovery failure is shown, a repeated failure SHALL NOT add another one, and a successful discovery SHALL remove the notification.

#### Scenario: Further edits while the error remains

- **WHEN** the user then edits a suite file twice while robot.toml still has the error
- **THEN** no second notification appears

#### Scenario: Error fixed

- **WHEN** the user fixes robot.toml
- **THEN** discovery runs, the run markers follow the new result, and the notification disappears

### Requirement: Problems of suite files show at their markers

When discovery reports problems for a suite file, the tooltip of the file's run marker on line 1 SHALL show them. A file that Robot Framework cannot turn into a suite SHALL get a marker on line 1 whose tooltip shows the problem, without run actions.

#### Scenario: File with tests and tasks

- **WHEN** a `.robot` file has both a `*** Test Cases ***` and a `*** Tasks ***` section
- **THEN** line 1 of the file shows a marker whose tooltip says that a file cannot have both tests and tasks

#### Scenario: Problem in a suite with tests

- **WHEN** a suite file sets `Test Template` twice and still has tests
- **THEN** the tooltip of its line 1 run marker shows that the setting is allowed only once, and the run actions stay

### Requirement: Run markers while indexing

The run markers of discovered tests, tasks and suites SHALL stay in the editor gutter while the IDE indexes the project, as long as discovery has a result for the file.

#### Scenario: Markers during indexing

- **WHEN** a suite file with discovered tests is open and the IDE starts indexing the project
- **THEN** the run markers of the file stay visible, and their Run and Debug actions work

### Requirement: Discovery uses the paths of the Robot settings

The full discovery and the discovery of a single suite file SHALL pass `-dp` for each entry of "Paths" on the "Robot" settings page, or `-dp .` when there is none, before the `discover` command. The profile list SHALL pass the same `-dp` arguments.

#### Scenario: Paths

- **WHEN** `robot.toml` sets no paths, the project has the folders `tests` and `examples` with suites, and "Paths" is `tests`
- **THEN** discovery and the profile list pass `-dp tests`, and run markers appear in the suites below `tests` and not in those below `examples`

#### Scenario: No paths

- **WHEN** "Paths" is empty
- **THEN** discovery passes `-dp .`, as before

### Requirement: Discovery arguments from the Robot settings

After the discover subcommand, the full discovery and the discovery of a single suite file SHALL pass `--rpa` or `--norpa` for "Mode" unless it is "Default", `-P` for each entry of "Python path" and then for each root that the switches of the "Robot" page add, `--language` for each language, and the args. Variables, variable files and environment variables of the "Robot" page SHALL NOT be passed to discovery, as in VS Code.

#### Scenario: Settings for discovery

- **WHEN** "Mode" is "RPA", "Python path" is `libs`, both root switches are off, "Languages" is `de`, and "Args" is `--exclude wip`
- **THEN** the full discovery's command line contains `--rpa -P libs --language de --exclude wip` after the discover subcommand

#### Scenario: Roots for discovery

- **WHEN** "Python path" is `libs`, and the module whose interpreter RobotCode uses has the content root `/p` and the source root `/p/src`, with both switches on
- **THEN** the full discovery's command line contains `-P libs -P /p -P /p/src` after the discover subcommand

### Requirement: Single-file rediscovery in a project with several paths

The plugin SHALL rediscover a single suite file without a full discovery also when the project has several test paths, from "Paths" on the "Robot" settings page or from `robot.toml`. The tests and tasks of the file SHALL keep their run markers, and a run from a marker SHALL run its test or task.

#### Scenario: Edit in a project with several paths

- **WHEN** `robot.toml` sets `paths = ["electron", "vscode"]` and `run-empty-suite = true`, and the user adds a test to `vscode/open_vs_code.robot`
- **THEN** one discover process runs for that file and no full discovery, and the gutter shows a run marker at the new test

#### Scenario: Run from a marker after the edit

- **WHEN** after that edit the user runs a test of `vscode/open_vs_code.robot` from its run marker
- **THEN** Robot Framework runs that one test

### Requirement: A discovery that fails because of the selection reports the selection

When discovery fails while the project's selection names a profile or pattern that selects no profile of `robot.toml`, the plugin SHALL show the notification about the selected profile instead of the notification about the failed discovery.

#### Scenario: Selection with a renamed profile

- **WHEN** `dev` is selected, `robot.toml` renames it to `development`, and discovery runs
- **THEN** one notification names `dev`, with "Remove from Selection" and "Select Configuration Profiles...", and no notification about the failed discovery appears
