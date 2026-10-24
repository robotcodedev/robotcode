## Purpose

Defines what the IntelliJ plugin provides when `robot.toml` and `.robot.toml` are edited in an IntelliJ-based IDE, so that writing the configuration is supported as in VS Code.

## ADDED Requirements

### Requirement: robot.toml is completed from RobotCode's JSON schema

The IntelliJ plugin SHALL associate RobotCode's JSON schema for `robot.toml`, `https://www.robotcode.io/schemas/robot.toml.json`, with files named `robot.toml` or `.robot.toml`, so that the IDE completes their settings without a schema mapping by the user. It SHALL NOT associate the schema with other TOML files. While the IDE's JSON support is disabled, the plugin SHALL work as without the association.

#### Scenario: Completion of a setting

- **WHEN** a project's `robot.toml` is open in PyCharm and `lang` is typed at the start of a line before the first table
- **THEN** the completion offers `languages` and `extend-languages`

#### Scenario: Schema of a .robot.toml

- **WHEN** a project has a `.robot.toml`
- **THEN** the IDE uses RobotCode's JSON schema for it, as for `robot.toml`

#### Scenario: Other TOML files

- **WHEN** a project has a `pyproject.toml`
- **THEN** the plugin does not associate RobotCode's JSON schema with it
