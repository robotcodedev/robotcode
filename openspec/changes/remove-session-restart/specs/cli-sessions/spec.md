# Spec Delta: cli-sessions

## MODIFIED Requirements

### Requirement: The end of a REPL or a run

When the REPL of a session exits or its run ends, the session SHALL stay open. The command that waits, or else the next `wait`, SHALL print the rest of the output and that the REPL or the run has ended with its exit code, and exit as for its input. The exit code of the REPL or the run SHALL NOT be the exit code of a `session` command. A `send` or an `interrupt` after the end SHALL fail with exit code 252.

#### Scenario: End of a debug run
- **WHEN** `send` gives `.continue` to a debug session and the run, in which two tests fail, reaches its end
- **THEN** `send` prints the rest of the run's output and `The run has ended with exit code 2.`, and exits with 0
- **AND** the session stays open

#### Scenario: The end while no command waits
- **WHEN** `send --timeout 1` gives `.continue` to a debug session and exits with 124, and the run ends before the next command
- **THEN** `robotcode session wait` prints the rest of the run's output and that the run has ended with its exit code, and exits with 0

#### Scenario: `.exit` in a REPL session
- **WHEN** `send` gives `.exit` to a REPL session in which a statement failed
- **THEN** it prints `The REPL has ended with exit code 1.` and exits with 0
- **AND** the session stays open

#### Scenario: A send after the end
- **WHEN** `send` gives `Log    hello` to a session whose run has ended
- **THEN** it says that the run has ended, that `robotcode session result` prints its exit code and that `robotcode session stop` ends the session, and exits with 252

## ADDED Requirements

### Requirement: Sessions that have ended

A session SHALL count as ended when nothing listens on its channel any more, also when another process has its process ID, and the next `session` command that finds its file SHALL remove its files. A session whose channel a command can't reach for another reason, such as a sandbox that forbids it, SHALL keep its files.

#### Scenario: The process of a session has gone
- **WHEN** the process of a session has ended without removing its file, after a crash for example
- **THEN** the next `robotcode session list` doesn't show it and removes its files

#### Scenario: Another process ID in a sandbox
- **WHEN** a `session` command runs where the process ID of an open session belongs to no process, as in a sandbox with processes of its own
- **THEN** it reaches the session as it does elsewhere

#### Scenario: A channel the command may not reach
- **WHEN** `robotcode session send` can't connect to the channel of an open session, because a sandbox forbids it for example
- **THEN** it says that the session doesn't answer and exits with code 252
- **AND** the session keeps its files

## REMOVED Requirements

### Requirement: Restarting a session

**Reason**: A session can't start again under its wrapper in a new process that the old process starts itself (#690, measured with `xvfb-run`). Removed by the maintainer on 2026-11-16 instead of being rebuilt; the sessions haven't been released.

**Migration**: End the session with `robotcode session stop <id>` and start a new one with `robotcode session start`, giving the breakpoints again with `--break`.

### Requirement: Ended sessions

**Reason**: Replaced by "Sessions that have ended", the same requirement without the session that restarts. A scenario can't be dropped from a modified requirement.

**Migration**: None; the behavior for sessions that have ended stays as it is.
