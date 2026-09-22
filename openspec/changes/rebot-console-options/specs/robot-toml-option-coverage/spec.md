# Spec Delta

## Purpose

Guarantees that `robot.toml` accepts the console and libdoc option values that Robot Framework 7.5 accepts, and that the generated option model, the JSON schema and the configuration reference stay consistent with each other.

## ADDED Requirements

### Requirement: Rebot console options

The `[rebot]` section SHALL accept `console` — the built-in console names `verbose`, `quiet` and `none`, or any other string passed to `rebot` unchanged as a custom console class or module — and `quiet`. `robotcode rebot` SHALL pass them to `rebot` on every Robot Framework version; on versions older than 7.5 `rebot` itself rejects them, and RobotCode SHALL NOT add a check of its own. The top-level `console` and `quiet` SHALL NOT be copied into the `rebot` options; only the values of the `[rebot]` section apply to `rebot`. The JSON schema and the configuration reference SHALL list `rebot.console` and `rebot.quiet`.

#### Scenario: Rebot console on RF 7.5
- **WHEN** `robot.toml` contains `[rebot]` with `console = "quiet"` and `robotcode rebot output.xml` is run on RF 7.5
- **THEN** `--console quiet` is passed to `rebot`

#### Scenario: Custom rebot console on RF 7.5
- **WHEN** `robot.toml` contains `[rebot]` with `console = "path/to/Console.py:arg"` on RF 7.5
- **THEN** configuration validation succeeds
- **AND** `--console path/to/Console.py:arg` is passed to `rebot`

#### Scenario: Rebot quiet flag
- **WHEN** `robot.toml` contains `[rebot]` with `quiet = true` on RF 7.5
- **THEN** `--quiet` is passed to `rebot`

#### Scenario: Rebot console on RF 7.4
- **WHEN** the same configurations are used with `robotcode rebot` on RF 7.4
- **THEN** the options are passed to `rebot`
- **AND** `rebot` fails with its own error naming the option (`option --console not a unique prefix`)

#### Scenario: Top-level console does not apply to rebot
- **WHEN** `robot.toml` contains a top-level `console = "dotted"` and `quiet = true` but no `[rebot] console`/`quiet`, and `robotcode rebot output.xml` is run on RF 7.5
- **THEN** neither `--console` nor `--quiet` is passed to `rebot`

#### Scenario: Schema and reference
- **WHEN** the JSON schema and `docs/03_reference/config.md` are regenerated
- **THEN** both document `rebot.console` (string, with the built-in names listed) and `rebot.quiet`
