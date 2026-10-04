# Spec Delta

## Purpose

Defines how the IntelliJ plugin runs the RobotCode language server: when it starts, how it is connected, stopped and restarted, what it receives at start, where its output goes, and how users control and observe it.

## ADDED Requirements

### Requirement: The language server starts only in Robot Framework projects

When a project is opened, the plugin SHALL start the language server and the first full test discovery only if the project contains Robot Framework suite or resource files, or a `robot.toml` or `.robot.toml` file. In any other project, it SHALL start them when the first Robot Framework file is opened. It SHALL NOT start them for the default project or in LightEdit mode. In every case the start SHALL wait until the interpreter has been found usable.

#### Scenario: Python project without Robot Framework files

- **WHEN** a project without `.robot` or `.resource` files and without a robot.toml is opened, including PyCharm's Welcome project
- **THEN** no robotcode process starts

#### Scenario: First Robot Framework file in such a project

- **WHEN** the user then creates or opens a `.robot` file in that project
- **THEN** the language server starts, discovery runs, and the run markers of the file's tests appear

#### Scenario: Project with Robot Framework files

- **WHEN** a project that contains `tests/sample.robot` is opened
- **THEN** the language server and discovery start without a file being opened

### Requirement: Bundled files come from the plugin's installation

The plugin SHALL take its bundled robotcode from the directory in which the IDE installed or loaded the plugin, not from a fixed folder below the IDE's plugins directory.

#### Scenario: Plugin loaded from another directory

- **WHEN** the IDE loads the plugin from a directory outside its plugins directory, for example through the `plugin.path` system property
- **THEN** the language server starts with the bundled robotcode from that directory
