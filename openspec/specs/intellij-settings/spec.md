# intellij-settings Specification

## Purpose

Defines the Robot Framework settings pages of the IntelliJ plugin and the settings the RobotCode language server receives from the plugin, so that the server behaves as with VS Code's defaults unless the user changes a setting.

## Requirements

### Requirement: Robot Framework settings node with an Editing page

The IntelliJ plugin SHALL provide a "Robot Framework" node under Settings | Languages & Frameworks for every project, with an "Editing" sub-page. While the node has no settings of its own, its page SHALL list its sub-pages instead of showing text. No RobotCode settings page SHALL show a work-in-progress notice or a field that has no effect. Every setting SHALL have a description in plain text, without markdown syntax.

#### Scenario: Opening the settings

- **WHEN** the user opens Settings | Languages & Frameworks | Robot Framework
- **THEN** the page lists the Editing sub-page, the tree shows the Editing sub-page below the node, and neither page shows a work-in-progress notice or the former "Arguments" and "Mode" fields

#### Scenario: Searching for a setting

- **WHEN** the user types "Header Style" into the search field of the settings dialog
- **THEN** the Editing sub-page of the Robot Framework node is found

### Requirement: The language server receives the complete settings tree

The plugin SHALL answer the language server's `workspace/configuration` requests, and send `workspace/didChangeConfiguration`, with one complete `robotcode` settings tree. The tree SHALL contain every setting that VS Code offers in the sections the server reads: the value from the settings pages where the plugin offers the setting, and VS Code's default otherwise.

#### Scenario: Every section is answered

- **WHEN** the language server requests `robotcode`, `robotcode.robot`, `robotcode.analysis`, `robotcode.analysis.cache`, `robotcode.analysis.robot`, `robotcode.analysis.diagnosticModifiers`, `robotcode.completion`, `robotcode.inlayHints`, `robotcode.robocop`, `robotcode.documentationServer` or `robotcode.experimental`
- **THEN** the plugin answers with an object, not with `null`

#### Scenario: Defaults of a project without RobotCode settings

- **WHEN** the settings tree of a project without stored RobotCode settings is compared with VS Code's defaults for the same keys
- **THEN** both are equal, apart from `robotcode.documentationServer.startOnDemand`, which is `true`, and `robotcode.inlayHints.parameterNames` and `robotcode.inlayHints.namespaces`, which are `false`

#### Scenario: Default exclude patterns

- **WHEN** a project has no stored RobotCode settings
- **THEN** `robotcode.workspace.excludePatterns` holds VS Code's default patterns `.hatch/`, `.venv/`, `node_modules/`, `.pytest_cache/`, `__pycache__/`, `.mypy_cache/` and `.robotcode_cache/`, and the server does not load Robot Framework files below these folders

### Requirement: Value types in the settings tree

Values in the `robotcode` settings tree SHALL have the types the server parses: JSON booleans, integers, the exact enum strings, maps from strings to strings, and lists without `null` or empty entries.

#### Scenario: Value types

- **WHEN** the language server receives the `robotcode` settings tree
- **THEN** every boolean in it is a JSON boolean, every number is an integer, and no list holds `null` or an empty entry

### Requirement: Exceptions in the settings tree

The only exceptions to VS Code's defaults in the `robotcode` settings tree SHALL be `robotcode.documentationServer.startOnDemand`, which is always `true` because the plugin has no documentation viewer, and the two inlay hint flags, which are `false` unless the user switches them on. Settings that only the clients use, for example for the debugger, runs, profiles or the language server process, SHALL NOT be part of the tree.

#### Scenario: Documentation server on demand

- **WHEN** the language server starts in IntelliJ
- **THEN** it does not start its documentation server until something needs a documentation URL

#### Scenario: Settings only the clients use

- **WHEN** the language server requests the `robotcode` section
- **THEN** the answer holds no settings for the debugger, runs, profiles or the language server process

### Requirement: Completion settings take effect

The Editing page SHALL offer "Filter default language", "Header style", "Hide private keywords" and "Hide deprecated keywords", and the language server SHALL use their values after the user applies them. The header style SHALL be sent only when it is not blank. Otherwise the server uses its default: `*** {name} ***` from Robot Framework 6 on, and `*** {name}s ***` before.

#### Scenario: Custom header style

- **WHEN** the user sets "Header style" to `*** {name}`, applies, and completes a section header in a suite file
- **THEN** the inserted header follows that style, for example `*** Test Cases`

#### Scenario: Blank header style

