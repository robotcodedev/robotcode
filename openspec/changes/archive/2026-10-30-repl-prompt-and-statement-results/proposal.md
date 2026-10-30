# Proposal

## Why

An AI agent that drives `robotcode repl` through a pipe or a FIFO can't tell when a statement has ended. Without a terminal, the REPL shows no prompt, and a statement without log output, such as `Evaluate    1 + 1`, leaves nothing at all, because the REPL keeps a statement's result only in `${_}`. The recordings of the AI agents guide showed both: the agent waited blindly with `sleep`, and it needed `Log    ${_}` to see the status of an order. The debugger already shows its prompt `(rdb) ` and the result of a keyword as `=> <value>` without a terminal, and its guide says the result is shown "exactly like at the shell prompt", which the shell prompt doesn't do.

## What Changes

- **The prompt without a terminal in agent sessions:** In a session that RobotCode recognizes as an AI agent's, `robotcode repl` shows `>>> ` and `... ` also when its input is not a terminal. A new option `--show-prompt` / `--no-show-prompt` shows or hides the prompt for input that is not a terminal, in any session. With a terminal, the prompt shows as before.
- **The result of a statement:** After each statement read from its input, the terminal REPL prints the statement's result as `=> <value>`, as the debugger does at `(rdb)`, with and without a terminal. A statement that fails shows its failure as before, and an assignment shows the message that sets the variable; neither shows a result.
- **No `=> None`, no result for an assignment:** A result of `None`, such as that of `Log`, and the value of an assignment are not shown, neither in the REPL nor at the debugger prompt, which shows both today.
- **Unchanged:** `robotcode repl-server` and the REPL of the VS Code notebook, which run on an interpreter of their own; the statements of script files passed as arguments, which run like the body of a test; `${_}`; the exit codes of a session.
- **Documentation:** The guides on the REPL and on `robot-debug` describe the prompt without a terminal and the results, and the CLI reference is generated again for the new option.

## Capabilities

### New Capabilities

- `repl-prompt-and-results`: when the terminal REPL shows its prompt, also without a terminal, and how the REPL and the debugger prompt show the result of a statement.

### Modified Capabilities

None.

## Impact

- `packages/repl/src/robotcode/repl/cli.py`: the option and the decision whether the prompt shows.
- `packages/repl/src/robotcode/repl/console_interpreter.py`: the prompt, the result after each statement, no `=> None` at the debugger prompt; `base_interpreter.py`: a step after each statement that only the console interpreter fills.
- Tests in `tests/robotcode/repl/`.
- Documentation: `docs/src/content/docs/guides/cli/repl.md`, `docs/src/content/docs/guides/cli/robot-debug.md`, and `reference/cli.md`, generated with `hatch run create-cmd-line-docs`.
- Follow-ups outside this change: the RobotCode skill in robotframework-agent-plugins, which then tells an agent to wait for the prompt, and the table of the AI-agent detection on `guides/ai-agents/how-the-skill-works.md`, which belongs to the change `docs-ai-agents-guide` that is not committed yet.
