# Tasks

## 1. One rule in the debugger and at `.print`

- [x] 1.1 In `_debug/controller.py`, make `evaluate_expression` decide with `is_variable` (D6), keep `_IS_VARIABLE_RE` for `set_variable` and adjust its comment. In `tests/robotcode/repl/test_debug_console.py`, cover `.print ${${inner}}`, `.print ${{"ich" + "bin" * 5}}`, the same for `.pprint`, `.whatis`, `.display` and a breakpoint condition; that `${a} + ${b}` still calculates is covered there already. Verify that the new tests pass with the fix and fail without it.
- [x] 1.2 In `debugger.py`, make `_evaluate_repl_mode` and `_evaluate_expression_mode` decide with `is_variable` on the stripped expression (D6). Add `tests/robotcode/debugger/test_evaluate.py`, which calls `Debugger.evaluate` from a second thread while the run is stopped, for the scenarios of "Debug Console follows the same rule" and "Two variables in a watch" and "Unknown variable in a watch". Verify that they pass with the fix and fail without it, and only need this fix.

## 2. `>>>` and sessions

- [x] 2.1 Add the method of D3 to `ConsoleInterpreter`: check with `is_variable`, read the value with the marker of D5, echo `=> <value>`, or log the failure with level `FAIL` and raise `ExecutionFailed`. Call it from `ConsoleInterpreter.get_input` for a fresh input and from `SessionInterpreter.get_input`. In `tests/robotcode/repl/test_prompt_and_results.py`, cover the scenarios of "A variable as the whole input shows its value" at `>>>`, including `=> None`, whitespace and a multi-line input with only blank lines around the variable, and verify they pass.
- [x] 2.2 Cover "Any other input stays a statement" in `tests/robotcode/repl/test_prompt_and_results.py`, with a resource file in `tmp_path` for the keyword with embedded arguments, and the scenarios that start at RF 6.0 skipped below it (one check of `RF_VERSION` at module scope). Verify that the embedded-arguments test also passes without the change, and that it fails if the check is switched to `IS_VARIABLE_RE`.
- [x] 2.3 Cover "Showing a value is not a keyword call": the session test in `output.xml` has status PASS and no keyword for the input, piped input exits with 0, `${_}` keeps the result of the keyword before, and `.save` doesn't export the input (`test_input_errors.py`, which holds the `.save` tests). Verify the tests pass.
- [x] 2.4 Cover "A value that cannot be resolved is a failure" at `>>>`: `${nope}` and `${{1/0}}` show Robot Framework's message and no `=>` line, piped input exits with 1, and the session test in `output.xml` is FAIL. Verify the tests pass.
- [x] 2.5 Cover `robotcode session send` in `tests/robotcode/repl/test_sessions.py`: `${x}` exits with 0 and prints `=> <value>`, `${nope}` exits with 1. Verify the tests pass.
- [x] 2.6 Cover Ctrl-C at `>>>` in `tests/robotcode/repl/test_termination_signals.py`, with an expression that raises the signal itself, and `session interrupt` in `test_sessions.py` with `${{time.sleep(30)}}`: the expression stops early, the session goes on, and `session wait` exits with 1. Verify that the tests pass with the marker of D5 and fail without it.

## 3. `(rdb)`

- [x] 3.1 In `_evaluate_at_stop`, check first, before the guard for the end of a suite (D4): read through `evaluate_expression` of the selected frame with the marker of D5, echo `=> <value>`, or echo `! <message>` and return `False`. Cover in `tests/robotcode/repl/test_debug_console.py`: the value, `=> None`, a caller's variable after `.up`, a suite variable at a failed-suite stop next to the existing `test_keywords_are_refused_at_a_failed_suite_stop`, a line in a breakpoint's `commands`, and `${user} logs in to ${page}` still running the keyword. Verify the tests pass.
- [x] 3.2 Cover the failure at `(rdb)`: `${nope}` shows the message, the session test stays PASS (`test_run.py`, next to the failing keyword at a stop), and `session send` in a debug session exits with 1 (`test_sessions.py`). Verify the tests pass.
- [x] 3.3 Cover Ctrl-C at `(rdb)` in `tests/robotcode/repl/test_debug_console.py`, which runs a real stop: the expression stops early and the run stays paused. Verify that the test passes with the marker of D5 and fails without it.

## 4. Documentation

- [x] 4.1 In `docs/src/content/docs/guides/cli/repl.md`, after the paragraph on `=> <value>`, describe the new input: a variable alone, also with item access, nested or as inline Python, shows its value, also `None`; only as the whole input; it is no keyword call, so `${_}`, the output files and `.save` don't see it; a failure fails the session. In `guides/cli/robot-debug.md`, add the same for `(rdb)` where the prompt and the typed keyword are described, with the selected frame. Verify with the docs dev server that both pages render.

## 5. Whole change

- [x] 5.1 Run `hatch run lint:all` and `hatch run test:test`, and report failures with their output. RF 5.0 and 6.0 results count on a Python they support, per `hatch run devel.py3.10-rf50:test` and `devel.py3.10-rf60:test` for the affected test files.
- [x] 5.2 Check the real programs before and after: the command from #684 piped into `robotcode repl`; a real DAP client over TCP for `${user} logs in to ${page}` and the watch `${n} + ${n}`; `.print ${${inner}}` in `robotcode robot-debug`; `${{time.sleep(30)}}` with Ctrl-C at the prompt-toolkit prompt. Record before and after in the report.

## Workflow follow-up

- Commit only on request: the debugger and `.print` fix of group 1 as `fix(debugger)`, the rest as `feat(repl)` with `Fixes #684`, the plan and the tasks as `docs(openspec)`.
- Archive with `/opsx:archive` after the review, then `openspec validate --specs --strict`.
