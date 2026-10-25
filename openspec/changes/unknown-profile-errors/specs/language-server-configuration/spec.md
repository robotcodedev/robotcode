## Purpose

Defines how the language server deals with errors in the configuration that it loads from `robot.toml` and the selected profiles at its start.

## ADDED Requirements

### Requirement: The language server shows errors of its configuration and starts anyway

When the configuration that the language server loads at its start has errors, the language server SHALL start anyway and SHALL show each error as an error message in the editor once the editor has initialized the connection. It SHALL also write each error to its log. With a profile name that selects no profile, it SHALL work with the configuration without that profile; with a `robot.toml` that it cannot load, with its defaults.

#### Scenario: Selected profile that does not exist

- **WHEN** the editor starts the language server with the profile `missing` selected, and `robot.toml` sets `python-path = ["libraries"]`
- **THEN** the editor shows "Can't find any configuration profiles matching the pattern 'missing'." as an error message
- **AND** the language server finds the libraries in `libraries` for the imports of the project's files

#### Scenario: robot.toml with an invalid value

- **WHEN** `robot.toml` sets `output-dir = 5` and the language server starts
- **THEN** the editor shows an error message that names `robot.toml` and `output_dir`
- **AND** the language server analyzes the Robot Framework files of the project

#### Scenario: Configuration without errors

- **WHEN** `robot.toml` has no errors, the selected profiles exist, and the language server starts
- **THEN** the editor shows no message about the configuration
