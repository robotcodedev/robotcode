# Spec: robot-toml-option-coverage

## Purpose

Guarantees that `robot.toml` accepts the console and libdoc option values that Robot Framework 7.5 accepts, and that the generated option model, the JSON schema and the configuration reference stay consistent with each other.

## Requirements

### Requirement: Custom console loggers are accepted

The `console` option SHALL accept the built-in console names `verbose`, `dotted`, `quiet` and `none` and any other string, which is passed to Robot Framework unchanged as a custom console class or module (`MyConsole`, `path/to/Console.py:arg`). The value `skipped`, which no Robot Framework version accepts, SHALL NOT be listed as a valid value. The JSON schema for `robot.toml` SHALL reflect this. The top-level `console` and `quiet` options SHALL apply to `robot` only and SHALL NOT be passed to `rebot`.

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

### Requirement: Libdoc accepts Markdown formats

`libdoc.doc-format` and `libdoc.format` SHALL accept `MARKDOWN` and pass it to `libdoc` unchanged; the JSON schema SHALL list `MARKDOWN` as a valid value.

#### Scenario: Markdown output format
- **WHEN** `robot.toml` contains `[libdoc]` with `format = "MARKDOWN"` and `robotcode libdoc MyLibrary out.md` is run on RF 7.5
- **THEN** `--format MARKDOWN` is passed to `libdoc`
- **AND** a Markdown file is written

### Requirement: Generated model, schema and reference stay consistent

The `robot.toml` option model, the JSON schema published for editors and the configuration reference in the documentation SHALL be regenerated from the same source with documented commands, so that field names (kebab-case aliases), examples and valid values agree.

#### Scenario: Regenerated schema keeps kebab-case names
- **WHEN** the model, schema and reference are regenerated
- **THEN** the schema still uses property names such as `console-colors` and `doc-format`
- **AND** the reference documents the same values as the schema
