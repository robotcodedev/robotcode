# Spec Delta

## MODIFIED Requirements

### Requirement: Debug page with the project defaults for runs

The Robot Framework settings node SHALL have a "Debug" sub-page with these project defaults for the runs of Robot Framework run configurations:

- "Launch wrapper", a command line; when it is empty, the wrapper of the selected `robot.toml` profile applies;
- "Output messages", off by default;
- "Output log", on by default;
- "Output timestamps", off by default;
- "Attach Python", off by default.

#### Scenario: Opening the Debug page

- **WHEN** the user opens Settings | Languages & Frameworks | Robot Framework | Debug in a project without stored RobotCode settings
- **THEN** the page shows an empty "Launch wrapper", "Output log" on, "Output messages", "Output timestamps" and "Attach Python" off, and no field for `robotcode` arguments, stop on entry or a connection timeout

#### Scenario: Searching for the wrapper

- **WHEN** the user types "wrapper" into the search field of the settings dialog
- **THEN** the Debug page is found

#### Scenario: Project default for Attach Python

- **WHEN** the user switches "Attach Python" on and applies, and starts a configuration that uses "Project default" for "Attach Python" with Debug
- **THEN** the run also starts PyCharm's Python debugger, and the language server keeps running
