# Spec Delta

## ADDED Requirements

### Requirement: Discovery uses the paths of the Robot settings

The full discovery and the discovery of a single suite file SHALL pass `-dp` for each entry of "Paths" on the "Robot" settings page, or `-dp .` when there is none, before the `discover` command. The profile list SHALL pass the same `-dp` arguments.

#### Scenario: Paths

- **WHEN** `robot.toml` sets no paths, the project has the folders `tests` and `examples` with suites, and "Paths" is `tests`
- **THEN** discovery and the profile list pass `-dp tests`, and run markers appear in the suites below `tests` and not in those below `examples`

#### Scenario: No paths

- **WHEN** "Paths" is empty
- **THEN** discovery passes `-dp .`, as before

### Requirement: Discovery arguments from the Robot settings

After the discover subcommand, the full discovery and the discovery of a single suite file SHALL pass `--rpa` or `--norpa` for "Mode" unless it is "Default", `-P` for each entry of "Python path", `--language` for each language, and the args. Variables, variable files and environment variables of the "Robot" page SHALL NOT be passed to discovery, as in VS Code.

#### Scenario: Settings for discovery

- **WHEN** "Mode" is "RPA", "Python path" is `libs`, "Languages" is `de`, and "Args" is `--exclude wip`
- **THEN** the full discovery's command line contains `--rpa -P libs --language de --exclude wip` after the discover subcommand
