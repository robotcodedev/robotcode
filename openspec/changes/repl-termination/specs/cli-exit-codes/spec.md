# Spec Delta

## MODIFIED Requirements

### Requirement: Own errors exit with 252

Commands that run Robot Framework (`robot`, `debug`, `repl`, `robot-debug`, `repl-server`) and commands that pass on the exit code of a Robot Framework tool (`rebot`, `libdoc`, `testdoc`) SHALL exit with code 252 when robotcode itself reports an error for them, such as a wrapper that cannot be started, an invalid configuration or an invalid command line option. This SHALL also apply when the status-based exit code is turned off.

#### Scenario: Wrapper that cannot be started
- **WHEN** `robotcode --wrapper ./does-not-exist.sh robot t.robot` runs
- **THEN** robotcode reports that the wrapper command could not be executed
- **AND** the process exits with code 252

#### Scenario: Invalid robot.toml
- **WHEN** `robot.toml` is not valid TOML and `robotcode robot t.robot` runs
- **THEN** robotcode reports the invalid file
- **AND** the process exits with code 252

#### Scenario: Invalid robot.toml for rebot
- **WHEN** `robot.toml` is not valid TOML and `robotcode rebot output.xml` runs
- **THEN** the process exits with code 252

#### Scenario: Invalid robot.toml for debug
- **WHEN** `robot.toml` is not valid TOML and `robotcode debug` loads it
- **THEN** the process exits with code 252, not 255

#### Scenario: Invalid option
- **WHEN** `robotcode repl --no-such-option` runs
- **THEN** robotcode reports the unknown option
- **AND** the process exits with code 252

#### Scenario: Status-based exit code turned off
- **WHEN** `robotcode --wrapper ./does-not-exist.sh robot --nostatusrc t.robot` runs
- **THEN** the process exits with code 252

#### Scenario: Invalid robot.toml for repl-server
- **WHEN** `robot.toml` is not valid TOML and `robotcode repl-server` runs
- **THEN** robotcode reports the invalid file instead of a traceback
- **AND** the process exits with code 252 instead of running on
