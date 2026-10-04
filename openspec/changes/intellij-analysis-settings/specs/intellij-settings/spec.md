# Spec Delta

## Purpose

Defines the Robot Framework settings pages of the IntelliJ plugin and the settings the RobotCode language server receives from the plugin, so that the server behaves as with VS Code's defaults unless the user changes a setting.

## ADDED Requirements

### Requirement: Analysis page

The Robot Framework settings node SHALL have an "Analysis" sub-page with these settings, and the language server SHALL use their values after the user applies them:

- references code lens, off by default;
- global library search order, empty by default;
- library load timeout in seconds: a whole number from 1 to 3600, or empty, which is the default;
- cache location: "IDE system directory", the default, or "Project folder";
- libraries and variable files that are not cached, and libraries whose arguments are ignored, all empty by default;
- exclude patterns, by default VS Code's seven patterns `.hatch/`, `.venv/`, `node_modules/`, `.pytest_cache/`, `__pycache__/`, `.mypy_cache/` and `.robotcode_cache/`;
- experimental semantic model, off by default.

An empty library load timeout SHALL NOT be sent to the server. The page SHALL reject a timeout outside 1 to 3600 and SHALL NOT send list entries that are blank. The page texts SHALL say that the list entries are added to those in `robot.toml` (`[tool.robotcode-analyze]`), that a library load timeout replaces the one from `robot.toml`, that exclude patterns use `.gitignore` syntax, and that the cache location "Project folder" is the folder `robotcode analyze` uses in the project.

#### Scenario: Excluding a folder

- **WHEN** the user adds `generated/` to the exclude patterns and applies
- **THEN** Find Usages of a project keyword no longer lists calls in Robot Framework files below `generated/`

#### Scenario: Removing all exclude patterns

- **WHEN** the user removes every exclude pattern, applies and reopens the project
- **THEN** the list is still empty, and the server receives an empty `robotcode.workspace.excludePatterns`

#### Scenario: Empty library load timeout

- **WHEN** the library load timeout is empty
- **THEN** the settings tree contains no `loadLibraryTimeout`, and the timeout from `robot.toml` or the server's default applies

#### Scenario: Invalid library load timeout

- **WHEN** the user enters `0` as library load timeout
- **THEN** the page shows an error and the value is not stored

#### Scenario: References code lens

- **WHEN** the user switches the references code lens on and applies
- **THEN** keyword definitions in Robot Framework files show the number of references, such as "2 references", above the definition

### Requirement: Diagnostics page

The Robot Framework settings node SHALL have a "Diagnostics" sub-page with these settings, and the language server SHALL use their values after the user applies them:

- diagnostic mode: "Open files only", the default, or "Workspace";
- progress mode: "Off", the default, "Simple" or "Detailed";
- find unused references, off by default;
- five diagnostic modifier lists of diagnostic codes, all empty by default: ignore, error, warning, information and hint.

The page texts SHALL say that the modifier lists are added to those in `robot.toml` (`[tool.robotcode-analyze.modifiers]`). The page SHALL NOT send blank list entries.

#### Scenario: Ignoring a diagnostic code

- **WHEN** the user adds `KeywordNotFound` to the ignore list and applies
- **THEN** a call of a keyword that does not exist is no longer marked

#### Scenario: Unused references

- **WHEN** the user switches find unused references on and applies, and a suite file defines a keyword that nothing calls
- **THEN** the editor marks that keyword with the message "Keyword '<name>' is not used."

#### Scenario: Workspace diagnostic mode

- **WHEN** the diagnostic mode is "Workspace" and a Robot Framework file that is not open in an editor contains an error
- **THEN** the server reports the problems of that file, and IntelliJ marks the file as a problem file

### Requirement: Information and Hint diagnostics are distinguishable

The plugin SHALL show diagnostics with severity Information as weak warnings, which the Problems view lists. Diagnostics with severity Hint SHALL use the IDE's information level: the Problems view does not list them, and their message appears on hover. Error and Warning diagnostics SHALL keep their levels, and the tags for unused and deprecated code SHALL keep their effect at every level. The texts of the information and hint modifier lists SHALL describe how these levels are shown in IntelliJ.

#### Scenario: Information diagnostic

- **WHEN** a diagnostic code is in the information modifier list and the open file contains such a problem
- **THEN** the editor marks the problem as a weak warning, and the Problems view lists it

#### Scenario: Hint diagnostic

- **WHEN** a diagnostic code is in the hint modifier list and the open file contains such a problem
- **THEN** the Problems view does not list the problem, and hovering over it shows its message

### Requirement: Robocop page

The Robot Framework settings node SHALL have a "Robocop" sub-page with these settings, and the language server SHALL use their values after the user applies them:

- enable Robocop analysis, on by default;
- configuration file, none by default;
- ignore Git directory, off by default;
- ignore file configuration, off by default.

The configuration file SHALL be sent as an absolute path, and the page SHALL reject a path to a file that does not exist. The page text SHALL say that switching Robocop analysis off removes Robocop's diagnostics but does not switch off formatting with Robocop.

#### Scenario: Switching Robocop off

- **WHEN** Robocop is installed in the project's interpreter and the user switches Robocop analysis off and applies
- **THEN** Robocop's diagnostics disappear, and the other RobotCode diagnostics stay

#### Scenario: Configuration file

- **WHEN** the user chooses a Robocop configuration file that ignores a Robocop rule and applies
- **THEN** diagnostics of that rule disappear

#### Scenario: Missing configuration file

- **WHEN** the user enters the path of a file that does not exist as configuration file
- **THEN** the page shows an error and the value is not stored

### Requirement: Analysis settings are stored with the project

The values of the Analysis, Diagnostics and Robocop pages SHALL be stored in the project's RobotCode settings file `.idea/robotcodeSettings.xml`, and only when they differ from their defaults. A settings file without these values SHALL yield the defaults, and the values stored before SHALL keep their meaning.

#### Scenario: Values survive a restart

- **WHEN** the user changes the diagnostic mode to "Workspace", applies and restarts the IDE
- **THEN** the Diagnostics page shows "Workspace", and the server receives `workspace` as diagnostic mode

#### Scenario: Settings file of an earlier version

- **WHEN** a project's `robotcodeSettings.xml` was written by an earlier plugin version
- **THEN** the Analysis, Diagnostics and Robocop pages show the defaults, and the Editing page keeps its stored values

### Requirement: One restart per Apply

When the user changed settings on several RobotCode pages that each restart the language server on Apply, pressing OK or Apply SHALL restart the language server once, not once per page.

#### Scenario: Two pages changed

- **WHEN** the user changes a value on the Analysis page and on the Robocop page and presses OK
- **THEN** the language server restarts once, and the new server uses both values
