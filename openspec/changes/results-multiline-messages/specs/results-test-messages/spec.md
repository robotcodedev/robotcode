# Spec Delta: results-test-messages

## Purpose

How the `robotcode results` commands show the failure and skip messages of tests, and how `--message-chars` shortens them.

## ADDED Requirements

### Requirement: Messages of several lines

`robotcode results show`, `results summary --failed` and `results diff` SHALL show the whole message of a test, every line of it as a line of the quote under the test. `--message-chars N` SHALL cut the message as a whole, line breaks counted, to N characters, and `--message-chars 0` SHALL show it whole. `results compare` SHALL put the message into its table cell with its lines joined by spaces.

#### Scenario: A failure of three lines
- **WHEN** a test fails with a message of three lines and `robotcode results show --failed` runs
- **THEN** all three lines stand in the quote under the test

#### Scenario: The list of failures in the summary
- **WHEN** a test fails with a message of three lines and `robotcode results summary --failed` runs
- **THEN** all three lines stand in the quote under the test

#### Scenario: A new failure in a diff
- **WHEN** a test passed in the baseline, fails with a message of three lines in the current run, and `robotcode results diff` runs
- **THEN** its entry shows all three lines

#### Scenario: A message cut to its length
- **WHEN** `robotcode results show --failed --message-chars 40` runs for a test whose message has three lines of 30 characters
- **THEN** the quote shows the first line and the first 9 characters of the second, as the line break counts as a character
- **AND** the JSON output has the whole message in `fullMessage`

#### Scenario: No limit
- **WHEN** `robotcode results show --failed --message-chars 0` runs
- **THEN** the quote shows the whole message, all its lines

#### Scenario: A failure of several lines in compare
- **WHEN** `robotcode results compare --show failures` runs over runs in which a test fails with a message of three lines
- **THEN** the group's message stands in one table cell, its three lines joined by spaces
