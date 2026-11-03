# Spec Delta

## ADDED Requirements

### Requirement: An expression in robot.toml that can't be evaluated

When an expression in `robot.toml` can't be evaluated, a command that needs its value SHALL report it as `[ ERROR ] <message>`, naming the setting, without a traceback, and exit with the code it exits with for an invalid `robot.toml`. `robotcode profiles show`, which shows the configuration, SHALL report it the same way, show the setting with its expression and exit with 0.

#### Scenario: A command that runs Robot Framework
- **WHEN** `robot.toml` sets `output-dir = { expr = "nope(" }` and `robotcode robot` runs
- **THEN** robotcode reports the error for `output_dir` without a traceback
- **AND** the process exits with code 252

#### Scenario: Another command
- **WHEN** `robot.toml` sets that and `robotcode discover tests` runs
- **THEN** robotcode reports the error without a traceback
- **AND** the process exits with code 1

#### Scenario: Showing the configuration
- **WHEN** `robot.toml` sets that and `robotcode profiles show` runs
- **THEN** robotcode reports the error without a traceback and shows `output-dir` with its expression
- **AND** the process exits with code 0
