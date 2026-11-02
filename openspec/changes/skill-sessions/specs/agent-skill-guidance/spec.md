# Spec Delta

## Purpose

What the RobotCode agent skill tells an agent about driving the REPL and the debugger, about sessions in a sandbox, about suite names and about searching a finished run, and how the evals of the plugin repository check it.

## ADDED Requirements

### Requirement: Driving the REPL and the debugger

The skill SHALL tell an agent to run the REPL and the debugger as a `robotcode session` and to drive it one input at a time, reading each answer before choosing the next input. It SHALL give the meaning of the exit codes of `session send` (0, 1, 124, 252), name `status`, `result`, `wait`, `interrupt` and `restart`, and tell the agent to end the session with `session stop`. It SHALL NOT name a fixed list of inputs through a pipe as a fallback.

#### Scenario: Trying keywords
- **WHEN** an agent is asked to try keywords in a REPL
- **THEN** it starts a session with `robotcode session start repl`, sends one input per `session send` and chooses the next input from the answer
- **AND** it ends the session with `session stop` when the task is done

#### Scenario: A block
- **WHEN** an agent runs a `FOR`, `IF` or `TRY` block in a session
- **THEN** it sends the whole block with its `END` in one `session send`

#### Scenario: Debugging a test
- **WHEN** an agent is asked to step through a test
- **THEN** it starts a session with `robotcode session start debug`, scoped to that test, and sends one debugger command per `session send`

#### Scenario: A session that was started earlier
- **WHEN** an agent is asked about a debug session that is open already, whose run has ended
- **THEN** it finds it with `session list`, gets the exit code of the run with `session result` and runs it again with `session restart`

#### Scenario: A bare REPL or debugger
- **WHEN** the skill describes `robotcode repl` and `robotcode robot-debug`
- **THEN** it warns against starting one of them without input and waiting for it to exit

### Requirement: Sessions in a sandbox

The skill SHALL tell an agent what it means when a `session` command fails in a sandbox, for all `session` commands: each command has a sandbox of its own, and a session can't outlive it or be reached from it. It SHALL say that an agent with a tool that writes to a running command drives `robotcode repl` or `robotcode robot-debug` in it, and that sessions work when the whole agent runs in one sandbox. It SHALL NOT tell an agent to leave the sandbox or to change its settings.

#### Scenario: A tool that writes to a running command
- **WHEN** `session start` fails in the sandbox of an agent that has such a tool
- **THEN** the agent drives `robotcode repl` or `robotcode robot-debug` in it, one input at a time, waiting for `>>> ` or `(rdb) `

#### Scenario: No such tool
- **WHEN** `session start` fails in the sandbox of an agent that has no such tool
- **THEN** the skill leaves the way to the agent and names no setting that opens the sandbox

#### Scenario: A session outside the sandbox
- **WHEN** `session result` or `session stop` fails from a sandbox with `doesn't answer`
- **THEN** the agent says that it can't reach that session from its sandbox

#### Scenario: One sandbox around the whole agent
- **WHEN** the whole agent runs in one sandbox, such as a container or a virtual machine
- **THEN** the agent uses sessions as usual

### Requirement: Names of suites

The skill SHALL say that the top suite of a run is named after the `paths` of the project, not after its folder, and that the names for `-s` and `-bl` come from `robotcode discover suites`.

#### Scenario: One suite of a project
- **WHEN** an agent is asked to run one suite in a project with `paths = ["tests"]`
- **THEN** it selects the suite by a name that starts with `Tests`, not with the name of the project's folder

### Requirement: Searching a finished run

The skill SHALL name `robotcode results log --search` as the way to find out whether a value or an argument occurred in a finished run.

#### Scenario: Whether a value was used
- **WHEN** an agent is asked whether a run used a given value, such as a browser passed to a keyword
- **THEN** it uses `robotcode results log --search` and doesn't search `output.xml` with `grep`

### Requirement: Length of the references on the REPL and the debugger

`references/repl.md` and `references/debugging.md` SHALL each stay under 20 000 bytes, so that an agent tool that doesn't read larger files at once, as Copilot CLI's `view` doesn't, gets the whole reference.

#### Scenario: Copilot reads a reference
- **WHEN** Copilot CLI reads `references/repl.md` or `references/debugging.md`
- **THEN** it gets the whole file in one read

### Requirement: Evals of the guidance

The evals of the plugin repository SHALL expect `robotcode session` commands in the cases on the REPL and the debugger, and SHALL have a case each for the names of suites and for searching a finished run. The harness SHALL be able to run the cases with a skill from a given folder.

#### Scenario: A debugging case
- **WHEN** the harness runs a case on the debugger and the agent uses `robotcode session start debug`, scoped to the test
- **THEN** the checks of the case pass

#### Scenario: A skill that isn't released
- **WHEN** the harness runs with the plugin folder of a working copy
- **THEN** the agent in each case has the skill of that folder
