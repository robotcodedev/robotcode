# Spec Delta

## ADDED Requirements

### Requirement: Ctrl-C attaches the debugger in a robot-debug run

When a `robotcode robot-debug` run executes with the debugger detached, by `--no-debugger-attached` or after `.detach`, Ctrl-C SHALL attach the debugger and SHALL then pause at the next keyword, as with an attached debugger. A second Ctrl-C before the pause SHALL interrupt the keyword that runs. In a REPL session with the debugger detached, Ctrl-C SHALL keep interrupting the keyword that runs.

#### Scenario: Run started without the debugger

- **WHEN** `robotcode robot-debug --no-debugger-attached` runs a keyword that sleeps 3 seconds and then `Log To Console    next`, and the user presses Ctrl-C while the keyword sleeps
- **THEN** a message says that the run pauses at the next keyword, the sleeping keyword passes, and the run stops with `* pause` at `Log To Console`

#### Scenario: After .detach

- **WHEN** the user enters `.detach` at a stop and presses Ctrl-C while a later keyword runs
- **THEN** the run stops with `* pause` at the next keyword

## REMOVED Requirements

### Requirement: Ctrl-C ends a robot-debug run without the debugger

**Reason**: Ctrl-C now attaches the debugger in such a run and pauses (requirement "Ctrl-C attaches the debugger in a robot-debug run").
**Migration**: To end the run, enter `.abort` at the stop that Ctrl-C brings, or send SIGTERM, which still ends a `robot-debug` run as Robot Framework does.
