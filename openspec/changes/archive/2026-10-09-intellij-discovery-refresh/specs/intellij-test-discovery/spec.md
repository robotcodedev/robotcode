# Spec Delta

## Purpose

Defines which discovered Robot Framework tests, tasks and suites the IntelliJ plugin marks in the editor gutter, when it discovers them again, and how it reports problems of discovery.

## ADDED Requirements

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

When discovery fails, because robotcode exits with an error or prints output that the plugin cannot read, the plugin SHALL keep the result of the last successful discovery, and SHALL show a RobotCode notification with the first lines of robotcode's error output and the actions "Retry" and, when the project folder has a `robot.toml`, "Open robot.toml". It SHALL write the command line, the exit code and the complete output to idea.log, and SHALL NOT raise an IDE error.

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
