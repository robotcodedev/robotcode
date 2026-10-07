# Spec Delta

## MODIFIED Requirements

### Requirement: Custom console loggers are accepted

The `console` option SHALL accept the built-in console names `verbose`, `dotted`, `quiet` and `none` and any other string, which is passed to Robot Framework unchanged as a custom console class or module (`MyConsole`, `path/to/Console.py:arg`). The value `skipped`, which no Robot Framework version accepts, SHALL NOT be listed as a valid value. The JSON schema for `robot.toml` SHALL reflect this.

#### Scenario: Custom console class in robot.toml
- **WHEN** `robot.toml` contains `console = "MyConsole.py:arg"` and `robotcode robot` is run on RF 7.5
- **THEN** configuration validation succeeds
- **AND** `--console MyConsole.py:arg` is passed to Robot Framework

#### Scenario: Built-in console name
- **WHEN** `robot.toml` contains `console = "dotted"`
- **THEN** `--console dotted` is passed to Robot Framework as before

#### Scenario: Top-level console does not reach rebot
- **WHEN** `robot.toml` contains `console = "dotted"` and `robotcode rebot output.xml` is run on RF 7.4
- **THEN** no `--console` option is passed to `rebot` and `rebot` completes without an option error

## ADDED Requirements

### Requirement: Console options apply to robot only

The top-level `console` and `quiet` options SHALL apply to `robot` only and SHALL NOT be passed to `rebot`.

#### Scenario: Top-level quiet and rebot
- **WHEN** `robot.toml` contains `quiet = true` and `robotcode rebot output.xml` is run
- **THEN** no `--quiet` option is passed to `rebot`
