# Spec Delta

## Purpose

Defines the Robot Framework settings pages of the IntelliJ plugin and the settings the RobotCode language server receives from the plugin, so that the server behaves as with VS Code's defaults unless the user changes a setting.

## ADDED Requirements

### Requirement: Robot Framework settings node with an Editing page

The IntelliJ plugin SHALL provide a "Robot Framework" node under Settings | Languages & Frameworks for every project, with an "Editing" sub-page. The node's own page SHALL say what the RobotCode settings cover and that most project configuration lives in `robot.toml`. No RobotCode settings page SHALL show a work-in-progress notice or a field that has no effect. Every setting SHALL have a description in plain text, without markdown syntax.

#### Scenario: Opening the settings

- **WHEN** the user opens Settings | Languages & Frameworks | Robot Framework
- **THEN** the page explains what the RobotCode settings cover, the Editing sub-page is listed below the node, and neither page shows a work-in-progress notice or the former "Arguments" and "Mode" fields

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
- **THEN** both are equal, apart from `robotcode.documentationServer.startOnDemand`, which is `true`

#### Scenario: Default exclude patterns

- **WHEN** a project has no stored RobotCode settings
- **THEN** `robotcode.workspace.excludePatterns` holds VS Code's default patterns `.hatch/`, `.venv/`, `node_modules/`, `.pytest_cache/`, `__pycache__/`, `.mypy_cache/` and `.robotcode_cache/`, and the server does not load Robot Framework files below these folders

### Requirement: Value types in the settings tree

Values in the `robotcode` settings tree SHALL have the types the server parses: JSON booleans, integers, the exact enum strings, maps from strings to strings, and lists without `null` or empty entries.

#### Scenario: Value types

- **WHEN** the language server receives the `robotcode` settings tree
- **THEN** every boolean in it is a JSON boolean, every number is an integer, and no list holds `null` or an empty entry

### Requirement: Exceptions in the settings tree

The only exception to VS Code's defaults in the `robotcode` settings tree SHALL be `robotcode.documentationServer.startOnDemand`, which is always `true` because the plugin has no documentation viewer. Settings that only the clients use, for example for the debugger, runs, profiles or the language server process, SHALL NOT be part of the tree.

#### Scenario: Documentation server on demand

- **WHEN** the language server starts in IntelliJ
- **THEN** it does not start its documentation server until something needs a documentation URL

#### Scenario: Settings only the clients use

- **WHEN** the language server requests the `robotcode` section
- **THEN** the answer holds no settings for the debugger, runs, profiles or the language server process

### Requirement: Completion settings take effect

The Editing page SHALL offer "Filter default language" and "Header style", and the language server SHALL use their values after the user applies them. The header style SHALL be sent only when it is not blank. Otherwise the server uses its default: `*** {name} ***` from Robot Framework 6 on, and `*** {name}s ***` before.

#### Scenario: Custom header style

- **WHEN** the user sets "Header style" to `*** {name}`, applies, and completes a section header in a suite file
- **THEN** the inserted header follows that style, for example `*** Test Cases`

#### Scenario: Blank header style

- **WHEN** the user clears "Header style" and applies
- **THEN** section header completion uses the server's default header style

#### Scenario: Filtering the default language

- **WHEN** "Filter default language" is on and a suite file starts with `Language: German`
- **THEN** section header completion offers the German headers, such as `*** Testfälle ***`, and no English ones

### Requirement: Inlay hints are on by default

The inlay hints for parameter names and for namespaces SHALL be on by default, as in VS Code and on the language server. Each SHALL be possible to switch off on the Editing page. The Editing page SHALL point to Settings | Editor | Inlay Hints, where the display of the hints can be switched off as well.

#### Scenario: Project without RobotCode settings

- **WHEN** a project without stored RobotCode settings shows a keyword call with positional arguments, such as `Should Be Equal    ${a}    ${b}`
- **THEN** the editor shows the parameter names of the arguments as inlay hints

#### Scenario: Switching parameter names off

- **WHEN** the user switches off "Parameter names" on the Editing page and applies
- **THEN** the editor shows no parameter name hints, and namespace hints are still shown

### Requirement: Stored settings stay valid

The values that earlier versions of the plugin stored in the project's `.idea/robotcodeSettings.xml` SHALL keep their meaning, and the plugin SHALL send them to the language server.

#### Scenario: Settings stored by an earlier version

- **WHEN** a project's `robotcodeSettings.xml`, written by an earlier plugin version, holds a header style and "Filter default language" switched on
- **THEN** the Editing page shows both values, and the language server receives them
