# Spec Delta

## MODIFIED Requirements

### Requirement: Discovery arguments from the Robot settings

After the discover subcommand, the full discovery and the discovery of a single suite file SHALL pass `--rpa` or `--norpa` for "Mode" unless it is "Default", `-P` for each entry of "Python path" and then for each root that the switches of the "Robot" page add, `--language` for each language, and the args. Variables, variable files and environment variables of the "Robot" page SHALL NOT be passed to discovery, as in VS Code.

#### Scenario: Settings for discovery

- **WHEN** "Mode" is "RPA", "Python path" is `libs`, both root switches are off, "Languages" is `de`, and "Args" is `--exclude wip`
- **THEN** the full discovery's command line contains `--rpa -P libs --language de --exclude wip` after the discover subcommand

#### Scenario: Roots for discovery

- **WHEN** "Python path" is `libs`, and the module whose interpreter RobotCode uses has the content root `/p` and the source root `/p/src`, with both switches on
- **THEN** the full discovery's command line contains `-P libs -P /p -P /p/src` after the discover subcommand
