## ADDED Requirements

### Requirement: Environment names of a run on Windows

On Windows, with `robotcodeTerminal` and with `internalConsole`, a variable that a run's environment sets SHALL replace an inherited variable whose name differs only in case, with every supported Python version, so that the run and the programs it starts see the same, new value.

#### Scenario: Lower-case name in the run terminal

- **WHEN** Windows has `Path`, `robotcode.robot.env` sets `path`, and the user runs a test with `robotcodeTerminal`
- **THEN** the run and a program that the run starts see the value of `path`

#### Scenario: Other spelling with the internal console and Python 3.10

- **WHEN** the run's interpreter is Python 3.10, the launch configuration sets `Path` in `env`, and the run uses `internalConsole`
- **THEN** the run and a program that the run starts see the value from the launch configuration

#### Scenario: Other platforms

- **WHEN** a run's environment on Linux or macOS sets `path` while `PATH` exists
- **THEN** the run gets both variables, as before
