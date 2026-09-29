# Spec Delta

## Purpose

Defines how tests and tasks are selected by their metadata (Robot Framework ≥ 7.5) in RobotCode — the entries a test is matched by and the pattern syntax, the selection options of `robot`, `robot-debug`, `discover` and `results`, the stand-alone pre-run modifiers, the `discover metadata` index of test and suite metadata, and the behaviour with older Robot Framework versions.

## ADDED Requirements

### Requirement: Metadata entries of a test

A test or task SHALL be matched by its metadata entries: for every metadata item with a name, one entry `Name:Line` for every line of its value that is not empty, or a single entry `Name:` when the value has no such line. Cells of one `[Metadata]` row, which Robot Framework joins into one line, SHALL NOT be split. The metadata of the test's suites SHALL NOT be part of its entries. A test without metadata, and every test when the installed Robot Framework is older than 7.5, SHALL have no entries. Values SHALL be used as the model holds them: `robot`, `robot-debug` and `discover` see them before variables are replaced, `results` after.

#### Scenario: Multi-line value
- **WHEN** a test has `[Metadata]    Issue    4409` continued with `...    5769` on the next line
- **THEN** both `--by-test-metadata Issue:4409` and `--by-test-metadata Issue:5769` select it

#### Scenario: Several cells in one row
- **WHEN** a test has `[Metadata]    Issue    4409    5769`
- **THEN** `--by-test-metadata Issue:4409` does not select it
- **AND** `--by-test-metadata "Issue:4409*"` does

#### Scenario: Metadata without a value
- **WHEN** a test has `[Metadata]    Owner` with nothing after the name
- **THEN** `--by-test-metadata "Owner:*"` selects it

#### Scenario: Suite metadata
- **WHEN** a suite has `Metadata    Owner    core` and its test has no metadata
- **THEN** `--by-test-metadata Owner:core` does not select the test

#### Scenario: Variables in values
- **WHEN** a test has `[Metadata]    Build    ${BUILD}` and is run with `--variable BUILD:42`
- **THEN** `robotcode robot --by-test-metadata 'Build:${BUILD}'` runs it and `robotcode robot --by-test-metadata Build:42` does not
- **AND** `robotcode results show --by-test-metadata Build:42` on the result of that run lists it

### Requirement: Metadata patterns

A metadata pattern SHALL consist of one or more terms `NAME:VALUE` combined with the operators `AND`, `OR` and `NOT`. An operator SHALL be recognised only as a word of its own: `AND`, `OR` or `NOT` in upper case, with whitespace or the start or end of the pattern on both sides. Everything else, including `AND`, `OR` and `NOT` inside a word or in lower case, SHALL belong to a term. A term SHALL match a test when it matches one of the test's entries; `*`, `?` and `[…]` SHALL work as in tag patterns, and case, spaces and underscores SHALL be ignored on both sides, so the name part compares as Robot Framework compares metadata names. The operators SHALL combine terms as in Robot Framework's tag patterns: `AND` binds before `OR` and `NOT` last, so `A NOT B NOT C` matches when `A` matches and neither `B` nor `C` does, and a pattern starting with `NOT` matches every test that does not match the rest. A term without `:`, and an operator without a term on both sides (apart from a leading `NOT`), SHALL make the pattern invalid; a command given an invalid pattern SHALL fail with an error that names the pattern, and select, run or list nothing.

#### Scenario: Terms combined with AND
- **WHEN** a test has `Issue: 4409` and `Author: Hans Müller`
- **THEN** `Issue:4409 AND Author:Hans*` selects it
- **AND** `Issue:4409 AND Author:Eva*` does not

#### Scenario: Missing metadata with NOT
- **WHEN** one test by `Author: Hans Müller` has `Reviewer: Eva Schmidt` and another test by him has no `Reviewer`
- **THEN** `Author:Hans* NOT Reviewer:*` selects only the second test
- **AND** `NOT Reviewer:*` selects every test without a `Reviewer`

#### Scenario: Any name
- **WHEN** one test has `Issue: 4409` and another has `Requirement: 4409`
- **THEN** `*:4409` selects both

#### Scenario: Name spelling
- **WHEN** a test has `Owner Team: core`
- **THEN** `owner_team:core` and `OWNERTEAM:Core` select it

#### Scenario: Upper-case values
- **WHEN** a test has `Issue: CORE-123` and another has `Author: NORBERT`
- **THEN** `Issue:CORE-123` selects the first and `Author:NORBERT` the second, also on Robot Framework 7.5, where the same text as a tag pattern would be read as `C OR E-123` and `N OR BERT`

#### Scenario: Operator word inside a value
- **WHEN** a test has `Title: Rock AND Roll`
- **THEN** `Title:rock and roll` selects it, because operators are upper case only and spaces are ignored
- **AND** `Title:Rock AND Roll` is rejected as invalid, because its second term `Roll` has no `:`

