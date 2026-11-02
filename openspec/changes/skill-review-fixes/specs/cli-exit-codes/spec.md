# Spec Delta

## ADDED Requirements

### Requirement: An expression in robot.toml that can't be evaluated

When an expression in `robot.toml` can't be evaluated, a command SHALL report it as `[ ERROR ] <message>`, naming the setting, without a traceback, and exit with the code it exits with for an invalid `robot.toml`.

#### Scenario: A command that runs Robot Framework
- **WHEN** `robot.toml` sets `output-dir = { expr = "nope(" }` and `robotcode robot` runs
- **THEN** robotcode reports the error for `output_dir` without a traceback
- **AND** the process exits with code 252

#### Scenario: Another command
- **WHEN** `robot.toml` sets that and `robotcode discover tests` runs
- **THEN** robotcode reports the error without a traceback
- **AND** the process exits with code 1
