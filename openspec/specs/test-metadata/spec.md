# Spec: test-metadata

## Purpose

Defines how test- and task-level metadata (Robot Framework ≥ 7.5) is represented and shown across RobotCode — in discover and results output, search, the discover models of the editor clients and the test hover — and how result files containing it are handled on older Robot Framework versions.

## Requirements

### Requirement: Test metadata in discover and results JSON

On Robot Framework ≥ 7.5, test and task items in the JSON output of `discover all`, `discover tests`, `discover tasks`, `results show`, `results summary --failed` and `results log` SHALL carry a `metadata` object mapping each metadata name, in the author's spelling, to its value verbatim (multi-line values joined with `\n`). An entry without a name — a `[Metadata]` setting with nothing after it, which Robot Framework's model holds as an empty name with an empty value — is no metadata and SHALL be left out, in JSON and text output, for tests and for the suite metadata of `results log --suite-info`. The key SHALL be omitted when the test has no metadata and SHALL be absent on older Robot Framework versions. Suite items are unchanged.

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

`--search` in `discover` and `results` SHALL match test metadata names and values literally, as it matches ancestor-suite metadata. `discover all/tests/tasks` and `results show` SHALL accept `--show-metadata/--no-show-metadata`, with the same defaults as the tags flag (on for `discover all`, off for the others), that prints `- _Metadata:_ name: value, …` under each test in text output; `results log` SHALL print the metadata of a test under its header whenever present. JSON output SHALL NOT depend on these flags. Robot's own `--metadata name:value` option SHALL still be passed through to Robot by the discover commands. With Robot Framework older than 7.5 installed, the `--show-metadata/--no-show-metadata` flags SHALL NOT be listed in the commands' `--help`; passing them SHALL still be accepted and have no effect.

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

### Requirement: Render flags are named `--show-…`

The flags of `discover all/tests/tasks` and `results show` that add the tags line SHALL be named `--show-tags/--no-show-tags`, like `--show-metadata/--no-show-metadata`. The former name `--tags/--no-tags` SHALL NOT be a RobotCode option any more.

#### Scenario: Tags flag
- **WHEN** `robotcode discover tests --show-tags` runs
- **THEN** every test with tags is followed by a `- _Tags:_ …` line
- **AND** `robotcode discover tests --help` lists `--show-tags / --no-show-tags` and not `--tags`

### Requirement: Editor clients accept test metadata

The test discovery of the VS Code extension and of the IntelliJ plugin SHALL keep working when discover items carry `metadata`. The IntelliJ plugin's discover model SHALL declare the field, because it decodes the discover output strictly. The test explorers do not show the metadata.

#### Scenario: VS Code discovery with metadata
- **WHEN** the workspace is discovered on RF 7.5 and a test has metadata
- **THEN** the test is listed in the test explorer as every other test, with an unchanged description

#### Scenario: IntelliJ discovery with metadata
- **WHEN** the IntelliJ plugin decodes discover output containing `metadata` on a test item
- **THEN** decoding succeeds and the test is listed

### Requirement: Test hover shows metadata

The hover on a test or task name SHALL show its metadata as a `Metadata` block with one `name: value` line per entry, next to the Documentation and Tags blocks; tests without metadata SHALL render as before. The entries SHALL be the ones Robot Framework itself reports for the test: metadata names are case, space and underscore insensitive, the first spelling of a name is kept and its last value wins.

#### Scenario: Hover on a test with metadata
- **WHEN** the hover for a test with `[Metadata]    Issue    4409` is requested on RF 7.5
- **THEN** the hover contains a Metadata block with `Issue: 4409`

#### Scenario: Metadata setting without a name in the hover
- **WHEN** a test has only `[Metadata]` with nothing after it
- **THEN** the hover shows no Metadata block

#### Scenario: Repeated metadata name
- **WHEN** a test has `[Metadata]    Issue    4409` followed by `[Metadata]    issue    4410`
- **THEN** the hover shows one entry `Issue: 4410`, as `discover` and `results` report it

### Requirement: Result files with test metadata on older Robot Framework

When `robotcode results` cannot read an `output.xml` or `output.json` because it contains test-level metadata and the installed Robot Framework is older than 7.5, the error message SHALL say that the file was written by Robot Framework ≥ 7.5 with test metadata and needs Robot Framework ≥ 7.5 to be read.

#### Scenario: RF 7.5 output.xml read on RF 7.4
- **WHEN** `robotcode results show` is run on RF 7.4 against an `output.xml` that contains `<meta>` elements under a `<test>`
- **THEN** the command fails with a message naming Robot Framework 7.5 and test metadata as the cause
