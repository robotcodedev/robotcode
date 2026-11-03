# Spec Delta

## ADDED Requirements

### Requirement: `.abort` ends a robot-debug run like SIGTERM

At a stop of `robotcode robot-debug`, `.abort` SHALL end the run as SIGTERM does: the current test SHALL fail with `Execution terminated by signal`, the remaining tests SHALL NOT run, teardowns SHALL run without further stops, and the output files SHALL be written. The process SHALL exit with 253.

#### Scenario: A result that can be read
- **WHEN** `robotcode robot-debug -o output.xml` waits at a stop in the first of two tests and `.abort` is given
- **THEN** the process exits with 253
- **AND** `robotcode results summary -o output.xml` reads the file, and the first test failed with `Execution terminated by signal`

#### Scenario: A teardown with a breakpoint
- **WHEN** the test has a `[Teardown]` with a line breakpoint and `.abort` is given at a stop in the test
- **THEN** the teardown runs and the run doesn't stop in it

### Requirement: A session ends a debug run at a stop the same way

When a debug session ends its run at a stop, through `robotcode session stop`, `robotcode session restart` or the idle timeout, it SHALL end the run as `.abort` does, so that the output files of that run can be read.

#### Scenario: `session stop` at a stop
- **WHEN** a debug session waits at a stop and `robotcode session stop <id>` runs
- **THEN** `robotcode results summary` reads the output file of that run

#### Scenario: Idle timeout at a stop
- **WHEN** a debug session waits at a stop until its idle timeout has passed
- **THEN** the session ends, and `robotcode results summary` reads the output file of that run
