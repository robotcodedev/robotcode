# Spec Delta

## Purpose

Defines how the IntelliJ plugin presents the results of a Robot Framework run: the events that become results in the test tree, the details of failures, rerunning tests, and access to the files the run writes.

## ADDED Requirements

### Requirement: Opening the report or the log after a run

When a run ends and the effective "open after run" value is "Report" or "Log", the plugin SHALL open the report or the log file that the run wrote in the external browser. With "Nothing", and when the run wrote no such file, it SHALL open nothing and report no error.

#### Scenario: Report after a run

- **WHEN** a configuration sets "open after run" to "Report" and the run ends
- **THEN** the run's `report.html` opens in the external browser

#### Scenario: Default

- **WHEN** neither the configuration nor the project default changes "open after run" and the run ends
- **THEN** no file opens

#### Scenario: No log written

- **WHEN** "open after run" is "Log" and the robot arguments contain `--log NONE`
- **THEN** no file opens and no error is reported

### Requirement: Open Report and Open Log actions

The tab of a Robot Framework run, started with Run or with Debug, SHALL offer "Open Report" and "Open Log". Each SHALL be enabled once the run has reported that it wrote the file, and SHALL open the file in the external browser.

#### Scenario: Opening the log from the run tab

- **WHEN** a run of the test project has ended and the user clicks "Open Log" in its tab
- **THEN** the run's `log.html` opens in the external browser

#### Scenario: While the run is going

- **WHEN** a run is still going
- **THEN** "Open Report" and "Open Log" are disabled
