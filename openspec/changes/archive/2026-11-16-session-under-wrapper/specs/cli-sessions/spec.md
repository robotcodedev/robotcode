# Spec Delta: cli-sessions

## ADDED Requirements

### Requirement: Aborting a start

`robotcode session start` SHALL end the session when it is aborted before the session can take commands: by Ctrl-C, by SIGTERM or SIGHUP, or on Windows in any way.

#### Scenario: A start that is aborted
- **WHEN** `robotcode session start repl` gets Ctrl-C, SIGTERM or SIGHUP, or is killed on Windows, before the session can take commands
- **THEN** the process of the session ends, together with the processes it has started
- **AND** after Ctrl-C, SIGTERM or SIGHUP no file of the session stays behind

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
