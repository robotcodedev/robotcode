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
