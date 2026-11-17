# Spec Delta: results-test-messages

## Purpose

How the `robotcode results` commands show the failure and skip messages of tests, and how `--message-chars` shortens them.

## ADDED Requirements

### Requirement: Messages of several lines

`robotcode results show`, `results summary --failed` and `results diff` SHALL show every line of a test's message that they show as a line of the quote under the test. `results compare` SHALL put the lines it shows into its table cell, joined by spaces.

#### Scenario: A failure of three lines
- **WHEN** a test fails with a message of three lines and `robotcode results show --failed` runs
- **THEN** all three lines stand in the quote under the test

#### Scenario: The list of failures in the summary
- **WHEN** a test fails with a message of three lines and `robotcode results summary --failed` runs
- **THEN** all three lines stand in the quote under the test

#### Scenario: A new failure in a diff
- **WHEN** a test passed in the baseline, fails with a message of three lines in the current run, and `robotcode results diff` runs
- **THEN** its entry shows all three lines

#### Scenario: A failure of several lines in compare
- **WHEN** `robotcode results compare --show failures` runs over runs in which a test fails with a message of three lines
- **THEN** the group's message stands in one table cell, its three lines joined by spaces

### Requirement: Shortening a message

`results show`, `results summary`, `results diff` and `results compare` SHALL take `--message-chars N`, 120 by default, and show as many whole lines of a message, from the first, as fit into N characters, line breaks counted, followed by a line `... (M more lines)` for the M lines left out. A first line longer than N SHALL be cut to N characters and end in `...`. `--message-chars 0` SHALL show the whole message.

#### Scenario: Whole lines
- **WHEN** `robotcode results show --failed --message-chars 70` runs for a test whose message has three lines of 30 characters
- **THEN** the quote shows the first two lines and `... (1 more line)`
- **AND** the JSON output has the whole message in `fullMessage`

#### Scenario: A first line longer than the limit
- **WHEN** `robotcode results show --failed --message-chars 20` runs for that test
- **THEN** the quote shows the first 20 characters of the first line followed by `...`, and `... (2 more lines)`

#### Scenario: The summary by default
- **WHEN** `robotcode results summary --failed` runs for a test whose message has ten lines of 50 characters
- **THEN** the quote shows the first two lines and `... (8 more lines)`

#### Scenario: No limit
- **WHEN** `robotcode results show --failed --message-chars 0` runs for a test whose message has ten lines
- **THEN** the quote shows all ten lines
