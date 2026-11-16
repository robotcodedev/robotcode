# Spec Delta: agent-skill-guidance

## MODIFIED Requirements

### Requirement: Driving a session

A session SHALL be driven one input at a time, reading each answer before choosing the next. The skill SHALL give the meaning of the exit codes of `session send` (0, 1, 124, 252), name `status`, `result`, `wait` and `interrupt`, and tell the agent to end the session with `session stop`. It SHALL NOT name a fixed list of inputs through a pipe as a fallback.

#### Scenario: Trying keywords
- **WHEN** an agent tries keywords in a session
- **THEN** it sends one input per `session send` and chooses the next input from the answer
- **AND** it ends the session with `session stop` when the task is done

#### Scenario: A block
- **WHEN** an agent runs a `FOR`, `IF` or `TRY` block in a session
- **THEN** it sends the whole block with its `END` in one `session send`

#### Scenario: Debugging a test
- **WHEN** an agent without a tool that writes to a running command is asked to step through a test
- **THEN** it starts a session with `robotcode session start debug`, scoped to that test, and sends one debugger command per `session send`

#### Scenario: Several steps at once
- **WHEN** an agent steps through a test in a session
- **THEN** it reads the answer of each step before the next, with no two steps in one shell command and no shell loop over inputs

#### Scenario: A session that was started earlier
- **WHEN** an agent is asked to take over a debug session that is open already and waits at a stop
- **THEN** it finds it with `session list` instead of starting a new one, looks around at the stop in that session, and lets the run go on there
