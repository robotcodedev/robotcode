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

### Requirement: Run page with the project defaults for opening the output

The Robot Framework settings node SHALL have a "Run" sub-page with "Open output after run": "Nothing", "Report" or "Log", "Nothing" by default; and "Open output target": "Built-in preview", "Default browser" or one of the active browsers of Settings | Tools | Web Browsers and Preview, "Built-in preview" by default.

#### Scenario: Opening the Run page

- **WHEN** the user opens Settings | Languages & Frameworks | Robot Framework | Run in a project without stored RobotCode settings
- **THEN** the page shows "Open output after run" set to "Nothing" and "Open output target" set to "Built-in preview"

#### Scenario: Choosing where the output opens

- **WHEN** the user opens the "Open output target" list on the Run page
- **THEN** it lists "Built-in preview", "Default browser" and the active browsers of Settings | Tools | Web Browsers and Preview, like the "Open In | Browser" menu of an HTML file

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

## MODIFIED Requirements

### Requirement: Settings for new projects

The Robot Framework settings pages that hold shared settings SHALL be available under File | New Projects Setup | Settings for New Projects, and the values set there SHALL be used for projects created afterwards. Pages with settings stored for the current user only, such as the extra arguments and the profile selection, SHALL NOT be offered there. Applying settings there SHALL NOT start, stop or restart a language server, and SHALL NOT run test discovery.

#### Scenario: Preset for a new project

- **WHEN** the user sets "Header style" to `*** {name}` on the Editing page under Settings for New Projects, applies, and then creates a new project
- **THEN** the Editing page of the new project shows `*** {name}`

#### Scenario: Personal settings are not offered

- **WHEN** the user opens the "Robot Framework" node under Settings for New Projects
- **THEN** it lists the Analysis, Debug, Editing, Robocop, Robot and Run pages, and not the General and Language Server pages

#### Scenario: Apply starts nothing

- **WHEN** the user changes a value under Settings for New Projects and applies
- **THEN** no `robotcode` process starts
