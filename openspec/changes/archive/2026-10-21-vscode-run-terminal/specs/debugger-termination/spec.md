# Spec Delta

## ADDED Requirements

### Requirement: A terminate request after the run has ended

When a `terminate` request arrives after the debugger has reported the end of the run with the `exited` event, the debugger SHALL NOT interrupt its process. The process SHALL end with the exit code of the run, as after a `disconnect` alone.

#### Scenario: Run from VS Code's Test Explorer

- **WHEN** a run from the Test Explorer passes and VS Code sends `disconnect` and then `terminate` after the `exited` event
- **THEN** the process ends with exit code 0

#### Scenario: Terminate during the run

- **WHEN** the client sends `terminate` while the run is still in progress
- **THEN** the debugger interrupts the run as before
