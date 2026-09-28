# Spec Delta

## MODIFIED Requirements

### Requirement: Search and text output include test metadata

`--search` in `discover` and `results` SHALL match test metadata names and values literally, as it matches ancestor-suite metadata. `discover all/tests/tasks` and `results show` SHALL accept `--show-metadata/--no-show-metadata`, with the same defaults as the tags flag (on for `discover all`, off for the others), that prints `- _Metadata:_ name: value, …` under each test in text output; `results log` SHALL print the metadata of a test under its header whenever present. JSON output SHALL NOT depend on these flags. Robot's own `--metadata name:value` option SHALL still be passed through to Robot by the discover commands. With Robot Framework older than 7.5 installed, the `--show-metadata/--no-show-metadata` flags SHALL NOT be listed in the commands' `--help`; passing them SHALL still be accepted and have no effect. On Robot Framework 7.5 and newer, the help of the flags SHALL say that they need Robot Framework 7.5 or newer, so that the CLI reference generated from it carries the note as well.

#### Scenario: Search by metadata value
- **WHEN** `robotcode discover tests --search 4409` runs on RF 7.5 against the suite above
- **THEN** only the test whose metadata contains `4409` is listed

#### Scenario: Text output with metadata
- **WHEN** `robotcode discover tests --show-metadata` runs on RF 7.5
- **THEN** the test is followed by `- _Metadata:_ Issue: 4409, Owner Team: core`
- **AND** without `--show-metadata` no such line is printed

#### Scenario: Default of discover all
- **WHEN** `robotcode discover all` runs on RF 7.5 without a metadata flag
- **THEN** the metadata line is printed under the test, as the tags line is
- **AND** `--no-show-metadata` hides it

#### Scenario: Help on older Robot Framework
- **WHEN** `robotcode discover tests --help` or `robotcode results show --help` runs on RF 7.4
- **THEN** the output does not list `--show-metadata`
- **AND** on RF 7.5 it does, with a help text that says it needs Robot Framework 7.5 or newer
- **AND** `robotcode discover tests --show-metadata` on RF 7.4 succeeds with the same output as without the flag

#### Scenario: Robot's metadata option
- **WHEN** `robotcode discover tests --metadata Version:1.2 suite.robot` runs
- **THEN** `Version:1.2` is given to Robot as suite metadata and not treated as a path
- **AND** the same tests are listed as without the option
