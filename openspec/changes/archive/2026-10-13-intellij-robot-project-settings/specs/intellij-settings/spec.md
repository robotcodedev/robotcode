# Spec Delta

## ADDED Requirements

### Requirement: Robot page

The Robot Framework settings node SHALL have a "Robot" sub-page, for VS Code's "Robot" category, with the settings Args (a command line), Paths, Python path, Languages and Variable files (lists), Env and Variables (name and value pairs), Output dir (a folder) and Mode ("Default", which passes nothing, "RPA" for `--rpa` or "Test automation" for `--norpa`). All are empty by default, and the mode is "Default".

#### Scenario: Labels as in VS Code

- **WHEN** the user opens the "Robot" sub-page
- **THEN** the settings appear as "Args", "Paths", "Python path", "Env", "Languages", "Variables", "Variable files", "Output dir" and "Mode", without groups

#### Scenario: Library on an extra Python path

- **WHEN** a suite imports the Python library `mylib`, which lives only in the folder `libs`, and the user adds `libs` to "Python path" and applies
- **THEN** the editor no longer reports the import as unresolved, and the library's keywords are completed

#### Scenario: Variable for analysis

- **WHEN** a suite uses `${SERVER}`, no file defines it, and the user adds the variable `SERVER` with the value `localhost` under "Variables" and applies
- **THEN** the editor no longer reports `${SERVER}` as not found

### Requirement: How the Robot settings are used

The language server SHALL receive the settings of the "Robot" page in `robotcode.robot`, under VS Code's keys, with maps from strings to strings and lists without blank entries; test discovery and runs SHALL use them as described for them. Applying a change SHALL restart the language server, and SHALL run test discovery again when the change alters the arguments that discovery passes.

#### Scenario: Language server payload

- **WHEN** `MODE=test` is set under "Env" and `SERVER=localhost` under "Variables"
- **THEN** the server receives `robotcode.robot.env` as `{"MODE": "test"}` and `robotcode.robot.variables` as `{"SERVER": "localhost"}`

#### Scenario: Output directory

- **WHEN** "Output dir" is `results/ide` and the user runs a test from the gutter, with no output directory in the run configuration
- **THEN** `output.xml`, `log.html` and `report.html` are written to `results/ide`

#### Scenario: Mode passed to discovery

- **WHEN** the user sets "Mode" to "RPA" and applies
- **THEN** test discovery runs again with `--rpa`

### Requirement: Texts of the Robot page

The texts of the "Robot" page SHALL say that lists add to those of `robot.toml`, that variables set there win over `robot.toml`, that environment variables set there win in the editor while `robot.toml`'s environment wins in runs, that paths are used only when `robot.toml` sets no paths and a run names no files or folders, and that run configurations can set their own values.

#### Scenario: Text on variables

- **WHEN** the user opens the "Robot" sub-page
- **THEN** the text of "Variables" says that variables set there win over `robot.toml`

#### Scenario: Text on paths

- **WHEN** the user opens the "Robot" sub-page
- **THEN** the text of "Paths" says that the paths are used only when `robot.toml` sets no paths and a run names no files or folders

### Requirement: Robot settings are stored with the project

The settings of the "Robot" page SHALL be stored in the project's shared settings file `.idea/robotcodeSettings.xml`, and only when they differ from their defaults. A settings file without them SHALL yield the defaults.

#### Scenario: Values survive a restart

- **WHEN** the user adds `libs` to "Python path", applies and restarts the IDE
- **THEN** the page shows `libs`, and `.idea/robotcodeSettings.xml` holds it

## MODIFIED Requirements

### Requirement: Settings for new projects

The Robot Framework settings pages that hold shared settings SHALL be available under File | New Projects Setup | Settings for New Projects, and the values set there SHALL be used for projects created afterwards. Pages with settings stored for the current user only, such as the extra arguments and the profile selection, SHALL NOT be offered there. Applying settings there SHALL NOT start, stop or restart a language server, and SHALL NOT run test discovery.

#### Scenario: Preset for a new project

- **WHEN** the user sets "Header style" to `*** {name}` on the Editing page under Settings for New Projects, applies, and then creates a new project
- **THEN** the Editing page of the new project shows `*** {name}`

#### Scenario: Personal settings are not offered

- **WHEN** the user opens the "Robot Framework" node under Settings for New Projects
- **THEN** it lists the Analysis, Editing, Robocop and Robot pages, and not the General and Language Server pages

#### Scenario: Apply starts nothing

- **WHEN** the user changes a value under Settings for New Projects and applies
- **THEN** no `robotcode` process starts
