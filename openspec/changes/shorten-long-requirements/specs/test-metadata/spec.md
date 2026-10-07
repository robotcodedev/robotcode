# Spec Delta

## MODIFIED Requirements

### Requirement: Test metadata in discover and results JSON

On Robot Framework ≥ 7.5, test and task items in the JSON output of `discover all`, `discover tests`, `discover tasks`, `results show`, `results summary --failed` and `results log` SHALL carry a `metadata` object mapping each metadata name, in the author's spelling, to its value verbatim (multi-line values joined with `\n`). The key SHALL be omitted when the test has no metadata and SHALL be absent on older Robot Framework versions. Suite items are unchanged.

#### Scenario: Discover on RF 7.5
- **WHEN** a suite contains a test with `[Metadata]    Issue    4409` and `[Metadata]    Owner Team    core` and `robotcode --format json discover tests` runs on RF 7.5
- **THEN** the item has `"metadata": {"Issue": "4409", "Owner Team": "core"}`
- **AND** a test without metadata in the same suite has no `metadata` key

#### Scenario: Results on RF 7.5
- **WHEN** the same suite was executed on RF 7.5 and `robotcode --format json results show` and `results log` are run on its `output.xml`
- **THEN** the corresponding test entries carry the same `metadata` object

#### Scenario: Metadata setting without a name
- **WHEN** a test has only `[Metadata]` with nothing after it and `robotcode --format json discover tests` runs on RF 7.5
- **THEN** the item has no `metadata` key
- **AND** `results show` and `results log` on an `output.json` of that suite, which contains `"metadata": {"": ""}`, report no metadata for the test either

#### Scenario: Older Robot Framework
- **WHEN** `robotcode --format json discover tests` runs on RF 7.4
- **THEN** no item has a `metadata` key

### Requirement: Search and text output include test metadata

`discover all/tests/tasks` and `results show` SHALL accept `--show-metadata/--no-show-metadata`, with the same defaults as the tags flag (on for `discover all`, off for the others), that prints `- _Metadata:_ name: value, …` under each test in text output; `results log` SHALL print the metadata of a test under its header whenever present. JSON output SHALL NOT depend on these flags.

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
- **AND** on RF 7.5 it does
- **AND** `robotcode discover tests --show-metadata` on RF 7.4 succeeds with the same output as without the flag

#### Scenario: Robot's metadata option
- **WHEN** `robotcode discover tests --metadata Version:1.2 suite.robot` runs
- **THEN** `Version:1.2` is given to Robot as suite metadata and not treated as a path
- **AND** the same tests are listed as without the option

## ADDED Requirements

### Requirement: Metadata settings without a name are left out

An entry without a name — a `[Metadata]` setting with nothing after it, which Robot Framework's model holds as an empty name with an empty value — is no metadata and SHALL be left out, in JSON and text output, for tests and for the suite metadata of `results log --suite-info`.

#### Scenario: Suite metadata without a name
- **WHEN** a suite has a `Metadata` setting with nothing after it and `robotcode results log --suite-info` runs on its `output.json`
- **THEN** the suite metadata shows no entry for it

### Requirement: Search matches test metadata

`--search` in `discover` and `results` SHALL match test metadata names and values literally, as it matches ancestor-suite metadata.

#### Scenario: Search in results by metadata value
- **WHEN** a test with `[Metadata]    Owner Team    core` was run on RF 7.5 and `robotcode results show --search core` runs on its `output.xml`
- **THEN** that test is listed

### Requirement: Robot's metadata option in discover

Robot's own `--metadata name:value` option SHALL still be passed through to Robot by the discover commands.

#### Scenario: Metadata option of discover all
- **WHEN** `robotcode discover all --metadata Version:1.2 suite.robot` runs
- **THEN** `Version:1.2` is given to Robot as suite metadata and not treated as a path

### Requirement: Show-metadata flags on older Robot Framework

With Robot Framework older than 7.5 installed, the `--show-metadata/--no-show-metadata` flags SHALL NOT be listed in the commands' `--help`; passing them SHALL still be accepted and have no effect.

#### Scenario: Flag passed to results show on RF 7.4
- **WHEN** `robotcode results show --no-show-metadata` runs on RF 7.4
- **THEN** it succeeds with the same output as without the flag