#### Scenario: Operator without a term
- **WHEN** `--by-test-metadata "Issue:4409 AND"` or `--by-test-metadata "AND Issue:4409"` is given
- **THEN** the pattern is rejected as invalid

#### Scenario: Operator precedence
- **WHEN** test A has `Issue: 1`, test B has `Issue: 2` and `Author: Eva`, and test C has `Issue: 2` and `Author: Hans`
- **THEN** `Issue:1 OR Issue:2 AND Author:Eva` selects A and B but not C

#### Scenario: Invalid pattern
- **WHEN** `robotcode robot --by-test-metadata Issue` runs
- **THEN** the command fails with an error that names the pattern `Issue`
- **AND** no test is run

### Requirement: Selecting tests by metadata in runs and discovery

`robot`, `robot-debug` and every `discover` command SHALL accept `-btm/--by-test-metadata PATTERN` and `-ebtm/--exclude-by-test-metadata PATTERN`, each any number of times. With `--by-test-metadata` only tests matching at least one of its patterns SHALL remain; with `--exclude-by-test-metadata` every test matching one of its patterns SHALL be removed. Both SHALL narrow the selection of every other option — Robot's `--include`, `--exclude`, `--suite` and `--test`, and RobotCode's `--by-longname`, `--exclude-by-longname` and `--search` — so a test remains only if it passes all of them. Suites without remaining tests SHALL be removed as with `--by-longname`. `robot-debug` SHALL pass the options on to the run it debugs.

#### Scenario: Discover by metadata
- **WHEN** `robotcode discover tests --by-test-metadata Issue:4409` runs on a suite where one test has `Issue: 4409`, one `Issue: 4410` and one no metadata
- **THEN** only the test with `Issue: 4409` is listed

#### Scenario: Several patterns
- **WHEN** `robotcode discover tests -btm Issue:4409 -btm Issue:4410` runs on the same suite
- **THEN** the tests with `Issue: 4409` and `Issue: 4410` are listed

#### Scenario: Excluding tests
- **WHEN** `robotcode discover tests --exclude-by-test-metadata "Issue:*"` runs on the same suite
- **THEN** only the test without metadata is listed

#### Scenario: Combined with a tag selection
- **WHEN** two tests have `Issue: 4409`, only one of them is tagged `smoke`, and `robotcode discover tests --include smoke --by-test-metadata Issue:4409` runs
- **THEN** only the tagged test is listed

#### Scenario: Running by metadata
- **WHEN** `robotcode robot --by-test-metadata Issue:4409` runs the suite
- **THEN** only the test with `Issue: 4409` is executed

#### Scenario: Debugging by metadata
- **WHEN** `robotcode robot-debug --by-test-metadata Issue:4409` runs the suite
- **THEN** the debugged run executes only the test with `Issue: 4409`

### Requirement: Filtering results by metadata

`results summary`, `results show`, `results log`, `results stats` and `results diff` SHALL accept `-btm/--by-test-metadata PATTERN` and `-ebtm/--exclude-by-test-metadata PATTERN` with the same meaning, applied to the tests of the result files together with the other filters. When one of them is given, the applied filters SHALL list it under `by-test-metadata` or `exclude-by-test-metadata` with the patterns as given. An invalid pattern SHALL fail the command as an invalid tag pattern does.

#### Scenario: Results of the tests for an issue
- **WHEN** a suite with one test with `Issue: 4411` among others was executed and `robotcode results show --by-test-metadata Issue:4411` runs on its `output.xml`
- **THEN** only that test is shown

#### Scenario: Applied filters
- **WHEN** `robotcode --format json results show --by-test-metadata Issue:4411` runs
- **THEN** `filtersApplied` contains `"by-test-metadata": ["Issue:4411"]`

### Requirement: Stand-alone pre-run modifiers

The package `robotcode-modifiers` SHALL provide the pre-run modifiers `robotcode.modifiers.ByTestMetadata` and `robotcode.modifiers.ExcludedByTestMetadata`. They SHALL take metadata patterns as arguments and select like `--by-test-metadata` and `--exclude-by-test-metadata`. They SHALL work with plain `robot --prerunmodifier`, where the arguments are separated from the name with `;` because patterns contain `:`, and in the `pre-run-modifiers` setting of `robot.toml`. Given an invalid pattern, they SHALL report the error and select no test; Robot Framework SHALL NOT end up running the suite without them.

#### Scenario: Plain robot
- **WHEN** `robot --prerunmodifier "robotcode.modifiers.ByTestMetadata;Issue:4409"` runs the suite with `robotcode-modifiers` installed
- **THEN** only the test with `Issue: 4409` is executed

