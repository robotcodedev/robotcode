# Spec Delta

## ADDED Requirements

### Requirement: Debug page with the project defaults for runs

The Robot Framework settings node SHALL have a "Debug" sub-page with these project defaults for the runs of Robot Framework run configurations:

- "Launch wrapper", a command line; when it is empty, the wrapper of the selected `robot.toml` profile applies;
- "Output messages", off by default;
- "Output log", on by default;
- "Output timestamps", off by default.

#### Scenario: Opening the Debug page

- **WHEN** the user opens Settings | Languages & Frameworks | Robot Framework | Debug in a project without stored RobotCode settings
- **THEN** the page shows an empty "Launch wrapper", "Output log" on, "Output messages" and "Output timestamps" off, and no field for `robotcode` arguments, stop on entry or a connection timeout

#### Scenario: Searching for the wrapper

- **WHEN** the user types "wrapper" into the search field of the settings dialog
- **THEN** the Debug page is found

### Requirement: Run page with the project default for opening the output

The Robot Framework settings node SHALL have a "Run" sub-page with "Open output after run": "Nothing", "Report" or "Log", "Nothing" by default.

#### Scenario: Opening the Run page

- **WHEN** the user opens Settings | Languages & Frameworks | Robot Framework | Run in a project without stored RobotCode settings
- **THEN** the page shows "Open output after run" set to "Nothing"

### Requirement: Options the Run and Debug pages leave to run configurations

The "Run" and "Debug" pages SHALL NOT offer `robotcode` arguments, stop on entry or a connection timeout; these are options of a run configuration only.

#### Scenario: Options only in the run configuration

- **WHEN** the user looks for stop on entry
- **THEN** neither the "Run" nor the "Debug" page has a field for it, and the "Modify options" of a Robot Framework run configuration offer it

### Requirement: Storage of the Run and Debug defaults

The values of the "Run" and "Debug" pages SHALL be stored with the project's shared RobotCode settings. They SHALL NOT be part of the settings tree the language server receives, and applying the pages SHALL NOT restart the language server.

#### Scenario: Applying the Debug page

- **WHEN** the user changes "Launch wrapper" and applies
- **THEN** the language server keeps running, and the next run uses the new wrapper
