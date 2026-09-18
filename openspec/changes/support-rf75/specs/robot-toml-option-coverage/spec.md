# Spec Delta

## Purpose

Guarantees that `robot.toml` accepts the console and libdoc option values that Robot Framework 7.5 accepts, and that the generated option model, the JSON schema and the configuration reference stay consistent with each other.

## ADDED Requirements

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
