# Spec Delta

## Purpose

Defines how `robotcode results diff` compares two result files and what its exit code tells about the differences it found, so that a CI step or an agent can act on it without reading the output.

## ADDED Requirements

### Requirement: No exit code for differences without the option

Without `--exit-code` and `--exit-code-mask`, `robotcode results diff` SHALL exit with 0 when it has compared the two files, whatever differences it found.

#### Scenario: New failure without the option
- **WHEN** `robotcode results diff base.xml new.xml` runs, where a test passed in `base.xml` and fails in `new.xml`
- **THEN** the new failure is shown
- **AND** the process exits with code 0

### Requirement: Exit code of the categories

With `--exit-code`, `robotcode results diff` SHALL exit with 0 when the diff it shows has no entries. Otherwise it SHALL exit with the sum of the values of the categories that have at least one entry: 1 for new failures, 2 for new passes, 4 for status changes, 8 for added tests and 16 for removed tests.

#### Scenario: No differences
- **WHEN** `robotcode results diff base.xml base.xml --exit-code` runs
- **THEN** the process exits with code 0

#### Scenario: New failure
- **WHEN** `robotcode results diff base.xml new.xml --exit-code` runs, where the only difference is a test that passed in `base.xml` and fails in `new.xml`
- **THEN** the process exits with code 1

#### Scenario: New pass
- **WHEN** the only difference is a test that failed in `base.xml` and passes in `new.xml`, and `robotcode results diff base.xml new.xml --exit-code` runs
- **THEN** the process exits with code 2

#### Scenario: Status change
- **WHEN** the only difference is a test that was skipped in `base.xml` and fails in `new.xml`, and `robotcode results diff base.xml new.xml --exit-code` runs
- **THEN** the process exits with code 4

#### Scenario: Added test
- **WHEN** the only difference is a test that exists only in `new.xml`, and `robotcode results diff base.xml new.xml --exit-code` runs
- **THEN** the process exits with code 8

#### Scenario: Removed test
- **WHEN** the only difference is a test that exists only in `base.xml`, and `robotcode results diff base.xml new.xml --exit-code` runs
- **THEN** the process exits with code 16

#### Scenario: Several categories
- **WHEN** the diff has a new failure and a removed test, and `robotcode results diff base.xml new.xml --exit-code` runs
- **THEN** the process exits with code 17

### Requirement: The exit code counts what the diff shows

The exit code SHALL count only the categories and tests that the diff shows: categories left out by `--only` and tests left out by the filter options SHALL NOT count.

#### Scenario: Only new failures
- **WHEN** the diff has a new failure and an added test, and `robotcode results diff base.xml new.xml --only new-failures --exit-code` runs
- **THEN** only the new failure is shown
- **AND** the process exits with code 1

#### Scenario: A category without entries
- **WHEN** the only difference is a new failure, and `robotcode results diff base.xml new.xml --only added --exit-code` runs
- **THEN** the process exits with code 0

#### Scenario: Filter
- **WHEN** the only new failure is a test without the tag `smoke`, and `robotcode results diff base.xml new.xml --include smoke --exit-code` runs
- **THEN** the process exits with code 0

### Requirement: Exit code mask

`--exit-code-mask` SHALL take the categories it lists out of the exit code and keep them in the output. It SHALL take the names that `--only` takes, and `all` for every category, repeated or separated by commas. It SHALL turn on the exit code of the categories as `--exit-code` does.

#### Scenario: Masked category
- **WHEN** the diff has a new failure and an added test, and `robotcode results diff base.xml new.xml --exit-code --exit-code-mask added` runs
- **THEN** the new failure and the added test are shown
- **AND** the process exits with code 1

#### Scenario: Several masked categories
- **WHEN** the diff has a new pass, an added test and a removed test, and `robotcode results diff base.xml new.xml --exit-code-mask new-passes,added --exit-code-mask removed` runs
- **THEN** the process exits with code 0

#### Scenario: Mask without --exit-code
- **WHEN** the diff has a new failure and an added test, and `robotcode results diff base.xml new.xml --exit-code-mask added` runs
- **THEN** the process exits with code 1

#### Scenario: Everything masked
- **WHEN** the diff has a new failure, and `robotcode results diff base.xml new.xml --exit-code-mask all` runs
- **THEN** the new failure is shown
- **AND** the process exits with code 0

### Requirement: Same exit code in every output format

The exit code of the categories SHALL NOT depend on the output format.

#### Scenario: JSON output
- **WHEN** the only difference is a new failure, and `robotcode --format json results diff base.xml new.xml --exit-code` runs
- **THEN** the JSON output lists the new failure
- **AND** the process exits with code 1

### Requirement: The help names the exit codes

`robotcode results diff --help` SHALL say what each exit code means: 0, the value of each category, and 128 for an error.

#### Scenario: Help
- **WHEN** `robotcode results diff --help` runs
- **THEN** its text names the exit codes 0, 1, 2, 4, 8, 16 and 128 with their meaning
