# test-discovery Specification

## Purpose

Defines what `robotcode discover` reports for the tests and tasks of a project — their IDs, lines and ranges — and that runs report each test under the same ID, so that the editor clients can match results to the tests they show.

## Requirements

### Requirement: Tests and tasks without a line number are discovered

When a test or task has no line number, as one that a custom parser or a pre-run modifier creates without one, `robotcode discover` SHALL list it like any other test or task instead of failing. Its JSON item SHALL have no `lineno` and no `range`, and its ID SHALL end in `;0`, as `<source>;<long name>;0`. Robot Framework's line numbers start at 1, so `0` names no line. A warning about another test with the same name SHALL name no line for it.

#### Scenario: A custom parser as in Robot Framework's User Guide

- **WHEN** a project's `robot.toml` configures a parser that creates its tests with `suite.tests.create(name=...)`, without a line number, and `robotcode --format json discover all` runs on it
- **THEN** the command succeeds, the tests appear with their names and long names, without `lineno` and `range`, and their IDs end in `;0`

#### Scenario: A test added by a pre-run modifier

- **WHEN** a pre-run modifier adds a test without a line number to a suite file with other tests, and `robotcode --format json discover all` runs on it
- **THEN** the added test appears next to the others, without `lineno` and `range`, with an ID that ends in `;0`, and the other tests keep their lines, ranges and IDs

#### Scenario: Two tests with the same name, one without a line number

- **WHEN** a suite has two tests with the same name and one of them has no line number
- **THEN** the warning about the duplicate name names no line for the test without one

### Requirement: Runs report a test under the ID of its discovery

The events with which a run reports its tests, when it enqueues them, when a test starts and ends, when a failing suite teardown marks its tests again, and when a test logs a warning or an error, SHALL carry the ID that `robotcode discover` gives the test, also when the test has no line number. A line number that Robot Framework does not know SHALL be empty in these events on every Robot Framework version, for the test and for its keywords.

#### Scenario: Run of a test without a line number

- **WHEN** a run executes a suite whose parser creates its tests without line numbers
- **THEN** each test is enqueued, started and ended under the ID that `robotcode discover` reports for it, ending in `;0`, and the events' `lineno` is empty

#### Scenario: Warning of a test without a line number

- **WHEN** a pre-run modifier adds a test without a line number that logs a warning and then fails, and a run executes it
- **THEN** the warning's event carries the ID that `robotcode discover` reports for the test, and the line numbers of the test and of its failed keyword are empty in the events, also with Robot Framework 6.1 and older

#### Scenario: Test count in PyCharm

- **WHEN** PyCharm runs such a suite
- **THEN** the run's test count includes the tests without a line number
