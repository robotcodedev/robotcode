# Spec Delta

## Purpose

Defines the exit codes of robotcode commands that run Robot Framework or pass on a Robot Framework tool's exit code, so that robotcode's own errors can be told apart from failed tests.

## ADDED Requirements

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

### Requirement: Robot Framework's exit codes pass through

The commands covered by the requirement "Own errors exit with 252" SHALL pass on the exit code that Robot Framework or the Robot Framework tool returns unchanged, including the number of failed tests and Robot Framework's own 252 for options it rejects.

#### Scenario: Failed test
- **WHEN** `robotcode robot` runs a suite with one failing test
- **THEN** the process exits with code 1

#### Scenario: Option rejected by Robot Framework
- **WHEN** `robotcode robot --nosuchoption t.robot` runs
- **THEN** Robot Framework reports the option
- **AND** the process exits with code 252

### Requirement: Other commands keep their exit codes

Commands that neither run Robot Framework nor pass on a Robot Framework tool's exit code SHALL keep the exit codes they use for robotcode's own errors.

#### Scenario: Invalid robot.toml for analyze
- **WHEN** `robot.toml` is not valid TOML and `robotcode analyze code` runs
- **THEN** the process exits with code 1

#### Scenario: Invalid robot.toml for discover
- **WHEN** `robot.toml` is not valid TOML and `robotcode discover tests` runs
- **THEN** the process exits with code 1
