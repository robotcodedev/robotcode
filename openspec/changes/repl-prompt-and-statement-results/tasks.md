# Tasks

## 1. The prompt without a terminal

- [x] 1.1 Add the flag pair `--show-prompt` / `--no-show-prompt` (default not given, environment variable `ROBOTCODE_REPL_SHOW_PROMPT`) to `SHELL_OPTIONS` in `packages/repl/src/robotcode/repl/cli.py`, compute `show_prompt` in `repl` as in design D1 (terminal: shown; otherwise the option, else `is_running_in_ai_agent()`), and pass it through `_pick_interpreter()` to both console interpreters. Verify with tests in `tests/robotcode/repl/test_cli.py` for each row of the D1 table, with the terminal check and the agent detection set per test; they pass with the change and fail without it.
  - Done 2026-10-30: `_resolve_show_prompt()` in `cli.py` decides it; `robot-debug` passes `_is_interactive_stdin()`, as `>>> ` showed there before. `test_cli_show_prompt` covers the four rows of D1 and both values of `ROBOTCODE_REPL_SHOW_PROMPT` (8 cases); all fail on the code of HEAD. Four tests in `test_input_errors.py` that faked a terminal through `sys.stdin` now pass `show_prompt`.
- [x] 1.2 Use `show_prompt` in `ConsoleInterpreter.get_input()` in place of `sys.stdin.isatty()` for `>>> ` and `... `. Verify with a test that runs `robotcode repl` with piped input in a subprocess: with `ROBOTCODE_FORCE_AI_AGENT=1` the output shows `>>> ` before and after the output of `Log    hello` and `... ` inside an unfinished `FOR` block; with `ROBOTCODE_NO_AI_AGENT=1` it shows no prompt; a failing statement still ends the session with exit code 1 (spec "Prompt without a terminal in an agent session", "Option for the prompt").
  - Done 2026-10-30: `tests/robotcode/repl/test_prompt_and_results.py` pipes into `robotcode repl` in a subprocess; an agent session prints `>>> [ INFO ] hello\n>>> ... ... [ INFO ] a\n[ INFO ] b\n>>> `, `ROBOTCODE_NO_AI_AGENT=1` prints no prompt, `--show-prompt` / `--no-show-prompt` override the detection, and `Fail    boom` prints `>>> >>> ` and exits with 1. All but the case without an agent fail on the code of HEAD.

## 2. The result of a statement

- [x] 2.1 Add a step after `set_last_result()` in `BaseInterpreter.run_input()` that does nothing in the base class, and fill it in `ConsoleInterpreter` with a helper that prints `=> <value>` with `_repr` unless the value is `None` or the statement came from a script file (design D2). Verify with tests: `Evaluate    1 + 1` prints `=> 2`; `${x}=    Set Variable    42` prints its message and no `=>` line, and so do `Log    hello` and a failing `Should Be Equal    1    2`; and `Evaluate    1 + 1` from a script file passed as an argument prints none (spec "Result of a statement").
  - Done 2026-10-30: `BaseInterpreter.show_result()` after `set_last_result()`; `ConsoleInterpreter` prints through `_echo_result()` unless `_input_from_file`, which `get_input()` sets for the statements of a script file. `test_statement_shows_its_result` (4 cases) and `test_statements_of_a_script_file_show_no_result` in `test_prompt_and_results.py`; removing the `None` check, the assignment check or the script-file check each fails its case.
- [x] 2.2 Let `_evaluate_at_stop()` print its result through the same helper, so `None` and an assignment show no result (design D3). Verify with tests in `tests/robotcode/repl/test_debug_console.py`: `Log    hello` at the `(rdb)` prompt prints no `=> None`, `${x}=    Set Variable    42` prints its message and no `=>` line, `Evaluate    1 + 1` prints `=> 2`, and the existing tests for `=> '42'` and `=> 'hello'` still pass (spec "No result for None").
  - Done 2026-10-30: `_evaluate_at_stop()` prints through `_echo_result()` for the last statement of the line. `test_evaluation_shows_no_result_for_none_or_an_assignment` (3 cases); with the old echo the cases `none` and `assignment` fail. The tests for `=> '42'` and `=> 'hello'` pass unchanged.
