# Spec Delta: cli-sessions

## MODIFIED Requirements

### Requirement: Starting a session

`robotcode session start repl` and `robotcode session start debug` SHALL start a REPL or a debug run in the background, with the options of `robotcode repl` or `robotcode robot-debug`, wait until it is ready and print the session's ID and its output so far. A debug session is ready at its first stop or at the end of its run. `start` SHALL return only once the session can take commands, and SHALL end a session that isn't ready within 60 seconds, or within `--timeout` when that is longer. A `start` that is aborted before the session can take commands, by Ctrl-C, by SIGTERM or SIGHUP, or on Windows in any way, SHALL end the session.

#### Scenario: Start a REPL
- **WHEN** `robotcode session start repl` runs
- **THEN** it prints the ID of a new session, such as `repl-3f9a2c1e`
- **AND** it returns while the session keeps running

#### Scenario: Start a debug run
- **WHEN** `robotcode session start debug --break tests/orders.robot:19 -bl "Tests.Orders"` runs
- **THEN** it prints the run's output up to the stop at line 19 and the session's ID

#### Scenario: A debug run that ends before a stop
- **WHEN** `robotcode session start debug -bl "Tests.Orders"` runs a suite in which nothing stops the run
- **THEN** it prints the session's ID, the run's output and that the run has ended with its exit code, and exits with 0
- **AND** the session stays open

#### Scenario: A session that is slow to start
- **WHEN** the process of a session takes longer to start than the `--timeout` of `session start`
- **THEN** `start` returns once the session can take commands, with the ID and exit code 124
- **AND** `robotcode session wait` with that ID reaches the session

#### Scenario: A session that doesn't get ready
- **WHEN** a session isn't ready within 60 seconds, or within `--timeout` when that is longer
- **THEN** `start` ends its process, prints what it wrote and exits with code 252

#### Scenario: A start that is aborted
- **WHEN** `robotcode session start repl` gets Ctrl-C, SIGTERM or SIGHUP, or is killed on Windows, before the session can take commands
- **THEN** the process of the session ends, together with the processes it has started
- **AND** after Ctrl-C, SIGTERM or SIGHUP no file of the session stays behind

## ADDED Requirements

### Requirement: Sessions under a wrapper

`robotcode session start` SHALL work when the selected profiles set a `wrapper`, also one that starts its command without passing on inherited handles other than the standard ones, as Python's `subprocess` does by default. What the wrapper and the processes it starts write while the session runs SHALL come with the answers of the session, as the output of the session does. When `start` ends a session that isn't ready, it SHALL also end the processes that the wrapper has started.

#### Scenario: A wrapper that starts its command with subprocess
- **WHEN** `robot.toml` sets `wrapper = ["python", "w.py", "--"]`, `w.py` runs its command with `subprocess.run`, and `robotcode session start repl` runs
- **THEN** it prints the ID of a new session
- **AND** `robotcode session send <id> "Log To Console    hello"` prints `hello`

#### Scenario: A debug session under a wrapper
- **WHEN** `robot.toml` sets that `wrapper`, and `robotcode session start debug --break debug.robot:4 debug.robot` runs
- **THEN** it prints the run's output up to the stop at line 4 and the session's ID

#### Scenario: A wrapper on Windows that passes its handles on
- **WHEN** `robot.toml` sets `wrapper = ["cmd", "/c"]` on Windows, and `robotcode session start repl` runs
- **THEN** it prints the ID of a new session

#### Scenario: Output of the wrapper
- **WHEN** the wrapper writes a line while the session waits at its prompt, and `robotcode session send` runs after that
- **THEN** the answer of the `send` starts with that line

#### Scenario: Much output of the wrapper before the session is ready
- **WHEN** the wrapper writes 100 KB before it starts its command, on Linux or Windows, and `robotcode session start repl` runs
- **THEN** it prints the ID of a new session and those 100 KB

#### Scenario: A start under a wrapper that fails
- **WHEN** the wrapper starts a process that keeps running, and the session isn't ready in time or the wrapper exits with 3 before the session is ready
- **THEN** `start` ends that process too, prints that the session wasn't ready or that it ended with exit code 3, and exits with 252 or with 3
