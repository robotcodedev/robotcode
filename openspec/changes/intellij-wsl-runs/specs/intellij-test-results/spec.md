# Spec Delta

## Purpose

Defines how the IntelliJ plugin turns the events of a Robot Framework run into the results shown in the run tab: the results tree, test statuses and messages, and the output that belongs to each test.

## ADDED Requirements

### Requirement: Locations of a run inside WSL

For a run whose interpreter is a WSL interpreter, every location that the run reports to the plugin SHALL refer to the file as the IDE shows it: the location of each suite and test in the results tree, the sources of log messages and failed keywords, and the output, log and report files of the run. Navigating from the results tree SHALL open that file at the reported line, and after the run the gutter SHALL show the result state of each test that ran.

#### Scenario: Navigation from the results tree

- **WHEN** a run of `tests/sample.robot` with a WSL interpreter has finished and the user double-clicks the failed test in the results tree
- **THEN** the IDE opens the project's `tests/sample.robot` at the test's line

#### Scenario: Gutter states after the run

- **WHEN** that run has finished with one failed and two passed tests
- **THEN** the run markers of the three tests in `tests/sample.robot` show their result states

#### Scenario: Project on a Windows drive

- **WHEN** a run of a suite in `C:\work\robot-project` with a WSL interpreter has finished
- **THEN** navigating from the results tree opens the suite below `C:\work\robot-project`
