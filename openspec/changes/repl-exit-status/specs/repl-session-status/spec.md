# Spec: repl-session-status

## Purpose

Defines the status of a `robotcode repl` session: the result of the session test in the output files, the process exit code for interactive and non-interactive use, how it can be overridden, and how a session can end with an explicit exit code.

## ADDED Requirements

### Requirement: Session test reflects unhandled failures

The session test that `robotcode repl` writes to `output.xml`, `log.html` and `report.html` SHALL have status FAIL when at least one input statement — a keyword call or a control structure — failed during the session without being handled, and PASS otherwise. The test message SHALL be Robot Framework's combined failure message for the unhandled failures. This SHALL apply to interactive and non-interactive sessions alike, and the output files SHALL remain valid.

A failure SHALL count as handled when it does not propagate to the REPL, for example inside `TRY`/`EXCEPT`, `Run Keyword And Expect Error` or `Run Keyword And Ignore Error`. `Skip` and `Pass Execution` SHALL NOT count as failures.

#### Scenario: Failing keyword followed by successful input
- **WHEN** `Fail    boom` and then `Log    after` are entered in a session run with `-o output.xml`
- **THEN** `after` is logged
- **AND** the session test in `output.xml` has status FAIL with a message containing `boom`
- **AND** `output.xml` can be read by `rebot`

#### Scenario: Failing control structure
- **WHEN** a `FOR` loop over a variable that does not exist is entered in a session run with `-o output.xml`
- **THEN** the session test in `output.xml` has status FAIL

#### Scenario: Handled failures
- **WHEN** a session only contains failures inside `TRY`/`EXCEPT`, `Run Keyword And Expect Error` or `Run Keyword And Ignore Error`
- **THEN** the session test has status PASS

#### Scenario: Skip and Pass Execution
- **WHEN** a session contains `Skip` or `Pass Execution` and no other failures
- **THEN** the session test has status PASS

#### Scenario: Interactive session with a failure
- **WHEN** a keyword fails in an interactive terminal session run with `-o output.xml`
- **THEN** the session test in `output.xml` has status FAIL

#### Scenario: Skip-on-failure settings do not apply
- **WHEN** the active profile sets `skip-on-failure` and a keyword fails in the session
- **THEN** the session test has status FAIL, not SKIP

### Requirement: Exit code of non-interactive sessions reflects the session status

A session SHALL be non-interactive when standard input is not a terminal, or when script files are passed without `--inspect`. A non-interactive session SHALL exit with code 1 when the session test failed and with code 0 when it passed. Interactive sessions SHALL exit with code 0 regardless of failures. Overrides and explicit exit codes defined by the following requirements take precedence.

#### Scenario: Piped input with a failure
- **WHEN** `Fail    boom` followed by `Log    after` is piped into `robotcode repl`
- **THEN** the process exits with code 1

#### Scenario: Piped input without failures
- **WHEN** only successful keywords are piped into `robotcode repl`
- **THEN** the process exits with code 0

#### Scenario: Script file on a terminal
- **WHEN** `robotcode repl script.robotrepl` is started from a terminal without `--inspect` and a keyword in the script fails
- **THEN** the process exits with code 1

#### Scenario: Interactive session with failures
- **WHEN** a keyword fails in an interactive terminal session and the user ends the session
- **THEN** the process exits with code 0

#### Scenario: Script file with --inspect on a terminal
- **WHEN** `robotcode repl --inspect script.robotrepl` is started from a terminal, a keyword in the script fails and the user ends the session
- **THEN** the process exits with code 0

### Requirement: Status-based exit code can be overridden

`robotcode repl` SHALL accept `--statusrc` and `--nostatusrc`. With `--statusrc`, the session SHALL exit with code 1 when the session test failed, also in interactive sessions. With `--nostatusrc`, the session SHALL exit with code 0 regardless of failures, also in non-interactive sessions. When the status-based exit code is switched off by configuration — `no-status-rc = true` in `robot.toml` or `--nostatusrc` in `ROBOT_OPTIONS` — the session SHALL exit with code 0 regardless of failures. A configuration that switches it on (`no-status-rc = false`, `--statusrc` in `ROBOT_OPTIONS`) SHALL NOT change the rules for interactive and non-interactive sessions. The options on the `robotcode repl` command line SHALL take precedence over the configuration. The session test status SHALL NOT be affected by any of these settings.

#### Scenario: Force the exit code in an interactive session
- **WHEN** `robotcode repl --statusrc` runs in a terminal and a keyword fails before the user ends the session
- **THEN** the process exits with code 1

#### Scenario: Suppress the exit code in a pipe
- **WHEN** a failing keyword is piped into `robotcode repl --nostatusrc`
- **THEN** the process exits with code 0
- **AND** the session test still has status FAIL when output files are written

#### Scenario: Suppress the exit code via robot.toml
- **WHEN** the active profile sets `no-status-rc = true` and a failing keyword is piped into `robotcode repl`
- **THEN** the process exits with code 0

#### Scenario: Profile with no-status-rc = false in an interactive session
- **WHEN** the active profile sets `no-status-rc = false` and a keyword fails in an interactive terminal session before the user ends it
- **THEN** the process exits with code 0

#### Scenario: Command line overrides the configuration
- **WHEN** the active profile sets `no-status-rc = true` and a failing keyword is piped into `robotcode repl --statusrc`
- **THEN** the process exits with code 1

### Requirement: Explicit exit codes

`.exit` and `.quit` SHALL accept an optional integer exit code. When a code is given, the session SHALL end and the process SHALL exit with that code in every mode, taking precedence over the status-based exit code and its overrides. Without a code, the status-based rules SHALL apply. A code that is not an integer SHALL print a usage message and SHALL NOT end the session.

#### Scenario: Exit with a code
- **WHEN** `.exit 3` is entered
- **THEN** the process exits with code 3

#### Scenario: Explicit code overrides failures
- **WHEN** `Fail    boom` is piped into `robotcode repl`, followed by `.exit 0`
- **THEN** the process exits with code 0

#### Scenario: Exit without a code after a piped failure
- **WHEN** `Fail    boom` is piped into `robotcode repl`, followed by `.exit`
- **THEN** the process exits with code 1

#### Scenario: Invalid exit code
- **WHEN** `.exit abc` is entered
- **THEN** a usage message is printed
- **AND** the session continues

### Requirement: Other exit codes are unchanged

Errors that occur before or outside the session, such as invalid options or unreadable data, SHALL keep their existing exit codes.

#### Scenario: Invalid option in the profile
- **WHEN** the active profile contains an option that the installed Robot Framework version does not accept
- **THEN** the process exits with code 252 as before
