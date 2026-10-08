# Spec Delta

## Purpose

Defines the Robot Framework settings pages of the IntelliJ plugin and the settings the RobotCode language server receives from the plugin, so that the server behaves as with VS Code's defaults unless the user changes a setting.

## ADDED Requirements

### Requirement: Settings for new projects

The Robot Framework settings pages that hold shared settings SHALL be available under File | New Projects Setup | Settings for New Projects, and the values set there SHALL be used for projects created afterwards. Pages with settings stored for the current user only, such as the extra arguments and the profile selection, SHALL NOT be offered there. Applying settings there SHALL NOT start, stop or restart a language server, and SHALL NOT run test discovery.

#### Scenario: Preset for a new project

- **WHEN** the user sets "Header style" to `*** {name}` on the Editing page under Settings for New Projects, applies, and then creates a new project
- **THEN** the Editing page of the new project shows `*** {name}`

#### Scenario: Personal settings are not offered

- **WHEN** the user opens the "Robot Framework" node under Settings for New Projects
- **THEN** it lists the Editing, Analysis and Robocop pages, and not the General and Language Server pages

#### Scenario: Apply starts nothing

- **WHEN** the user changes a value under Settings for New Projects and applies
- **THEN** no `robotcode` process starts

## MODIFIED Requirements

### Requirement: Robocop page

The Robot Framework settings node SHALL have a "Robocop" sub-page with these settings, and the language server SHALL use their values after the user applies them:

- Robocop analysis enabled, on by default;
- config file, none by default;
- ignore Git dir, off by default;
- ignore file config, off by default.

The config file SHALL be stored and sent as entered, without a check by the plugin, as in VS Code; the language server and Robocop resolve it and report a file they cannot read.

#### Scenario: Switching Robocop off

- **WHEN** Robocop is installed in the project's interpreter and the user switches Robocop analysis off and applies
- **THEN** Robocop's diagnostics disappear, and the other RobotCode diagnostics stay

#### Scenario: Config file

- **WHEN** the user enters `robocop.toml`, a Robocop configuration file in the project folder that ignores a Robocop rule, and applies
- **THEN** the page keeps `robocop.toml`, and diagnostics of that rule disappear

#### Scenario: Missing config file

- **WHEN** the user enters the path of a file that does not exist as config file and applies
- **THEN** the value is stored as entered, and the language server reports that the Robocop configuration could not be loaded
