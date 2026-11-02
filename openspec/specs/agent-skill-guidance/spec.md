# agent-skill-guidance Specification

## Purpose

What the RobotCode agent skill tells an agent about driving the REPL and the debugger, about sessions in a sandbox, about suite names and about searching a finished run, what it leaves out, where a rule stands, and how the evals of the plugin repository check it.

## Requirements

### Requirement: How to run the REPL and the debugger

`references/repl.md` and `references/debugging.md` SHALL say right after their introduction, in the same order, how to run the program. They SHALL ask whether the agent's shell tool can keep a command running and write to its input. With such a tool, the agent SHALL work at the prompt, one input at a time; a background process fed through a file or a FIFO doesn't count. Without one, it SHALL run a `robotcode session`.

#### Scenario: An agent with such a tool
- **WHEN** an agent whose shell tool writes to a running command is asked to try keywords in a REPL
- **THEN** it starts `robotcode repl` in that tool, writes one input at a time and reads each answer up to the prompt `>>> `

#### Scenario: An agent without such a tool
- **WHEN** an agent whose shell tool can't write to a running command is asked to try keywords in a REPL
- **THEN** it starts a session with `robotcode session start repl`

#### Scenario: The same order in both files
- **WHEN** an agent opens `references/repl.md` or `references/debugging.md`
- **THEN** the section on how to run the program comes right after the introduction, and no section is set apart as being for agents

#### Scenario: A bare REPL or debugger
- **WHEN** the skill describes `robotcode repl` and `robotcode robot-debug`
- **THEN** it warns against starting one of them without input and waiting for it to exit

### Requirement: The ways to start in the overview

The mode list of `SKILL.md` SHALL name both ways to start the REPL and the debugger.

#### Scenario: The overview
- **WHEN** an agent reads the mode list of `SKILL.md`
- **THEN** the REPL and the debugger each name their own command and `robotcode session start`, with the condition for the session

### Requirement: Driving a session

A session SHALL be driven one input at a time, reading each answer before choosing the next. The skill SHALL give the meaning of the exit codes of `session send` (0, 1, 124, 252), name `status`, `result`, `wait`, `interrupt` and `restart`, and tell the agent to end the session with `session stop`. It SHALL NOT name a fixed list of inputs through a pipe as a fallback.

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
- **WHEN** an agent is asked about a debug session that is open already, whose run has ended
- **THEN** it finds it with `session list`, gets the exit code of the run with `session result` and runs it again with `session restart`

### Requirement: Sessions in a sandbox

The skill SHALL tell an agent what it means when a `session` command fails in a sandbox, for all `session` commands: each command has a sandbox of its own, and a session can't outlive it or be reached from it. It SHALL say that sessions work when the whole agent runs in one sandbox. It SHALL NOT tell an agent to leave the sandbox or to change its settings.

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
- **THEN** the agent can use sessions as usual

### Requirement: What an agent doesn't need

The skill SHALL leave out what works without the agent doing anything, what the agent sees in a message anyway, what it can't do through its tools, and what only a person needs.

#### Scenario: What works automatically
- **WHEN** the skill describes a command that adapts to an agent, such as the input of the REPL or paging and colors
- **THEN** it doesn't explain the detection; that stays in the guide for people

#### Scenario: A message the agent gets
- **WHEN** a command refuses something with a message that says what to do, such as `.exit` at a debugger stop
- **THEN** the skill doesn't repeat that message

### Requirement: One place for a rule

A rule of the skill SHALL stand once, in `SKILL.md` in the section on its topic, and other places SHALL link to it; a reference SHALL only add what its own topic needs. `SKILL.md` SHALL have a section on selecting one test or suite, which the sections on running, debugging and discovery link to, and no section that repeats the rules above it.

#### Scenario: Selecting one test
- **WHEN** an agent is asked to run or debug one test
- **THEN** it selects the test by longname, not by its `.robot` file

#### Scenario: A section on another topic
- **WHEN** the section on running or debugging comes to selecting a test
- **THEN** it links to the section on selecting instead of explaining the rule again

#### Scenario: An example
- **WHEN** an example in the skill starts the debugger for one test
- **THEN** it selects the test by longname, and the text says or links to how to drive the debugger

### Requirement: Asking before installing

`SKILL.md` SHALL send an agent to `references/install.md` for a missing `robotcode` or a message `No such command 'X'`, which means a missing extra. The reference SHALL say to ask the user before installing anything, and what to ask.

#### Scenario: A missing extra
- **WHEN** a command fails with `No such command 'X'`
- **THEN** the agent installs nothing without asking and names what is missing

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

The evals of the plugin repository SHALL accept a session or the prompt in a terminal as the way to drive the REPL and the debugger, and check the way as well as the answer. They SHALL have a case each for the rules of this skill that an agent can get wrong. The harness SHALL run the cases with a skill from a given folder and with several agents.

#### Scenario: A debugging case
- **WHEN** the harness runs a case on the debugger and the agent uses `robotcode session start debug`, scoped to the test, or the prompt of `robotcode robot-debug` with a tool that writes to a running command
- **THEN** the checks of the case pass

#### Scenario: A right answer on a wrong way
- **WHEN** an agent gets the right answer through a fixed list of inputs or a throwaway test file
- **THEN** the case fails

#### Scenario: A missing extra in a case
- **WHEN** the harness runs the case in which a command fails with `No such command` and the agent installs something
- **THEN** the case fails

#### Scenario: What a run can see
- **WHEN** the harness runs an agent in its sandbox around the whole agent
- **THEN** the agent sees neither the other runs nor the user's home folder, apart from its own configuration and what it and `robotcode` run from

#### Scenario: A small model
- **WHEN** the harness runs a model with `haiku` in its name
- **THEN** the prompt names the skill, as the guide tells the users of such a model

#### Scenario: A skill that isn't released
- **WHEN** the harness runs with the plugin folder of a working copy
- **THEN** the agent in each case has the skill of that folder

#### Scenario: Several agents
- **WHEN** the harness runs with several agents
- **THEN** it runs each case with each of them and shows how many runs passed per case and agent
