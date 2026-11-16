# Spec Delta: cli-sessions

## ADDED Requirements

### Requirement: Sessions under a wrapper

`robotcode session start` and `robotcode session restart` SHALL work when the selected profiles set a `wrapper`, also one that starts its command without passing on inherited handles other than the standard ones, as Python's `subprocess` does by default. What the wrapper and the processes it starts write while the session runs SHALL come with the answers of the session, as the output of the session does.

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

#### Scenario: A restart under a wrapper
- **WHEN** `robotcode session restart <id>` runs for a REPL session that started under that `wrapper`
- **THEN** the session starts again in a new process
- **AND** the next `robotcode session send <id> "Log To Console    hello"` prints `hello`
