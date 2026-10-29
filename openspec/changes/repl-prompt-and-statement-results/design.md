# Design

## Context

- **The prompt:** `ConsoleInterpreter.get_input()` reads each line with `self._read(prompt, …)`. The prompt is `>>> ` or `... ` only when `sys.stdin.isatty()`, otherwise empty (`console_interpreter.py:940-942`). The plain backend reads with `input(prompt)`; the prompt-toolkit backend, which runs only on a terminal, draws the prompt it gets.
- **The backend choice:** `_resolve_backend()` in `cli.py` picks the plain backend when the input is not a terminal or when `is_running_in_ai_agent()` recognizes an AI agent (overrides `ROBOTCODE_FORCE_AI_AGENT=1`, `ROBOTCODE_NO_AI_AGENT=1`). The options of `SHELL_OPTIONS` belong to `repl` only; `REPL_BASE_OPTIONS` (`--backend`, `--plain`, `--no-history`) are shared with `robot-debug`, and each of them has an environment variable.
- **The debugger prompt:** `(rdb) ` is passed to `_read()` always (`:672`). `_evaluate_at_stop()` runs the keywords of a line and then prints `=> {_repr.repr(self.last_result)}` (`:871`), also for `None`. `_repr` cuts long values (200 characters, 20 items).
- **Statements:** `BaseInterpreter.run_input()` runs each statement that `get_input()` yields and calls `set_last_result(self.run_keyword(kw))`. A statement that fails raises out of `run_input()`, and `run()` records the failure. `ConsoleInterpreter.set_last_result()` mirrors the result into `${_}` (`:877`). `get_input()` yields the bodies of the script files first, then reads the input.
- **The REPL server:** `robotcode repl-server` runs statements with `Interpreter(BaseInterpreter)` in `repl_server/interpreter.py` and returns their results through its protocol.
- **Interactive or not:** A session whose input is not a terminal is non-interactive and exits with code 1 when a statement failed (`repl-session-status`).

## Goals / Non-Goals

**Goals:**
- An AI agent that drives the REPL without a terminal sees where each statement ends.
- The REPL and the debugger prompt show results by the same rule.

**Non-Goals:**
- The prompt `(rdb) `, the prompt-toolkit backend, interactivity and exit codes.
- The output of `robotcode repl-server` and of the VS Code notebook.
- The RobotCode skill, which is a change of its own in robotframework-agent-plugins.

## Decisions

### D1: The CLI decides whether the prompt shows

`repl` computes `show_prompt` once and passes it to the interpreter, which uses it in `get_input()` in place of `sys.stdin.isatty()`, for `>>> ` and `... ` alike:

| Input | `--prompt` / `--no-prompt` | Prompt |
| --- | --- | --- |
| a terminal | any | shown |
| not a terminal | `--prompt` | shown |
| not a terminal | `--no-prompt` | hidden |
| not a terminal | not given | shown when `is_running_in_ai_agent()` |

- The option is a flag pair with the default "not given", in `SHELL_OPTIONS`, with the environment variable `ROBOTCODE_REPL_PROMPT` like its neighbors `ROBOTCODE_REPL_PLAIN`, `ROBOTCODE_REPL_BACKEND` and `ROBOTCODE_REPL_NO_HISTORY`. `robot-debug` has no `>>>` prompt and doesn't get it.
- Rejected: calling `is_running_in_ai_agent()` inside the interpreter. The CLI already makes the backend choice from it, and a value passed in keeps the interpreter testable without patching the environment.
- Without a terminal, `input(prompt)` writes the prompt without a newline, as the debugger's `(rdb) ` does today. The next output starts on the same line; an agent sees that a statement has ended when the output ends with `>>> `.

### D2: The result is shown after each statement of the input

`BaseInterpreter.run_input()` calls a step after `set_last_result()` that does nothing in the base class, so the REPL server stays as it is. `ConsoleInterpreter` fills it: it prints `=> <value>` with the debugger's `_repr`, unless the value is `None` or the statement came from a script file.

- `get_input()` marks the statements it yields from a script file. A script file runs like the body of a test, so its output stays that of a run.
- A statement that fails never reaches the step, since it raises out of `run_input()`.
- An assignment shows its value like any statement (`=> 42` after the message that sets `${x}`), as the debugger does today, so both prompts follow one rule.
- Rejected: printing in `ConsoleInterpreter.set_last_result()`. It also runs for each keyword at the debugger prompt, which prints the result of a line itself, so the result would show twice.

### D3: No `=> None` anywhere

The REPL and `_evaluate_at_stop()` share one helper that prints `=> <value>` and leaves out `None`. At the debugger prompt, `Log    hello` then prints only its message; other results show as before.

### D4: Documentation

- `guides/cli/repl.md`: "How the prompt works" says when the prompt shows without a terminal (agent sessions, `--prompt` / `--no-prompt`) and that each statement shows its result, without `None`; the section on AI agents and automation mentions the prompt.
- `guides/cli/robot-debug.md`: the sentence on results at the `(rdb)` prompt says that `None` shows nothing; "exactly like at the shell prompt" is then true.
- `reference/cli.md` is generated again with `hatch run create-cmd-line-docs`.
- The table of the AI-agent detection on `guides/ai-agents/how-the-skill-works.md` gets the prompt in the change `docs-ai-agents-guide`, which owns that page and is not committed yet.

## Risks / Trade-offs

- [Piped input of people now shows `=> …` lines] → Only statements that return a value show one, and script files passed as arguments show none. Scripts that parse the REPL's output see the new lines.
- [An agent that pipes a fixed sequence gets `>>> ` between the outputs] → It marks where the output of each statement ends; `--no-prompt` removes it.
- [The agent detection misses an agent] → `--prompt`, `ROBOTCODE_REPL_PROMPT=1` or `ROBOTCODE_FORCE_AI_AGENT=1` shows the prompt.
