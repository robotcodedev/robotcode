# Spec Delta

## Purpose

Defines the Robot Framework settings pages of the IntelliJ plugin and the settings the RobotCode language server receives from the plugin, so that the server behaves as with VS Code's defaults unless the user changes a setting.

## ADDED Requirements

### Requirement: Robot Framework environment settings

The "Robot Framework" settings page SHALL have a group "Robot Framework environment" with these settings, all empty by default:

- Python path: a list of folders or glob patterns;
- environment variables: name and value pairs;
- variables: name and value pairs;
- variable files: a list of files;
- languages: a list of language names or codes.

Applying a change SHALL restart the language server and run test discovery again.

#### Scenario: Library on an extra Python path

- **WHEN** a suite imports the Python library `mylib`, which lives only in the folder `libs`, and the user adds `libs` to the Python path and applies
- **THEN** the editor no longer reports the import as unresolved, and the library's keywords are completed

#### Scenario: Variable for analysis

- **WHEN** a suite uses `${SERVER}`, no file defines it, and the user adds the variable `SERVER` with the value `localhost` and applies
- **THEN** the editor no longer reports `${SERVER}` as not found

### Requirement: How the environment settings reach the server and runs

The language server SHALL receive the settings of the group "Robot Framework environment" in `robotcode.robot` as `pythonPath`, `env`, `variables`, `variableFiles` and `languages`, with maps from strings to strings and lists without blank entries, and runs SHALL get them as described for combining project settings with runs.

#### Scenario: Language server payload

- **WHEN** the environment variable `MODE=test` and the variable `SERVER=localhost` are set
- **THEN** the server receives `robotcode.robot.env` as `{"MODE": "test"}` and `robotcode.robot.variables` as `{"SERVER": "localhost"}`

### Requirement: Text of the environment settings group

The text of the group "Robot Framework environment" SHALL say that lists add to those of `robot.toml`, that variables set here win over `robot.toml`, and that environment variables set here win in the editor while `robot.toml`'s environment wins in runs.

#### Scenario: Text on variables

- **WHEN** the user opens the "Robot Framework" settings page
- **THEN** the group "Robot Framework environment" says that variables set there win over `robot.toml`

### Requirement: Robot Framework run options settings

The "Robot Framework" settings page SHALL have a group "Run options" with these settings:

- robot arguments, entered as a command line, empty by default;
- mode: "Default", which passes nothing and is the default, "RPA" (`--rpa`) or "Test automation" (`--norpa`);
- default paths: a list of files and folders, empty by default;
- output directory, empty by default.

#### Scenario: Output directory

- **WHEN** the output directory is `results/ide` and the user runs a test from the gutter, with no output directory in the run configuration
- **THEN** `output.xml`, `log.html` and `report.html` are written to `results/ide`

### Requirement: How the run options are used

Test discovery and runs SHALL use the settings of the group "Run options" as described for discovery and for combining project settings with runs; the language server receives them in `robotcode.robot` as well. Applying a change SHALL restart the language server and run test discovery again.

#### Scenario: Mode passed to discovery

- **WHEN** the user sets the mode to "RPA" and applies
- **THEN** test discovery runs again with `--rpa`

### Requirement: Text of the run options group

The text of the group "Run options" SHALL say that default paths are used only when `robot.toml` sets no paths and a run names no files or folders, and that run configurations can set their own values.

#### Scenario: Text on default paths

- **WHEN** the user opens the "Robot Framework" settings page
- **THEN** the group "Run options" says that default paths are used only when `robot.toml` sets no paths and a run names no files or folders

### Requirement: Robot settings are stored with the project

The Robot Framework environment and run options SHALL be stored in the project's shared settings file `.idea/robotcodeSettings.xml`, and only when they differ from their defaults. A settings file without them SHALL yield the defaults.

#### Scenario: Values survive a restart

- **WHEN** the user adds `libs` to the Python path, applies and restarts the IDE
- **THEN** the page shows `libs`, and `.idea/robotcodeSettings.xml` holds it
