# Spec Delta

## Purpose

Defines the Robot Framework settings pages of the IntelliJ plugin and the settings the RobotCode language server receives from the plugin, so that the server behaves as with VS Code's defaults unless the user changes a setting.

## ADDED Requirements

### Requirement: Settings for new projects

The Robot Framework settings pages that hold shared settings SHALL be available under File | New Projects Setup | Settings for New Projects, and the values set there SHALL be used for projects created afterwards. Settings stored for the current user only, such as the profile selection, SHALL NOT be offered there. Applying settings there SHALL NOT start, stop or restart a language server, and SHALL NOT run test discovery.

#### Scenario: Preset for a new project

- **WHEN** the user sets "Header style" to `*** {name}` on the Editing page under Settings for New Projects, applies, and then creates a new project
- **THEN** the Editing page of the new project shows `*** {name}`

#### Scenario: Personal settings are not offered

- **WHEN** the user opens the "Robot Framework" page under Settings for New Projects
- **THEN** the page does not show the configuration profiles

#### Scenario: Apply starts nothing

- **WHEN** the user changes a value under Settings for New Projects and applies
- **THEN** no `robotcode` process starts
