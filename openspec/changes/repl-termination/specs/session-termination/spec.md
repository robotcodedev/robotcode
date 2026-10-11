# Spec Delta

## Purpose

Defines how `robotcode repl`, `robotcode repl-server` and `robotcode robot-debug` end when they receive SIGTERM, so that `kill` or a process manager can end them while they wait.

## ADDED Requirements

### Requirement: SIGTERM ends a REPL session

`robotcode repl` and `robotcode repl-server` SHALL end their session when they receive SIGTERM, also while they wait for input or for a client. A keyword that runs SHALL be interrupted first. The session SHALL end as at the end of the input, without running input that isn't complete; its output files SHALL be written, and the process SHALL exit with code 253.

#### Scenario: Waiting for input
- **WHEN** `robotcode repl -o output.xml` waits for input from a pipe that stays open and receives SIGTERM
- **THEN** the process exits with code 253
- **AND** `output.xml` contains the session test

#### Scenario: Keyword that runs
- **WHEN** `robotcode repl` receives SIGTERM while `Sleep    30` runs
- **THEN** the keyword is interrupted
- **AND** the process exits with code 253

#### Scenario: Unfinished input
- **WHEN** `robotcode repl` receives SIGTERM while a `FOR` loop has been entered without its `END`
- **THEN** the loop doesn't run
- **AND** the process exits with code 253

#### Scenario: repl-server waiting for a client
- **WHEN** `robotcode repl-server` waits for a client and receives SIGTERM
- **THEN** the process exits with code 253

### Requirement: SIGTERM ends a robot-debug run like Robot Framework

When `robotcode robot-debug` receives SIGTERM, it SHALL end the run as Robot Framework ends a run on SIGTERM: the current test SHALL fail with `Execution terminated by signal`, the remaining tests SHALL NOT run, and the output files SHALL be written. While it waits at a stop, it SHALL stop pausing and resume first.

#### Scenario: Waiting at a stop
- **WHEN** `robotcode robot-debug -o output.xml` waits at a stop in the first of two tests and receives SIGTERM
- **THEN** the first test fails with `Execution terminated by signal`
- **AND** the second test isn't executed
- **AND** `output.xml` is written

#### Scenario: Keyword that runs
- **WHEN** `robotcode robot-debug` receives SIGTERM while `Sleep    30` runs and no stop is active
- **THEN** the test fails with `Execution terminated by signal`
- **AND** the run ends

### Requirement: A second SIGTERM forces the end

When `robotcode repl`, `robotcode repl-server` or `robotcode robot-debug` receives a second SIGTERM before it has ended, the process SHALL end at once with exit code 253, as Robot Framework does.

#### Scenario: Two signals
- **WHEN** a session receives SIGTERM twice before it has ended
- **THEN** the process exits with code 253 without waiting for the session to end
