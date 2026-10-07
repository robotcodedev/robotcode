# Spec Delta

## Purpose

Defines which discovered Robot Framework tests, tasks and suites the IntelliJ plugin marks in the editor gutter, and how it keeps that model current when a single suite file is opened, closed or edited.

## ADDED Requirements

### Requirement: Discovery uses the project's run options

The full discovery and the discovery of a single suite file SHALL pass `-dp` for each default path of the project's run options, or `-dp .` when there is none, before the `discover` command. The profile list SHALL pass the same `-dp` arguments.

#### Scenario: Default paths

- **WHEN** `robot.toml` sets no paths, the project has the folders `tests` and `examples` with suites, and the default paths of the run options are `tests`
- **THEN** discovery and the profile list pass `-dp tests`, and run markers appear in the suites below `tests` and not in those below `examples`

#### Scenario: No default paths

- **WHEN** the run options set no default paths
- **THEN** discovery passes `-dp .`, as before

### Requirement: Discovery arguments from the run options

After the discover subcommand, the full discovery and the discovery of a single suite file SHALL pass `--rpa` or `--norpa` for the mode unless it is "Default", `-P` for each Python path entry, `--language` for each language, and the robot arguments. Variables, variable files and environment variables of the settings SHALL NOT be passed to discovery, as in VS Code.

#### Scenario: Settings for discovery

- **WHEN** the mode is "RPA", the Python path is `libs`, the languages are `de`, and the robot arguments are `--exclude wip`
- **THEN** the full discovery's command line contains `--rpa -P libs --language de --exclude wip` after the discover subcommand
