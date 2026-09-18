# Spec Delta

## Purpose

Defines how test- and task-level metadata (Robot Framework ≥ 7.5) is represented and shown across RobotCode — in discover and results output, search, the VS Code test explorer, the IntelliJ discover model and the test hover — and how result files containing it are handled on older Robot Framework versions.

## ADDED Requirements

### Requirement: Test metadata in discover and results JSON

On Robot Framework ≥ 7.5, test and task items in the JSON output of `discover all`, `discover tests`, `discover tasks`, `results show`, `results summary --failed` and `results log` SHALL carry a `metadata` object mapping each metadata name, in the author's spelling, to its value verbatim (multi-line values joined with `\n`). The key SHALL be omitted when the test has no metadata and SHALL be absent on older Robot Framework versions. Suite items are unchanged.

#### Scenario: Discover on RF 7.5
- **WHEN** a suite contains a test with `[Metadata]    Issue    4409` and `[Metadata]    Owner Team    core` and `robotcode --format json discover tests` runs on RF 7.5
- **THEN** the item has `"metadata": {"Issue": "4409", "Owner Team": "core"}`
- **AND** a test without metadata in the same suite has no `metadata` key

#### Scenario: Results on RF 7.5
- **WHEN** the same suite was executed on RF 7.5 and `robotcode --format json results show` and `results log` are run on its `output.xml`
- **THEN** the corresponding test entries carry the same `metadata` object

#### Scenario: Older Robot Framework
- **WHEN** `robotcode --format json discover tests` runs on RF 7.4
- **THEN** no item has a `metadata` key

### Requirement: Search and text output include test metadata

`--search` in `discover` and `results` SHALL match test metadata names and values literally, as it matches ancestor-suite metadata. `discover all/tests/tasks` and `results show` SHALL accept `--metadata/--no-metadata` (default off) that prints `- _Metadata:_ name: value, …` under each test in text output; `results log` SHALL print the metadata of a test under its header whenever present. JSON output SHALL NOT depend on these flags.

#### Scenario: Search by metadata value
- **WHEN** `robotcode discover tests --search 4409` runs on RF 7.5 against the suite above
- **THEN** only the test whose metadata contains `4409` is listed

#### Scenario: Text output with metadata
- **WHEN** `robotcode discover tests --metadata` runs on RF 7.5
- **THEN** the test is followed by `- _Metadata:_ Issue: 4409, Owner Team: core`
- **AND** without `--metadata` no such line is printed

### Requirement: Test explorer shows metadata

The VS Code test explorer SHALL show a test's metadata compactly in the item description (`test  - Issue: 4409, Owner Team: core`, truncated like other descriptions) and SHALL refresh the item when only its metadata changed. The IntelliJ plugin's discover model SHALL accept items that carry `metadata` so discovery keeps working on RF 7.5 projects.

#### Scenario: Explorer description
- **WHEN** the workspace is discovered on RF 7.5 and a test has metadata
- **THEN** the test item's description contains `Issue: 4409`

#### Scenario: Metadata-only edit
- **WHEN** only the value of a test's `[Metadata]` changes and the file is saved
- **THEN** the explorer updates the item's description

#### Scenario: IntelliJ discovery with metadata
- **WHEN** the IntelliJ plugin decodes discover output containing `metadata` on a test item
- **THEN** decoding succeeds and the test is listed

### Requirement: Test hover shows metadata

The hover on a test or task name SHALL show its metadata as a `Metadata` block with one `name: value` line per entry, next to the Documentation and Tags blocks; tests without metadata SHALL render as before.

#### Scenario: Hover on a test with metadata
- **WHEN** the hover for a test with `[Metadata]    Issue    4409` is requested on RF 7.5
- **THEN** the hover contains a Metadata block with `Issue: 4409`

### Requirement: Result files with test metadata on older Robot Framework

When `robotcode results` cannot read an `output.xml` or `output.json` because it contains test-level metadata and the installed Robot Framework is older than 7.5, the error message SHALL say that the file was written by Robot Framework ≥ 7.5 with test metadata and needs Robot Framework ≥ 7.5 to be read.

#### Scenario: RF 7.5 output.xml read on RF 7.4
- **WHEN** `robotcode results show` is run on RF 7.4 against an `output.xml` that contains `<meta>` elements under a `<test>`
- **THEN** the command fails with a message naming Robot Framework 7.5 and test metadata as the cause
