# Tasks

## 1. Shell prompt `>>>`

- [x] 1.1 In `ConsoleInterpreter.get_input`, handle every `KeyboardInterrupt` from `_read` (D2, D5):
  - clear `lines` and `last_one`;
  - print `KeyboardInterrupt` on a line of its own;
  - read again, without re-raising.

  Verify with scripted-reader tests in `tests/robotcode/repl/test_input_errors.py`:
  - Ctrl-C inside an unfinished `FOR` block discards the block without running it, and the next input runs;
  - Ctrl-C at an empty prompt prints `KeyboardInterrupt`, and the session goes on;
  - `EOFError` afterwards still ends the session.
- [x] 1.2 Add a subprocess test to `tests/robotcode/repl/test_session_termination.py`. It starts `robotcode repl --backend plain` and sends these lines, with SIGINT after the second:
  1. `FOR    ${i}    IN    a`
  2. `    Log To Console    loop ${i}`
  3. `Log To Console    after`
  4. `.exit`

  Verify that `loop` is never printed, `after` is printed, and the process exits with code 0.
- [x] 1.3 In `docs/src/content/docs/guides/repl.md` ("How the prompt works", next to the sentence on how to exit), describe that Ctrl-C discards the typed line or the unfinished block, prints `KeyboardInterrupt` and shows `>>>` again. Verify with `npm run docs:build`.

## 2. Debugger prompt `(rdb)`

- [x] 2.1 In `ConsoleInterpreter.wait_at_stop`, handle `KeyboardInterrupt` and `EOFError` differently (D3):
  - `KeyboardInterrupt` prints the message and reads again;
  - `EOFError` resumes as before.

  Update the docstring and the comments. Verify with tests in `tests/robotcode/repl/test_debug_console.py`:
  - a reader that raises `KeyboardInterrupt` and then returns `.continue` gives exactly one stop, and the stopped keyword runs only after `.continue`;
  - `test_eof_at_prompt_continues` still passes.
- [x] 2.2 Rewrite `test_sigint_at_a_debugger_stop_resumes_the_run_with_the_plain_backend` in `test_session_termination.py` so that it expects the run to stay paused, and update the module docstring. Verify that after SIGINT the process still runs and prints `KeyboardInterrupt`, and that `.continue` then ends it with exit code 0 and a passed test.
- [x] 2.3 In `docs/src/content/docs/guides/robot-debug.md`, rewrite the sentence that says Ctrl-C or Ctrl-D at `(rdb)` resumes the run:
  - Ctrl-C discards the typed input, and the run stays paused;
  - Ctrl-D resumes it, as `.continue` does.

  Verify with `npm run docs:build`.

## 3. Breakpoint commands `(com)`

- [x] 3.1 In the `.commands` dot command, handle `KeyboardInterrupt` (D4):
  - keep `bp.commands`;
  - print `KeyboardInterrupt` and `breakpoint N: commands unchanged`;
  - return.

  `end` and `EOFError` store the commands as before. Verify with tests in `test_debug_console.py`:
  - a breakpoint with `.print ${i}` keeps only that command after an entry of `.continue` aborted with `KeyboardInterrupt`, and the stop's prompt reads again;
  - an entry ended with `EOFError` stores what was typed.
- [x] 3.2 In the `.commands` row of the command table in `guides/robot-debug.md`, describe that Ctrl-C aborts the entry and keeps the previous commands. Verify with `npm run docs:build`.

## 4. Pausing a run with Ctrl-C

- [x] 4.1 In `DebugController` (D9):
  - `_pause` clears a pending pause request;
  - add a method that cancels a pending pause request;
  - add a read-only property that tells whether a pause request is pending.

  Verify with tests in `tests/robotcode/repl/test_debug_controller.py`:
  - with a pause requested, an exception stop that comes first is the only stop of the run;
  - a cancelled pause request doesn't stop;
  - `test_request_pause_stops_at_next_executed_keyword` still passes.
- [x] 4.2 In `base_interpreter.py`, let the patched `_StopSignalMonitor.__call__` ask a new interpreter hook before it interrupts a running keyword. `BaseInterpreter`'s hook reports that it didn't handle the signal.

  In `ConsoleInterpreter`, implement the conditions of D6. The hook requests the pause before it writes the message of D8 on a line of its own, and a failed write doesn't escape the handler.

  Verify with monitor tests in `tests/robotcode/repl/test_termination_signals.py`:
  - attached, inside `forward_events` and no stop: the pause is requested, nothing is raised, and the message is printed;
  - the keyword is interrupted with `ExecutionInterrupted` when the debugger is detached, at a stop, while a pause is pending, and in a REPL session outside a statement;
  - a plain `BaseInterpreter` is unchanged;
  - the two existing SIGINT tests still pass.