- [x] 2.3 Verify that `robotcode repl-server` answers as before: its tests in `tests/robotcode/repl_server/` pass unchanged.
  - Done 2026-10-30: its `Interpreter` inherits the empty `show_result()`; the 6 tests in `tests/robotcode/repl_server/` pass without a change to them (RF 7.5; again in the matrix of 4.1).

## 3. Documentation

- [x] 3.1 Update `docs/src/content/docs/guides/cli/repl.md` (design D4): in "How the prompt works", when the prompt shows without a terminal, the option `--show-prompt` / `--no-show-prompt`, and the result after each statement without `None`; in the section on AI agents and automation, the prompt in agent sessions. Verify in the dev server that the page shows the changes and its links resolve.
  - Done 2026-10-30: "How the prompt works" got the results with an example and the prompt without a terminal; "Disabling all enhancements" got the prompt in agent sessions with a `--show-prompt` example, whose output matches a real run. The running dev server shows both, and every anchor and internal link of the page resolves.
- [x] 3.2 Update the sentence on results at the `(rdb)` prompt in `docs/src/content/docs/guides/cli/robot-debug.md`: `None` shows nothing. Verify in the dev server.
  - Done 2026-10-30: besides the sentence at the `(rdb)` prompt, the page showed `=> None` in the example "A debug session, end to end" and said so in the sentence after it; both changed too. Checked in the dev server, `=> None` no longer appears.
- [x] 3.3 Generate `docs/src/content/docs/reference/cli.md` again with `hatch run create-cmd-line-docs`. Verify that the diff adds the option `--show-prompt` / `--no-show-prompt` to `repl` and changes nothing else.
  - Done 2026-10-30: the diff adds only `--show-prompt / --no-show-prompt` to `repl` (5 lines).

## 4. Checks

- [x] 4.1 Run `hatch run lint:all` and `hatch run test:test`, and verify that both pass.
  - Done 2026-10-30: `lint:all` passes (ruff, mypy on 505 files) after `_pick()` in `test_backends.py` got `show_prompt` and a pass-through test for both backends; `test:test` passes in all 9 environments, RF 5.0 to 7.5, without a failure (e.g. RF 7.5: 5753 passed, 97 skipped).
- [x] 4.2 Repeat the trial of finding B2, `playground/robotcode-demo/agent-sessions/trials/fifo_repl.sh`, which drives the REPL through a FIFO with `CLAUDECODE=1` and waits for `>>> ` at the end of the log. Verify that each statement ends with `>>> `, `Import Resource` included, that `${order}=    Create Order    coffee    quantity=2` shows the message that sets `${order}` and no `=>` line, and that the failing `Create Order    mug` shows its failure and no `=>` line.
  - Done 2026-10-30: each turn ended with `>>> `, the first one before any input; the assignment printed `[ INFO ] ${order} = order-4711` without `=>`, `Create Order    mug` printed `[ FAIL ] mug is out of stock` without `=>`, and `.exit` ended with 1 after that failure. The task first expected `=> 'order-4711'` for the assignment; it now follows the decision that an assignment shows no result (edb31d406).
- [x] 4.3 Run `npm run docs:build` with all internal links valid, and `openspec validate repl-prompt-and-statement-results --strict`.
  - Done 2026-10-30: 92 pages built, "All internal links are valid."; the change is valid with `--strict`.

## Workflow follow-up

- After the archive, run `openspec validate --specs --strict` and verify that all main specs pass.
- Outside this change: the RobotCode skill in robotframework-agent-plugins tells an agent to wait for the prompt (findings B1–B3); the table of the AI-agent detection on `guides/ai-agents/how-the-skill-works.md` gets the prompt in the change `docs-ai-agents-guide`.