#### Scenario: Invalid pattern in a stand-alone modifier
- **WHEN** `robot --prerunmodifier "robotcode.modifiers.ExcludedByTestMetadata;Issue"` runs the suite
- **THEN** an error naming the pattern `Issue` is reported
- **AND** no test is executed

#### Scenario: Profile in robot.toml
- **WHEN** a `robot.toml` profile sets `pre-run-modifiers = { "robotcode.modifiers.ByTestMetadata" = ["Issue:4409"] }` and `robotcode --profile <that profile> discover tests` runs
- **THEN** only the test with `Issue: 4409` is listed

### Requirement: Metadata index

`robotcode discover metadata` SHALL list, by name, the metadata of the discovered tests and tasks and, in a separate section, the metadata of the discovered suites, including metadata given to Robot with `--metadata`. Both sections SHALL be built from entries as defined for tests, applied to each test's or suite's own metadata; the test section therefore lists exactly what `--by-test-metadata` can select, and suite metadata SHALL NOT be selectable by it. Names Robot Framework treats as the same SHALL be one name, and values the patterns do not tell apart SHALL be one value; each SHALL be shown in the first spelling found, and names and values SHALL be sorted. The text output SHALL list only the names; `--values` SHALL add the values of each name, and `--tests`, `--tasks` and `--suites` SHALL add the tests, tasks or suites under each value, or under each name without `--values`. The JSON output SHALL map every name to its values and every value to the items that have it, test and task metadata under `metadata` and suite metadata under `suiteMetadata`, independent of these flags. Robot's options, `--by-longname`, `--by-test-metadata`, `--search` and their exclusions SHALL narrow the discovered tests and suites before the index is built.

#### Scenario: Names
- **WHEN** a suite has tests with `Issue: 4409`, with `Owner Team: core` and `Issue: 4410`, and with a two-line `Description`, and `robotcode discover metadata` runs
- **THEN** the test section lists `Description`, `Issue` and `Owner Team`, in this order, without values

#### Scenario: Values and tests
- **WHEN** `robotcode discover metadata --values --tests` runs on the same suite
- **THEN** `Issue` lists the values `4409` and `4410`, each with the test that has it
- **AND** `Description` lists each of its two lines as a value

#### Scenario: JSON
- **WHEN** `robotcode --format json discover metadata` runs on the same suite
- **THEN** `metadata.Issue["4409"]` holds the item of the test with `Issue: 4409`

#### Scenario: Spellings of a name
- **WHEN** one test has `Issue: 4409` and a later one `issue: 4410`
- **THEN** one name `Issue` is listed, with both values

#### Scenario: Narrowed index
- **WHEN** only the test with `Issue: 4409` is tagged `smoke` and `robotcode discover metadata --include smoke --values` runs
- **THEN** `Issue` lists only `4409`, and `Owner Team` is not listed

#### Scenario: Suite metadata in its own section
- **WHEN** a suite has `Metadata    Version    1.0`, its tests have no `Version`, and `robotcode discover metadata --values --suites` runs
- **THEN** the suite section lists `Version` with the value `1.0` and the suite under it
- **AND** the test section does not list `Version`, and `--by-test-metadata Version:1.0` selects no test

#### Scenario: Metadata given to Robot
- **WHEN** `robotcode --format json discover metadata --metadata Build:42` runs
- **THEN** `suiteMetadata.Build["42"]` holds the item of the top-level suite

### Requirement: Metadata selection with older Robot Framework

With Robot Framework older than 7.5 installed, `--by-test-metadata`, `--exclude-by-test-metadata` and `discover metadata` SHALL NOT be listed in `--help`. They SHALL still be accepted: no test has metadata there, so `--by-test-metadata` selects no test, `--exclude-by-test-metadata` removes none, and `discover metadata` lists only the suite metadata. The generated CLI reference SHALL mark them as needing Robot Framework 7.5, as the requirement of `cli-reference-generation` on version-dependent commands and options describes.

#### Scenario: Help on RF 7.4
- **WHEN** `robotcode robot --help`, `robotcode discover tests --help` and `robotcode results show --help` run on RF 7.4
- **THEN** none of them lists `--by-test-metadata` or `--exclude-by-test-metadata`, and `robotcode discover --help` does not list the command `metadata`
- **AND** on RF 7.5 they do

#### Scenario: Options on RF 7.4
- **WHEN** `robotcode discover tests --exclude-by-test-metadata "Issue:*"` runs on RF 7.4
- **THEN** the same tests are listed as without the option
- **AND** `robotcode discover tests --by-test-metadata "Issue:*"` lists no test

#### Scenario: Metadata index on RF 7.4
- **WHEN** `robotcode discover metadata --values` runs on RF 7.4 on a suite with `Metadata    Version    1.0`
- **THEN** the suite section lists `Version` with `1.0`
- **AND** no test metadata is listed
