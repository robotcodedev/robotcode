# Spec Delta

## Purpose

How the terminal REPL `robotcode repl` shows its prompt with and without a terminal, and how it and the debugger prompt show the result of a statement, so that people and AI agents see when a statement has ended and what it returned.

## ADDED Requirements

### Requirement: Prompt without a terminal in an agent session

When its input is not a terminal and RobotCode recognizes the session as an AI agent's, `robotcode repl` SHALL show the prompt `>>> ` before each new input and `... ` while a block is unfinished, as it does on a terminal. Showing the prompt SHALL NOT make the session interactive: its exit code SHALL stay that of a session without a terminal.

#### Scenario: Input from a pipe in an agent session
- **WHEN** an AI agent's session pipes `Log    hello` into `robotcode repl`
- **THEN** the output shows `>>> ` before the message of `Log` and `>>> ` again after it

#### Scenario: Without an agent
- **WHEN** a session that RobotCode doesn't recognize as an AI agent's pipes a statement into `robotcode repl`
- **THEN** no prompt is shown, as before

#### Scenario: Exit code with the prompt
- **WHEN** an AI agent's session pipes a statement that fails into `robotcode repl`
- **THEN** the prompt is shown
- **AND** the REPL exits with code 1, as a session without a terminal does

### Requirement: Option for the prompt

The option `--prompt` of `robotcode repl` SHALL show the prompt, and `--no-prompt` SHALL hide it, when the input is not a terminal, whether or not the session is an AI agent's. When the input is a terminal, the prompt SHALL show whatever the option says.

#### Scenario: Prompt for piped input
- **WHEN** a person pipes statements into `robotcode repl --prompt`
- **THEN** `>>> ` is shown before each statement

#### Scenario: No prompt in an agent session
- **WHEN** an AI agent's session pipes statements into `robotcode repl --no-prompt`
- **THEN** no prompt is shown

#### Scenario: On a terminal
- **WHEN** `robotcode repl --no-prompt` reads from a terminal
- **THEN** the prompt `>>> ` is shown

### Requirement: Result of a statement

After each statement it reads from its input, `robotcode repl` SHALL print the statement's result as `=> <value>` on a line of its own, with and without a terminal, as the debugger does at its prompt. A statement that fails SHALL show its failure and no result. Statements of a script file passed as an argument SHALL show no result, and `robotcode repl-server` SHALL answer as before.

#### Scenario: Result of a keyword
- **WHEN** `Evaluate    1 + 1` is entered
- **THEN** `=> 2` is printed

#### Scenario: Assignment
- **WHEN** `${x}=    Set Variable    42` is entered
- **THEN** the message that sets `${x}` is printed, followed by `=> 42`

#### Scenario: Failing statement
- **WHEN** `Should Be Equal    1    2` is entered
- **THEN** its failure is printed
- **AND** no line starting with `=>` follows

#### Scenario: Script file
- **WHEN** a script file passed to `robotcode repl` runs `Evaluate    1 + 1`
- **THEN** no line starting with `=>` is printed for it

### Requirement: No result for None

Neither `robotcode repl` nor the debugger prompt `(rdb)` SHALL print a result line for a statement whose result is `None`.

#### Scenario: Log in the REPL
- **WHEN** `Log    hello` is entered at the `>>>` prompt
- **THEN** the message of `Log` is printed
- **AND** no line starting with `=>` follows

#### Scenario: Log at the debugger prompt
- **WHEN** `Log    hello` is entered at the `(rdb)` prompt
- **THEN** no line `=> None` is printed

#### Scenario: Other results at the debugger prompt
- **WHEN** `Evaluate    1 + 1` is entered at the `(rdb)` prompt
- **THEN** `=> 2` is printed