- **WHEN** the user clears "Header style" and applies
- **THEN** section header completion uses the server's default header style

#### Scenario: Filtering the default language

- **WHEN** "Filter default language" is on and a suite file starts with `Language: German`
- **THEN** section header completion offers the German headers, such as `*** Testfälle ***`, and no English ones

#### Scenario: Showing private keywords

- **WHEN** the user switches off "Hide private keywords", applies, and completes a keyword in a suite that imports a resource file with a private keyword
- **THEN** completion offers the private keyword, marked as private

#### Scenario: Hiding deprecated keywords

- **WHEN** the user switches on "Hide deprecated keywords" and applies
- **THEN** keyword completion offers no deprecated keywords

### Requirement: Inlay hints are off by default

The inlay hints for parameter names and for namespaces SHALL be off by default, unlike in VS Code and on the language server: IntelliJ shows inlay hints all the time once they are on, and has no mode that shows them only while a key is held, as VS Code can. Each SHALL be possible to switch on from the Editing page. The Editing page SHALL point to Settings | Editor | Inlay Hints, where the display of the hints can be switched off as well.

#### Scenario: Project without RobotCode settings

- **WHEN** a project without stored RobotCode settings shows a keyword call with positional arguments, such as `Should Be Equal    ${a}    ${b}`
- **THEN** the editor shows no inlay hints

#### Scenario: Switching parameter names on

- **WHEN** the user switches on "Parameter names" on the Editing page and applies
- **THEN** the editor shows the parameter names of the arguments as inlay hints, and no namespace hints

### Requirement: Stored settings stay valid

The values that earlier versions of the plugin stored in the project's `.idea/robotcodeSettings.xml` SHALL keep their meaning, and the plugin SHALL send them to the language server.

#### Scenario: Settings stored by an earlier version

- **WHEN** a project's `robotcodeSettings.xml`, written by an earlier plugin version, holds a header style and "Filter default language" switched on
- **THEN** the Editing page shows both values, and the language server receives them

### Requirement: Analysis page

The Robot Framework settings node SHALL have an "Analysis" sub-page with these settings, and the language server SHALL use their values after the user applies them:

- diagnostic mode: "Open files only", the default, or "Workspace";
- progress mode: "Off", the default, "Simple" or "Detailed";
- find unused references, off by default;
- references code lens, off by default.

#### Scenario: References code lens

- **WHEN** the user switches the references code lens on and applies
- **THEN** keyword definitions in Robot Framework files show the number of references, such as "2 references", above the definition

#### Scenario: Unused references

- **WHEN** the user switches find unused references on and applies, and a suite file defines a keyword that nothing calls
- **THEN** the editor marks that keyword with the message "Keyword '<name>' is not used."

#### Scenario: Workspace diagnostic mode

- **WHEN** the diagnostic mode is "Workspace" and a Robot Framework file that is not open in an editor contains an error
- **THEN** the server reports the problems of that file, and IntelliJ marks the file as a problem file

### Requirement: Cache and library settings of the Analysis page

The "Analysis" sub-page SHALL also have these settings, and the language server SHALL use their values after the user applies them:

- save location of the cache: "IDE system directory", the default, or "Project folder";
- ignored libraries, ignored variables and libraries whose arguments are ignored, all empty by default;
- global library search order, empty by default;
- load library timeout in seconds: a whole number from 1 to 3600, or empty, which is the default.

#### Scenario: Default save location

- **WHEN** the user opens the "Analysis" sub-page of a project without stored settings
- **THEN** the save location is "IDE system directory"

### Requirement: Diagnostic modifiers on the Analysis page

The "Analysis" sub-page SHALL have five lists of diagnostic codes, all empty by default: ignore, error, warning, information and hint. The language server SHALL use them after the user applies them.

#### Scenario: Ignoring a diagnostic code

- **WHEN** the user adds `KeywordNotFound` to the ignore list and applies
- **THEN** a call of a keyword that does not exist is no longer marked

### Requirement: Workspace and experimental settings on the Analysis page

The "Analysis" sub-page SHALL have the exclude patterns, by default VS Code's seven patterns `.hatch/`, `.venv/`, `node_modules/`, `.pytest_cache/`, `__pycache__/`, `.mypy_cache/` and `.robotcode_cache/`, and the experimental semantic model, off by default. The language server SHALL use their values after the user applies them.

#### Scenario: Excluding a folder

