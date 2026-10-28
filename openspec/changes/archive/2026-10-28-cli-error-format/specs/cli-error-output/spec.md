## Purpose

Defines how robotcode writes an error that stops a command, so that it looks like the errors robotcode reports and goes on after.

## ADDED Requirements

### Requirement: An error that stops a command looks like a reported error

When a robotcode command stops with an error of its own, such as an error of the configuration or an invalid option, robotcode SHALL write it to standard error as `[ ERROR ] <message>`, in the form and with the colours of the errors it reports without stopping, and SHALL exit with the code it exits with for that error. For an invalid option or argument of robotcode, the usage line and the hint to `--help` SHALL stay above it.

#### Scenario: Selected profile that does not exist

- **WHEN** `robotcode -p typo run tests` runs with its error output in a pipe, in a project whose `robot.toml` defines no profile `typo`
- **THEN** the error output shows `[ ERROR ] No profile matches 'typo'.` once, without colour codes, and robotcode exits with 252

#### Scenario: The same error, reported and stopping

- **WHEN** a project's `robot.toml` sets `default-profiles = ["typo"]` without a profile `typo`, and `robotcode run tests` and `robotcode -p typo run tests` run
- **THEN** both write the line `[ ERROR ] No profile matches 'typo'.`; the first runs the tests, the second stops

#### Scenario: Colours on

- **WHEN** `robotcode --color -p typo run tests` runs in such a project
- **THEN** `ERROR` is written in the colour of errors, as in the errors robotcode reports

#### Scenario: Colours off

- **WHEN** `robotcode --no-color -p typo run tests` runs in such a project, or with `NO_COLOR` set
- **THEN** the line has no colour codes

#### Scenario: Invalid option of robotcode

- **WHEN** `robotcode --nonsense profiles list` runs
- **THEN** robotcode writes its usage line, the hint to `robotcode --help`, and `[ ERROR ] No such option '--nonsense'.`, and exits with 2

#### Scenario: Unexpected error

- **WHEN** a command ends with an exception that robotcode does not report itself
- **THEN** Python's traceback is written as before