- [x] 4.3 Cancel a pending pause when a REPL statement ends (D9). Verify with a test that a pause requested during the last keyword of a statement doesn't stop the next statement.
- [x] 4.4 Add subprocess tests to `test_session_termination.py`, using the plain backend:
  - a robot-debug run of a keyword that sleeps 3 seconds and then `Log To Console`, which gets SIGINT while the keyword runs, prints the message, stops with `* pause` at `Log To Console`, and after `.continue` exits with code 0 and a passed test;
  - a second SIGINT while such a keyword sleeps 30 seconds makes it fail with `Execution interrupted` well before 30 seconds, and the run stops with `* exception`;
  - `robotcode repl --debugger-attached` stops with `* pause` before the second `Sleep` of a `FOR` loop.

  The keyword of the robot-debug tests comes from a small test library and prints before it sleeps, so the signal sent after its output always arrives while it runs. Verify that they pass with `hatch run test:test tests/robotcode/repl/test_session_termination.py`.
- [x] 4.5 Update the docs, then verify with `npm run docs:build`:
  - in `guides/robot-debug.md`, add Ctrl-C to the table of ways to make a run pause, and describe the message and the second Ctrl-C;
  - in `guides/repl.md`, extend the sentence "`Ctrl-C` interrupts a keyword that runs" with the pause while the debugger is attached, and mention the pause under "Debugging at the prompt".

## 5. Ctrl-C in a robot-debug run without the debugger

- [x] 5.1 In `base_interpreter.py`, let the patched `_StopSignalMonitor.__call__` ask a second interpreter hook, after the pause hook, whether SIGINT ends the run (D10). `BaseInterpreter`'s hook says no. `ConsoleInterpreter`'s says yes outside a REPL session when the debugger is detached or missing. The monitor then takes the run branch of the SIGTERM handling, with SIGINT counted together with SIGTERM.

  Verify with monitor tests in `tests/robotcode/repl/test_termination_signals.py`:
  - a robot-debug run without the debugger gets Robot Framework's `ExecutionFailed` with `exit=True` and `Execution terminated by signal` while a keyword runs;
  - a second SIGINT, and SIGINT after SIGTERM, end with exit code 253 through the fake `os._exit`;
  - a REPL statement with the debugger detached still gets `ExecutionInterrupted`; the `detached` case of `test_sigint_interrupts_the_running_keyword_where_nothing_pauses` moves to a REPL statement;
  - the attached cases and `repl-server` are unchanged.
- [x] 5.2 Add subprocess tests to `test_session_termination.py`, with the napping library:
  - `robot-debug --no-debugger-attached` with two tests: SIGINT during the first ends the run as in `robotcode robot`. The first test fails with `Execution terminated by signal`, the second with `Test execution stopped due to a fatal error.`, the exit code is 2, and `output.xml` is written;
  - `.detach` at a stop, then SIGINT: the same results;
  - a second SIGINT while the teardown of the first test runs ends the process with exit code 253.

  Verify that they pass with `hatch run test:test tests/robotcode/repl/test_session_termination.py`.
- [x] 5.3 In the `Ctrl-C` row of the table of ways to make a run pause in `guides/robot-debug.md`, replace "detached, `Ctrl-C` interrupts the keyword that runs" with the new behavior: without the debugger (`--no-debugger-attached`, or after `.detach`), `Ctrl-C` ends the run as in `robotcode robot`, and a second `Ctrl-C` ends it at once. Verify with `npm run docs:build`.

## 6. Agent skill

- [x] 6.1 In `robotframework-agent-plugins`, correct the Ctrl-C statements in `plugins/robotcode/skills/robotcode/SKILL.md`, `references/debugging.md` and `references/repl.md`. Ctrl-D resumes a stop; Ctrl-C keeps it paused. Change only what becomes wrong. Edit upstream only, never the vendored copy in `chat-plugins/`, and commit upstream only with the user's approval. Then re-sync with `scripts/sync_chat_plugin.py`, and verify with `scripts/sync_chat_plugin.py --check`.

## 7. Integration checks

- [x] 7.1 Drive the prompt-toolkit backend through a pty with the scratch drivers:
  - Ctrl-C at `>>>` in an unfinished block and at an empty prompt;
  - Ctrl-C at `(rdb)`;
  - Ctrl-C at `(com)`;
  - Ctrl-C during a robot-debug run.

  Confirm that `KeyboardInterrupt` and the pause message each start on a line of their own (D5), with the plain backend as well.
- [x] 7.2 Run `hatch run lint:all` and `hatch run test:test` (full Robot Framework matrix) and confirm that both pass.
- [x] 7.3 Run `openspec validate prompt-ctrl-c-like-python --strict` and confirm that it passes.

## Workflow follow-up

- Archive the change after review; the sync creates the main spec `session-interrupt`.
- Remove findings P17 and P18, and the `pause` part of P16, from `playground/docs-review-befunde.md`.
