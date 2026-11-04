# Spec Delta

## Purpose

How `robotcode results log --suite-info` shows the suites of a run: which suites get a header, in which order, and what a header holds.

## ADDED Requirements

### Requirement: Suite headers include the suites above a test

With `--suite-info`, the text output of `robotcode results log` SHALL show one header for every suite that holds a shown test, directly or through a suite below it, as `log.html` shows these suites. A header SHALL come before the headers of the suites below it and before the suite's own tests, and SHALL hold the suite's long name, source, status, documentation and metadata. The JSON output SHALL keep its form: `suites` lists these suites, and every test names the suite it lies in directly.

#### Scenario: Nested suites
- **WHEN** `robotcode results log --suite-info` reads a run with a top suite, a suite below it and two suites with tests below that one
- **THEN** the output has one `## Suite:` header per suite
- **AND** they come in the order of the run: the top suite, the suite below it, the first suite with its tests, the second suite with its tests

#### Scenario: Documentation and metadata of the top suite
- **WHEN** the top suite of that run has documentation and metadata in its `__init__.robot`
- **THEN** the header of the top suite shows them

#### Scenario: One test selected
- **WHEN** `robotcode results log --suite-info -bl "<long name of a test>"` reads that run
- **THEN** the output has the headers of that test's suite and of the suites above it
- **AND** no header of another suite

#### Scenario: One suite
- **WHEN** `robotcode results log --suite-info` reads a run of a single file
- **THEN** the output has one `## Suite:` header

#### Scenario: JSON output
- **WHEN** `robotcode --format json results log --suite-info` reads a run with nested suites
- **THEN** `suites` has an entry for the top suite and for each suite below it
- **AND** every test names the suite it lies in directly

#### Scenario: Without the option
- **WHEN** `robotcode results log` reads a run without `--suite-info`
- **THEN** the output has no `## Suite:` header
