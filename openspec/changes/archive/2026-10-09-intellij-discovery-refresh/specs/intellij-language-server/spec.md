# Spec Delta

## Purpose

Defines how the IntelliJ plugin runs the RobotCode language server: when it starts, how it is connected, stopped and restarted, what it receives at start, where its output goes, and how users control and observe it.

## ADDED Requirements

### Requirement: The language server restarts when its inputs change

The plugin SHALL restart the language server of a project when something the running server received at start has changed: the settings it reads, its command line, environment or working directory, or its initialization options. It SHALL also restart it when `robot.toml`, `.robot.toml`, `pyproject.toml`, `robocop.toml`, `.gitignore` or `.robotignore` in the project is created, changed or deleted. Several changes within half a second SHALL lead to one restart.

#### Scenario: Setting the server reads

- **WHEN** the user changes "Header style" on the Editing page and applies
- **THEN** the language server restarts once

#### Scenario: Several pages applied together

- **WHEN** the user changes settings on two RobotCode pages and presses OK
- **THEN** the language server restarts once

### Requirement: Changes that do not restart the language server

A settings change that leaves all inputs of the running language server unchanged SHALL NOT restart the server, and changes in another open project SHALL NOT restart it.

#### Scenario: Setting the server does not use

- **WHEN** the user changes the additional robotcode arguments, which only discovery and the profile list receive, and applies
- **THEN** the language server does not restart

#### Scenario: Configuration file of another project

- **WHEN** two projects are open and the user edits the robot.toml of the first one
- **THEN** only the language server of the first project restarts

### Requirement: Settings changed outside the settings dialog

Changes of the stored settings from outside the settings dialog, such as a VCS update, SHALL be handled like changes applied in the dialog.

#### Scenario: Settings changed by a VCS update

- **WHEN** a VCS update changes the header style in the project's `.idea/robotcodeSettings.xml`
- **THEN** the language server restarts with the new value
