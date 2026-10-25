# language-server-configuration Specification

## Purpose

Defines how the language server deals with errors in the configuration that it loads from `robot.toml` and the selected profiles at its start.

## Requirements

### Requirement: The language server starts despite errors of its configuration

When the configuration that the language server loads at its start has errors, the language server SHALL start anyway and SHALL write each error to its log. With a name that selects no profile, it SHALL work with the configuration without that name; with a `robot.toml` that it cannot load, with its defaults.

#### Scenario: Selected profile that does not exist

- **WHEN** the editor starts the language server with the profile `missing` selected, and `robot.toml` sets `python-path = ["libraries"]`
- **THEN** the language server writes the error for `missing` to its log
- **AND** it finds the libraries in `libraries` for the imports of the project's files

#### Scenario: robot.toml with an invalid value

- **WHEN** `robot.toml` sets `output-dir = 5` and the language server starts
- **THEN** the language server writes the error to its log and analyzes the Robot Framework files of the project

#### Scenario: Profiles that inherit each other

- **WHEN** the profile `a` inherits `b`, `b` inherits `a`, and the editor starts the language server with `a` selected
- **THEN** the language server writes the error to its log and analyzes the Robot Framework files of the project

### Requirement: The language server shows errors of its configuration in the editor

Once the editor has initialized the connection, the language server SHALL show each error of the configuration that it loaded at its start as an error message in the editor, except a name that the editor passes with `-p` and that selects no profile, which the editors report themselves. A name from `ROBOTCODE_PROFILES` that selects no profile SHALL be shown, since no editor reports it.

#### Scenario: Default profile that does not exist

- **WHEN** `robot.toml` sets `default-profiles = ["typo"]`, has no profile `typo`, and the language server starts without a selection
- **THEN** the editor shows the error for `typo` from `default-profiles` as an error message

#### Scenario: Invalid value in robot.toml

- **WHEN** `robot.toml` sets `output-dir = 5` and the language server starts
- **THEN** the editor shows an error message that names `robot.toml` and `output_dir`

#### Scenario: Selected profile without a message

- **WHEN** the editor starts the language server with the profile `missing` selected, which `robot.toml` does not define
- **THEN** the language server shows no message for `missing`

#### Scenario: Profile from ROBOTCODE_PROFILES

- **WHEN** the language server starts with `ROBOTCODE_PROFILES=missing` in its environment, without `-p`, and `robot.toml` defines no profile `missing`
- **THEN** the editor shows the error for `missing` as an error message

#### Scenario: Configuration without errors

- **WHEN** `robot.toml` has no errors, the selected profiles exist, and the language server starts
- **THEN** the editor shows no message about the configuration
