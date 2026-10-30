# Spec Delta

## Purpose

REPL and debug sessions that run in the background and that separate `robotcode session` commands start, drive line by line, wait for, interrupt, list and end, so that an AI agent without a tool for running processes can work turn by turn on Linux, macOS and Windows.

## ADDED Requirements

### Requirement: Starting a session

`robotcode session start repl` and `robotcode session start debug` SHALL start a REPL or a debug run in the background, with the options of `robotcode repl` or `robotcode robot-debug`, wait until it is ready and print the session's ID and its output so far. A debug session is ready at its first stop or at the end of its run.

#### Scenario: Start a REPL
- **WHEN** `robotcode session start repl` runs
- **THEN** it prints the ID of a new session, such as `repl-3f9a2c1e`
- **AND** it returns while the session keeps running

#### Scenario: Start a debug run
- **WHEN** `robotcode session start debug --break tests/orders.robot:19 -bl "Tests.Orders"` runs
- **THEN** it prints the run's output up to the stop at line 19 and the session's ID

### Requirement: Session IDs

A session's ID SHALL be its kind, `repl` or `debug`, a hyphen and eight random hexadecimal characters, such as `repl-3f9a2c1e`, and it SHALL differ from the ID of every open session. The `robotcode session` commands SHALL address a session by its ID; a session SHALL have no other name.

#### Scenario: Form of the ID
- **WHEN** `robotcode session start debug -bl "Tests.Orders"` runs
- **THEN** the ID it prints starts with `debug-`, followed by eight hexadecimal characters

#### Scenario: A new session gets a new ID
- **WHEN** the session `repl-3f9a2c1e` has ended and `robotcode session start repl` runs again
- **THEN** the new session gets another ID
- **AND** `robotcode session send repl-3f9a2c1e "Log    hi"` says that no such session is open

### Requirement: Sending a line

`robotcode session send <id> "<line>"` SHALL give the line to the session's prompt, print the output it causes until the session waits at its next prompt, and exit with 0 when the statement passed and 1 when it failed. The line MAY be a block of several lines, and dot commands such as `.vars` SHALL work as at the prompt. The session SHALL keep its state, such as variables and imports, from one `send` to the next.

#### Scenario: Statement
- **WHEN** `robotcode session send repl-3f9a2c1e "Evaluate    1 + 1"` runs
- **THEN** `=> 2` is printed and the command exits with 0

#### Scenario: Failing statement
- **WHEN** `robotcode session send repl-3f9a2c1e "Should Be Equal    1    2"` runs
- **THEN** the failure is printed and the command exits with 1

#### Scenario: State between calls
- **WHEN** one `send` runs `${order}=    Create Order    coffee` and a later `send` runs `Log    ${order}`
- **THEN** the second shows the order id the first one set

#### Scenario: Debugger command
- **WHEN** `send` gives `.vars --user` to a debug session paused at a stop
- **THEN** the variables are printed and the run stays paused

### Requirement: Waiting with a timeout

`robotcode session send` SHALL wait at most the time given with `--timeout`, 60 seconds without it. When the statement runs longer, `send` SHALL print the output so far and exit with code 124 while the statement goes on, and `robotcode session wait <id>` SHALL print the rest once the session waits at its prompt again, with the exit code `send` would have had.

#### Scenario: Statement longer than the timeout
- **WHEN** `robotcode session send repl-3f9a2c1e --timeout 2 "Sleep    5s"` runs
- **THEN** it returns after about 2 seconds with exit code 124
- **AND** `robotcode session wait repl-3f9a2c1e` returns when `Sleep` has ended, with exit code 0

### Requirement: Interrupting a session

`robotcode session interrupt <id>` SHALL act on the session as Ctrl-C does at the terminal of `robotcode repl` or `robotcode robot-debug`.

#### Scenario: Statement in a REPL session
- **WHEN** `Sleep    60s` runs in a REPL session with the debugger detached and `robotcode session interrupt repl-3f9a2c1e` runs
- **THEN** `Sleep` fails with `Execution interrupted`, and the session waits at its prompt again

#### Scenario: Running debug session
- **WHEN** a debug session runs after `.continue` and `robotcode session interrupt debug-7b2d9e04` runs
- **THEN** the run pauses at the next keyword, and `robotcode session wait debug-7b2d9e04` shows the stop

### Requirement: Ending a session

A session SHALL end with `robotcode session stop <id>`, with `.exit` in a REPL session, at the end of a debug run, and when it has waited at its prompt for 15 minutes without a request; `--idle-timeout` at the start SHALL change that time. A statement that runs SHALL NOT count as waiting. Ending a debug session before its run ends SHALL stop the run as `.abort` does.

#### Scenario: Stop
- **WHEN** `robotcode session stop repl-3f9a2c1e` runs
- **THEN** the session's process ends, and `robotcode session list` no longer shows it

#### Scenario: Idle session
- **WHEN** a session started with `--idle-timeout 1` waits at its prompt for a minute without a request
- **THEN** the session ends

#### Scenario: End of a debug run
- **WHEN** `send` gives `.continue` to a debug session and the run reaches its end
- **THEN** `send` prints the rest of the run's output, exits with the run's exit code, and the session ends

### Requirement: Listing sessions

`robotcode session list` SHALL show each open session of the user with its ID, its project folder, whether it waits or runs, and the time left until it ends for being idle.

#### Scenario: Two sessions
- **WHEN** a REPL session and a debug session are open
- **THEN** `robotcode session list` shows both, each with its ID, project folder, state and the time left

### Requirement: Structured output

With the global option `--format json`, `robotcode session send` and `robotcode session wait` SHALL print one object with the output, the status (`passed`, `failed`, `running` or `ended`) and the prompt the session waits at, if any.

#### Scenario: Result as JSON
- **WHEN** `robotcode --format json session send repl-3f9a2c1e "Evaluate    1 + 1"` runs
- **THEN** it prints an object whose output contains `=> 2`, whose status is `passed` and whose prompt is `>>>`

### Requirement: Unknown session

A `robotcode session` command for an ID with no open session SHALL say that no such session is open and exit with code 252.

#### Scenario: Send to an ended session
- **WHEN** `robotcode session send repl-0d1e2f3a "Log    hello"` runs and no session `repl-0d1e2f3a` is open
- **THEN** it says that no session `repl-0d1e2f3a` is open and exits with code 252

### Requirement: Platforms and access

Sessions SHALL work on Linux, macOS and Windows. A session SHALL accept requests only from processes of the user who started it.

#### Scenario: Windows
- **WHEN** a REPL session is started, driven with `send` and stopped in PowerShell on Windows
- **THEN** it behaves as on Linux

#### Scenario: Another user
- **WHEN** a process of another user connects to a session's channel
- **THEN** the session refuses the connection
