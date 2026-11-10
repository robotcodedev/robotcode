# Spec Delta

## Purpose

Defines which document formats besides plain Robot Framework files RobotCode serves in a project, when such a format is active, and how editors learn the active formats through `robotcode discover info`.

## ADDED Requirements

### Requirement: Markdown is active only when configured

The Markdown format SHALL be active only on Robot Framework 7.5.1 or newer, and only for those of the extensions `md`, `markdown` and `robot.md` that the `extensions` option of the selected robot.toml profiles lists, compared without letter case and without a leading dot. Robot Framework's default extensions SHALL NOT make it active.

#### Scenario: robot.md configured
- **WHEN** the robot.toml contains `extensions = "robot:robot.md"` and Robot Framework 7.5.1 is installed
- **THEN** the Markdown format is active for the extension `robot.md` and for no other extension

#### Scenario: Nothing configured
- **WHEN** the robot.toml sets no `extensions`, on Robot Framework 7.5.1
- **THEN** no Markdown format is active, although Robot Framework itself parses `*.robot.md` files by default

#### Scenario: Robot Framework 7.5.0
- **WHEN** the robot.toml contains `extensions = "robot:md"` and Robot Framework 7.5.0 is installed
- **THEN** no Markdown format is active

### Requirement: discover info lists the active formats

`robotcode discover info` SHALL read the configuration with the selected profiles and list every active document format with its name and extensions, in the text output and as `documentFormats` in the JSON output. It SHALL NOT list inactive formats. When the configuration cannot be read, it SHALL fail like the other `discover` commands.

#### Scenario: JSON output
- **WHEN** `robotcode --format json discover info` runs in a project whose robot.toml contains `extensions = "robot:md"`, on Robot Framework 7.5.1
- **THEN** `documentFormats` holds exactly one entry, with the name `markdown` and the extensions `["md"]`

#### Scenario: No active format
- **WHEN** the same command runs in a project whose robot.toml sets no `extensions`
- **THEN** no document format is listed

#### Scenario: Profile selects the format
- **WHEN** only the profile `docs` of the robot.toml sets `extensions = "robot:robot.md"` and `robotcode -p docs --format json discover info` runs, on Robot Framework 7.5.1
- **THEN** `documentFormats` lists `markdown` with the extensions `["robot.md"]`

### Requirement: VS Code serves the files of the active formats

For each workspace folder whose language server it starts, the VS Code extension SHALL ask `discover info` with the folder's profiles and send the files of the active formats' extensions in that folder to the language server, while they keep their own language in the editor. When `discover info` fails or lists no format, the folder SHALL be served as before.

#### Scenario: Markdown suite in VS Code
- **WHEN** a folder's robot.toml contains `extensions = "robot:robot.md"`, Robot Framework 7.5.1 is selected and `tests/shop.robot.md` is opened
- **THEN** the editor shows the file as Markdown, and hovering a keyword call inside a `robotframework` code block shows the keyword's documentation

#### Scenario: Format switched off
- **WHEN** `extensions` is removed from that folder's robot.toml
- **THEN** after the language server has restarted, RobotCode shows no hover in `tests/shop.robot.md`
