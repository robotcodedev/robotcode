# cli-exit-codes Specification

## Purpose

Defines the exit codes of robotcode commands that run Robot Framework or pass on a Robot Framework tool's exit code, so that robotcode's own errors can be told apart from failed tests.

## Requirements

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

Commands that neither run Robot Framework nor pass on a Robot Framework tool's exit code SHALL keep the exit codes they use for robotcode's own errors. The `results` commands are not among them, see "Errors of the results commands exit with 128".

#### Scenario: Invalid robot.toml for analyze
- **WHEN** `robot.toml` is not valid TOML and `robotcode analyze code` runs
- **THEN** the process exits with code 1

#### Scenario: Invalid robot.toml for discover
- **WHEN** `robot.toml` is not valid TOML and `robotcode discover tests` runs
- **THEN** the process exits with code 1

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

### Requirement: Errors of the results commands exit with 128

`robotcode results` and its commands (`diff`, `log`, `show`, `stats`, `summary`) SHALL exit with 128 for every error that stops them: a usage error, a result file that is missing or can't be read, an error of the configuration such as an invalid `robot.toml`, and an unexpected error. They SHALL report the error as before. An error of robotcode's own options before `results` SHALL keep its exit code.

#### Scenario: Missing result file
- **WHEN** `robotcode results summary -o missing.xml` runs and `missing.xml` doesn't exist
- **THEN** robotcode reports that the result file was not found
- **AND** the process exits with code 128

#### Scenario: Invalid option value
- **WHEN** `robotcode results diff base.xml new.xml --only nope` runs
- **THEN** robotcode reports the invalid value
- **AND** the process exits with code 128

#### Scenario: Result file that can't be read
- **WHEN** `new.xml` is not a result file and `robotcode results diff base.xml new.xml` runs
- **THEN** robotcode reports that it failed to parse `new.xml`
- **AND** the process exits with code 128

#### Scenario: Invalid robot.toml for results
- **WHEN** `robot.toml` is not valid TOML and `robotcode results summary` runs
- **THEN** robotcode reports the invalid file
- **AND** the process exits with code 128

#### Scenario: Unknown command of results
- **WHEN** `robotcode results nope` runs
- **THEN** robotcode reports the unknown command
- **AND** the process exits with code 128

#### Scenario: Error with the exit code of a diff
- **WHEN** `robotcode results diff base.xml missing.xml --exit-code` runs and `missing.xml` doesn't exist
- **THEN** the process exits with code 128

#### Scenario: Unexpected error
- **WHEN** a `results` command ends with an exception that robotcode does not report itself
- **THEN** Python's traceback is written as before
- **AND** the process exits with code 128

#### Scenario: Invalid option of robotcode before results
- **WHEN** `robotcode --nonsense results summary` runs
- **THEN** robotcode reports the unknown option
- **AND** the process exits with code 2
