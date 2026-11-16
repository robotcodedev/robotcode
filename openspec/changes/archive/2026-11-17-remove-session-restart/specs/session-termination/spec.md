# Spec Delta: session-termination

## MODIFIED Requirements

### Requirement: A session ends a debug run at a stop the same way

When a debug session ends its run at a stop, through `robotcode session stop` or the idle timeout, it SHALL end the run as `.abort` does, so that the output files of that run can be read.

#### Scenario: `session stop` at a stop
- **WHEN** a debug session waits at a stop and `robotcode session stop <id>` runs
- **THEN** `robotcode results summary` reads the output file of that run

#### Scenario: Idle timeout at a stop
- **WHEN** a debug session waits at a stop until its idle timeout has passed
- **THEN** the session ends, and `robotcode results summary` reads the output file of that run
