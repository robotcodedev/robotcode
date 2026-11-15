# Spec Delta

## Purpose

Defines which Markdown files RobotCode serves in a project, how `robotcode discover info` reports the document formats Robot Framework parses with the project's settings, and how VS Code hands the Markdown files to the language server.

## ADDED Requirements

### Requirement: Markdown files are served as Robot Framework parses them

On Robot Framework 7.5.1 or newer, RobotCode SHALL serve a file with the extension `md`, `markdown` or `robot.md` when that extension is in Robot Framework's extension list of the selected robot.toml profiles: `extensions`, or Robot Framework's default extensions when `extensions` is not set, plus the extension of each `parse-include` pattern. Extensions SHALL be compared like Robot Framework compares them. Below 7.5.1, RobotCode SHALL serve no Markdown file.

#### Scenario: Nothing configured
- **WHEN** the robot.toml sets neither `extensions` nor `parse-include`, on Robot Framework 7.5.1
- **THEN** RobotCode serves `tests/shop.robot.md` and does not serve `README.md`

#### Scenario: extensions replaces the defaults
- **WHEN** the robot.toml contains `extensions = "robot"`, on Robot Framework 7.5.1
- **THEN** RobotCode does not serve `tests/shop.robot.md`

#### Scenario: md in extensions
- **WHEN** the robot.toml contains `extensions = "robot:md"`, on Robot Framework 7.5.1
- **THEN** RobotCode serves `README.md` and `tests/shop.robot.md`

#### Scenario: Letter case, dot and trailing suffixes
- **WHEN** the robot.toml contains `extensions = "robot:.MD"`, on Robot Framework 7.5.1
- **THEN** RobotCode serves `tests/shop.robot.md`, whose trailing suffix `.md` matches

#### Scenario: Robot Framework 7.5.0
- **WHEN** the robot.toml contains `extensions = "robot:md"` and Robot Framework 7.5.0 is installed
- **THEN** RobotCode serves no Markdown file

### Requirement: parse-include patterns limit the served Markdown files

When `parse-include` sets patterns, RobotCode SHALL serve a Markdown file only when it also matches one of them as Robot Framework matches them, with relative patterns taken from the project root, unless it is the `__init__` file of its extension.

#### Scenario: parse-include pattern
- **WHEN** the robot.toml contains `parse-include = ["docs/*.md"]`, on Robot Framework 7.5.1
- **THEN** RobotCode serves `docs/guide.md` and serves neither `README.md` nor `tests/shop.robot.md`, which Robot Framework does not parse either

### Requirement: discover info lists the document formats Robot Framework parses

`robotcode discover info` SHALL read the configuration with the selected profiles and list every document format Robot Framework parses with them, in the text output and as `documentFormats` in the JSON output: one entry per format, with its name and the extensions of Robot Framework's extension list that Robot Framework parses with that format. It SHALL NOT list the `parse-include` patterns. When the configuration cannot be read, it SHALL fail like the other `discover` commands.

#### Scenario: Default extensions
- **WHEN** `robotcode --format json discover info` runs in a project whose robot.toml sets no `extensions`, on Robot Framework 7.5.1
- **THEN** `documentFormats` lists `robot` with `["robot"]`, `json` with `["rbt"]`, `rest` with `["robot.rst"]` and `markdown` with `["robot.md"]`

#### Scenario: md in extensions
- **WHEN** the same command runs in a project whose robot.toml contains `extensions = "robot:md"`, on Robot Framework 7.5.1
- **THEN** `documentFormats` lists exactly `robot` with `["robot"]` and `markdown` with `["md"]`

#### Scenario: Other extensions are Robot Framework's own format
- **WHEN** the robot.toml contains `extensions = "robot:txt"`
- **THEN** `documentFormats` lists exactly `robot` with `["robot", "txt"]`

#### Scenario: Robot Framework 7.4
- **WHEN** the robot.toml sets no `extensions`, on Robot Framework 7.4
- **THEN** `documentFormats` lists `robot`, `json` and `rest`, and no `markdown`

#### Scenario: Profile selects the extensions
- **WHEN** only the profile `docs` of the robot.toml sets `extensions = "robot:md"` and `robotcode -p docs --format json discover info` runs, on Robot Framework 7.5.1
- **THEN** `documentFormats` lists `markdown` with `["md"]`, and without `-p docs` with `["robot.md"]`

### Requirement: VS Code sends the Markdown files to the language server

For each workspace folder whose language server it starts, the VS Code extension SHALL ask `discover info` with the folder's profiles and send the files of the Markdown format's extensions in that folder to the language server, while they keep their own language in the editor; the other formats of the list SHALL add nothing. When `discover info` fails or lists no Markdown format, the folder SHALL be served as before.

#### Scenario: Markdown suite in VS Code
- **WHEN** a folder's robot.toml sets no `extensions`, Robot Framework 7.5.1 is selected and `tests/shop.robot.md` is opened
- **THEN** the editor shows the file as Markdown, and hovering a keyword call inside a `robotframework` code block shows the keyword's documentation

#### Scenario: Format switched off
- **WHEN** `extensions = "robot"` is added to that folder's robot.toml
- **THEN** after the language server has restarted, RobotCode shows no hover in `tests/shop.robot.md`

### Requirement: Breakpoints in Markdown files in VS Code

The VS Code extension SHALL let breakpoints be set in the Markdown file of the active editor when the language server of its folder serves files of its extension, and in no other Markdown file. Debugging SHALL stop at a breakpoint on an executed line of a Markdown suite, whichever file is active.

#### Scenario: Breakpoint in a Markdown suite
- **WHEN** a folder's robot.toml sets no `extensions`, Robot Framework 7.5.1 is selected, a breakpoint is toggled on the line `    Log    hello` inside a code block of `tests/shop.robot.md` and the file is debugged while `README.md` is the active editor
- **THEN** the breakpoint is set and the debugger stops at that line of `tests/shop.robot.md`

#### Scenario: Markdown file that is no suite
- **WHEN** the same folder's `README.md` is the active editor
- **THEN** toggling a breakpoint in `README.md` sets none

#### Scenario: No folder serves Markdown
- **WHEN** the robot.toml of every folder contains `extensions = "robot"`
- **THEN** toggling a breakpoint in `tests/shop.robot.md` sets none
