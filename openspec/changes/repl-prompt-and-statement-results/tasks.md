# Tasks

## 1. The prompt without a terminal

- [ ] 1.1 Add the flag pair `--show-prompt` / `--no-show-prompt` (default not given, environment variable `ROBOTCODE_REPL_SHOW_PROMPT`) to `SHELL_OPTIONS` in `packages/repl/src/robotcode/repl/cli.py`, compute `show_prompt` in `repl` as in design D1 (terminal: shown; otherwise the option, else `is_running_in_ai_agent()`), and pass it through `_pick_interpreter()` to both console interpreters. Verify with tests in `tests/robotcode/repl/test_cli.py` for each row of the D1 table, with the terminal check and the agent detection set per test; they pass with the change and fail without it.
- [ ] 1.2 Use `show_prompt` in `ConsoleInterpreter.get_input()` in place of `sys.stdin.isatty()` for `>>> ` and `... `. Verify with a test that runs `robotcode repl` with piped input in a subprocess: with `ROBOTCODE_FORCE_AI_AGENT=1` the output shows `>>> ` before and after the output of `Log    hello` and `... ` inside an unfinished `FOR` block; with `ROBOTCODE_NO_AI_AGENT=1` it shows no prompt; a failing statement still ends the session with exit code 1 (spec "Prompt without a terminal in an agent session", "Option for the prompt").

## 2. The result of a statement

- [ ] 2.1 Add a step after `set_last_result()` in `BaseInterpreter.run_input()` that does nothing in the base class, and fill it in `ConsoleInterpreter` with a helper that prints `=> <value>` with `_repr` unless the value is `None` or the statement came from a script file (design D2). Verify with tests: `Evaluate    1 + 1` prints `=> 2`; `${x}=    Set Variable    42` prints its message and no `=>` line, and so do `Log    hello` and a failing `Should Be Equal    1    2`; and `Evaluate    1 + 1` from a script file passed as an argument prints none (spec "Result of a statement").
- [ ] 2.2 Let `_evaluate_at_stop()` print its result through the same helper, so `None` and an assignment show no result (design D3). Verify with tests in `tests/robotcode/repl/test_debug_console.py`: `Log    hello` at the `(rdb)` prompt prints no `=> None`, `${x}=    Set Variable    42` prints its message and no `=>` line, `Evaluate    1 + 1` prints `=> 2`, and the existing tests for `=> '42'` and `=> 'hello'` still pass (spec "No result for None").
- [ ] 2.3 Verify that `robotcode repl-server` answers as before: its tests in `tests/robotcode/repl_server/` pass unchanged.

## 3. Documentation

- [ ] 3.1 Update `docs/src/content/docs/guides/cli/repl.md` (design D4): in "How the prompt works", when the prompt shows without a terminal, the option `--show-prompt` / `--no-show-prompt`, and the result after each statement without `None`; in the section on AI agents and automation, the prompt in agent sessions. Verify in the dev server that the page shows the changes and its links resolve.
- [ ] 3.2 Update the sentence on results at the `(rdb)` prompt in `docs/src/content/docs/guides/cli/robot-debug.md`: `None` shows nothing. Verify in the dev server.
- [ ] 3.3 Generate `docs/src/content/docs/reference/cli.md` again with `hatch run create-cmd-line-docs`. Verify that the diff adds the option `--show-prompt` / `--no-show-prompt` to `repl` and changes nothing else.

## 4. Checks

- [ ] 4.1 Run `hatch run lint:all` and `hatch run test:test`, and verify that both pass.
- [ ] 4.2 Repeat the trial of finding B2, `playground/robotcode-demo/agent-sessions/trials/fifo_repl.sh`, which drives the REPL through a FIFO with `CLAUDECODE=1` and waits for `>>> ` at the end of the log. Verify that each statement ends with `>>> `, `Import Resource` included, that `${order}=    Create Order    coffee    quantity=2` shows `=> 'order-4711'`, and that the failing `Create Order    mug` shows its failure and no `=>` line.
- [ ] 4.3 Run `npm run docs:build` with all internal links valid, and `openspec validate repl-prompt-and-statement-results --strict`.

## Workflow follow-up

- After the archive, run `openspec validate --specs --strict` and verify that all main specs pass.
- Outside this change: the RobotCode skill in robotframework-agent-plugins tells an agent to wait for the prompt (findings B1–B3); the table of the AI-agent detection on `guides/ai-agents/how-the-skill-works.md` gets the prompt in the change `docs-ai-agents-guide`.
