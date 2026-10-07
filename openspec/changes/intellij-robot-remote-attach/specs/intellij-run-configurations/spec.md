# Spec Delta

## Purpose

Defines what a Robot Framework run configuration of the IntelliJ plugin runs or attaches to, how it is stored, edited, shared and reused, and which arguments its runs pass to `robotcode` and Robot Framework.

## ADDED Requirements

### Requirement: The attach configuration

The Robot Framework configuration type SHALL offer a "Robot Framework (Attach)" configuration with a host, `127.0.0.1` by default, a port, `6612` by default, and a list of path mappings, each from a local folder to a folder on the side of the run, empty by default. Its editor SHALL say how to start a run that it can attach to.

#### Scenario: New attach configuration

- **WHEN** the user adds a "Robot Framework (Attach)" configuration
- **THEN** its editor shows the host `127.0.0.1`, the port `6612`, an empty list of path mappings and a hint how to start a run with `robotcode debug`

### Requirement: The attach configuration only debugs

A "Robot Framework (Attach)" configuration SHALL start no process and SHALL NOT offer interpreter, environment, working directory or Robot Framework options. The attach configuration SHALL be startable only with Debug. Gutter and context runs SHALL keep creating run configurations, not attach configurations.

#### Scenario: Debug only

- **WHEN** the user selects a "Robot Framework (Attach)" configuration in the run widget
- **THEN** Debug is available and Run is not

#### Scenario: Gutter run

- **WHEN** a project has an attach configuration and the user runs a test from the gutter
- **THEN** a Robot Framework run configuration for that test is created and run

### Requirement: Storing and checking the attach configuration

A "Robot Framework (Attach)" configuration SHALL be stored, shared as a project file and copied like the other Robot Framework configurations. Before it starts, a blank host, a port outside 1 to 65535 or a path mapping with an empty folder SHALL be reported as an error of the configuration.

#### Scenario: Invalid port

- **WHEN** the port of an attach configuration is set to `70000`
- **THEN** the configuration is marked with an error and cannot be started

#### Scenario: Stored configuration

- **WHEN** the user saves an attach configuration with the host `buildhost`, the port `7000` and one path mapping, and restarts the IDE
- **THEN** the configuration shows the same host, port and mapping
