# Spec Delta

## Purpose

Defines what a Robot Framework run configuration of the IntelliJ plugin runs, how it is stored, edited, shared and reused, and which arguments its runs pass to `robotcode` and Robot Framework.

## ADDED Requirements

### Requirement: The configuration profiles option

The editor of a Robot Framework run configuration SHALL offer "Configuration profiles" under "Modify options", in its Robot Framework section, with the choices "Project selection", "Default profiles of robot.toml" and "Custom". For "Custom", it SHALL show the chosen profile names and a button that opens a list of the profiles `robot.toml` defines, without hidden profiles, with their descriptions and with the configuration's names checked. The choice and the names SHALL be stored with the configuration, in saved and temporary configurations, in the template and in configurations stored as project files, and a copy of a configuration SHALL have the same choice. A configuration stored before this option existed SHALL open with "Project selection".

#### Scenario: Custom profiles survive a restart

- **WHEN** the user shows "Configuration profiles" through "Modify options", chooses "Custom", checks `ci` in the list, applies and restarts the IDE
- **THEN** the editor shows "Custom" with `ci`, and a run of the configuration contains `-p ci`

#### Scenario: Stored as a project file

- **WHEN** a configuration with the choice "Custom" and `ci` is stored as a project file
- **THEN** the file under `.run/` holds the choice and `ci`

#### Scenario: Configuration of an earlier version

- **WHEN** a configuration saved before this option existed is opened
- **THEN** its choice is "Project selection"
