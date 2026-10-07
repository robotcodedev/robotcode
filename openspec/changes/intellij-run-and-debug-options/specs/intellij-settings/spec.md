# Spec Delta

## Purpose

Defines the Robot Framework settings pages of the IntelliJ plugin and the settings the RobotCode language server receives from the plugin, so that the server behaves as with VS Code's defaults unless the user changes a setting.

## ADDED Requirements

### Requirement: Run & Debug page with the project defaults for runs

The Robot Framework settings node SHALL have a "Run & Debug" sub-page with these project defaults for Robot Framework runs:

- the launch wrapper, a command line; when it is empty, the wrapper of the selected `robot.toml` profile applies;
- Robot Framework messages in the debugger output, off by default;
- log messages in the debugger output, on by default;
- timestamps in the debugger output, off by default;
- what to open after a run: "Nothing", "Report" or "Log", "Nothing" by default.

#### Scenario: Opening the page

- **WHEN** the user opens Settings | Languages & Frameworks | Robot Framework | Run & Debug in a project without stored RobotCode settings
- **THEN** the page shows an empty launch wrapper, log messages on, messages and timestamps off, and "Nothing" to open after a run, and no field for `robotcode` arguments, stop on entry or a connection timeout

#### Scenario: Searching for the wrapper

- **WHEN** the user types "wrapper" into the search field of the settings dialog
- **THEN** the Run & Debug page is found

### Requirement: Options the Run & Debug page leaves to run configurations

The "Run & Debug" page SHALL NOT offer `robotcode` arguments, stop on entry or a connection timeout; these are options of a run configuration only.

#### Scenario: Options only in the run configuration

- **WHEN** the user looks for stop on entry
- **THEN** the "Run & Debug" page has no field for it, and the "Modify options" of a Robot Framework run configuration offer it

### Requirement: Storage of the Run & Debug defaults

The values of the "Run & Debug" page SHALL be stored with the project's shared RobotCode settings. They SHALL NOT be part of the settings tree the language server receives, and applying the page SHALL NOT restart the language server.

#### Scenario: Applying the page

- **WHEN** the user changes the launch wrapper and applies
- **THEN** the language server keeps running, and the next run uses the new wrapper
