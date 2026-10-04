# Spec Delta

## Purpose

Defines which discovered Robot Framework tests, tasks and suites the IntelliJ plugin marks in the editor gutter, and how it keeps that model current when a single suite file is opened, closed or edited.

## ADDED Requirements

### Requirement: Discovery in a WSL project

For a project whose interpreter is a WSL interpreter, test discovery SHALL run inside the interpreter's distribution, and the discovered tests, tasks and suites SHALL get their run markers in the project's files as in a project with a local interpreter, for a project inside the distribution and for a project on a Windows drive. Discovery SHALL use the unsaved content of open Robot files, as it does with a local interpreter.

#### Scenario: Run markers in a project inside WSL

- **WHEN** a project inside the distribution "Ubuntu" whose interpreter is a WSL interpreter, with three tests in `tests/sample.robot`, is opened
- **THEN** discovery runs inside "Ubuntu", and the three tests and the suite get run markers in the gutter of `tests/sample.robot`

#### Scenario: Unsaved test

- **WHEN** the user adds a test to an open suite of that project without saving the file
- **THEN** after the next discovery the new test has a run marker

#### Scenario: Project on a Windows drive

- **WHEN** a project in `C:\work\robot-project` whose interpreter is a WSL interpreter is opened
- **THEN** the tests of its suites get run markers in the gutter
