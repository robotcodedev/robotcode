# Spec Delta

## MODIFIED Requirements

### Requirement: Other commands keep their exit codes

Commands that neither run Robot Framework nor pass on a Robot Framework tool's exit code SHALL keep the exit codes they use for robotcode's own errors. The `results` commands are not among them, see "Errors of the results commands exit with 128".

#### Scenario: Invalid robot.toml for analyze
- **WHEN** `robot.toml` is not valid TOML and `robotcode analyze code` runs
- **THEN** the process exits with code 1

#### Scenario: Invalid robot.toml for discover
- **WHEN** `robot.toml` is not valid TOML and `robotcode discover tests` runs
- **THEN** the process exits with code 1

## ADDED Requirements

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