- **WHEN** the user adds `generated/` to the exclude patterns and applies
- **THEN** Find Usages of a project keyword no longer lists calls in Robot Framework files below `generated/`

#### Scenario: Removing all exclude patterns

- **WHEN** the user removes every exclude pattern, applies and reopens the project
- **THEN** the list is still empty, and the server receives an empty `robotcode.workspace.excludePatterns`

### Requirement: Values of the Analysis page

An empty load library timeout SHALL NOT be sent to the server. The "Analysis" sub-page SHALL reject a timeout outside 1 to 3600 and SHALL NOT send list entries that are blank.

#### Scenario: Empty load library timeout

- **WHEN** the load library timeout is empty
- **THEN** the settings tree contains no `loadLibraryTimeout`, and the timeout from `robot.toml` or the server's default applies

#### Scenario: Invalid load library timeout

- **WHEN** the user enters `0` as load library timeout
- **THEN** the page shows an error and the value is not stored

#### Scenario: Blank entry in a modifier list

- **WHEN** the user adds a blank entry to the ignore list and applies
- **THEN** the server receives the ignore list without the blank entry

### Requirement: Texts of the Analysis page

The texts of the "Analysis" sub-page SHALL say that the list entries are added to those in `robot.toml` (`[tool.robotcode-analyze]`, for the diagnostic modifiers `[tool.robotcode-analyze.modifiers]`), that a load library timeout replaces the one from `robot.toml`, that exclude patterns use `.gitignore` syntax, and that the save location "Project folder" is the folder `robotcode analyze` uses in the project.

#### Scenario: Text on exclude patterns

- **WHEN** the user opens the "Analysis" sub-page
- **THEN** its text says that exclude patterns use `.gitignore` syntax

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

- Robocop analysis enabled, on by default;
- config file, none by default;
- ignore Git dir, off by default;
- ignore file config, off by default.

The config file SHALL be sent as an absolute path, and the page SHALL reject a path to a file that does not exist.

#### Scenario: Switching Robocop off

- **WHEN** Robocop is installed in the project's interpreter and the user switches Robocop analysis off and applies
- **THEN** Robocop's diagnostics disappear, and the other RobotCode diagnostics stay

#### Scenario: Config file

- **WHEN** the user chooses a Robocop configuration file that ignores a Robocop rule and applies
- **THEN** diagnostics of that rule disappear

#### Scenario: Missing config file

- **WHEN** the user enters the path of a file that does not exist as config file
- **THEN** the page shows an error and the value is not stored

### Requirement: Text of the Robocop page

The text of the "Robocop" sub-page SHALL say that switching Robocop analysis off removes Robocop's diagnostics but does not switch off formatting with Robocop.

#### Scenario: Text on formatting

- **WHEN** the user opens the "Robocop" sub-page
- **THEN** its text says that switching Robocop analysis off does not switch off formatting with Robocop

### Requirement: Labels of the settings pages follow VS Code

A setting on the pages of the Robot Framework settings node that VS Code also offers SHALL be labelled with the words of its VS Code setting title, the title VS Code derives from the setting key, in sentence case. Groups SHALL be named after the parts of the key that VS Code shows before the title, and the settings of one VS Code settings category SHALL be on one page.

#### Scenario: Cache setting

- **WHEN** the user opens the "Analysis" sub-page
- **THEN** the setting `robotcode.analysis.cache.ignoredLibraries` appears as "Ignored libraries" in the group "Cache"

### Requirement: Analysis settings are stored with the project

The values of the Analysis and Robocop pages SHALL be stored in the project's RobotCode settings file `.idea/robotcodeSettings.xml`, and only when they differ from their defaults. A settings file without these values SHALL yield the defaults, and the values stored before SHALL keep their meaning.

#### Scenario: Values survive a restart

- **WHEN** the user changes the diagnostic mode to "Workspace", applies and restarts the IDE
- **THEN** the Analysis page shows "Workspace", and the server receives `workspace` as diagnostic mode

#### Scenario: Settings file of an earlier version

- **WHEN** a project's `robotcodeSettings.xml` was written by an earlier plugin version
- **THEN** the Analysis and Robocop pages show the defaults, and the Editing page keeps its stored values

### Requirement: One restart per Apply

When the user changed settings on several RobotCode pages that each restart the language server on Apply, pressing OK or Apply SHALL restart the language server once, not once per page.

#### Scenario: Two pages changed

- **WHEN** the user changes a value on the Analysis page and on the Robocop page and presses OK
- **THEN** the language server restarts once, and the new server uses both values
