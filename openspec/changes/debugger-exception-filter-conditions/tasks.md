# Tasks

## 1. Debugger

- [ ] 1.1 In `packages/debugger/src/robotcode/debugger/debugger.py`, move the evaluation of a line-breakpoint condition (`replace_string`, then `internal_evaluate_expression` on the current variables) into a helper that raises on an error and takes variables to add, which it sets on a copy of the current variables (`Variables.copy()`). Let the line breakpoints use it without added variables and with their message "Breakpoint condition error: …" unchanged. Verify that `tests/robotcode/debugger/test_breakpoint_conditions.py` passes without changes.
- [ ] 1.2 In `process_end_state`, count a kept filter option of the failure's kinds only when it has no condition or the helper finds its condition true; for an error, send `Exception breakpoint condition error (<name of the filter>): <error>` to the debug console as error output and don't count that option. Add `tests/robotcode/debugger/test_exception_breakpoint_conditions.py`, running Robot Framework under the debugger as `test_breakpoint_conditions.py` does, with the scenarios of the requirements "Conditions of the exception filters" and "A condition that cannot be evaluated": a false condition, the test name, the failure message of a test (`'3 != 4' in $TEST_MESSAGE`), a condition on "Failed Keywords", a filter without a condition, an unknown variable with the exact message, and a keyword failure with an erroneous condition on "Failed Keywords" next to "Uncaught Failed Keywords" without one, which stops as unhandled. Skip the tests with the form `$name` for Robot Framework before 6.1 on Python 3.12 or newer. Verify with `hatch run test:test` and `hatch run lint:all`.
- [ ] 1.3 Pass `${EXCEPTION_NAME}`, the name of what failed that `process_end_state` reports as the exception's id, and `${EXCEPTION_MESSAGE}`, the failure message, as the variables the helper adds for a condition of an exception filter. Add the scenarios of the requirement "Variables of the failure in a condition" to `test_exception_breakpoint_conditions.py`: the name of the failed keyword, a failure message with quotes, a teardown that finds no `${EXCEPTION_NAME}`, and a variable of the run with the same name that keeps its value. Verify with `hatch run test:test` and `hatch run lint:all`.

## 2. Documentation

- [ ] 2.1 In `docs/src/content/docs/guides/vscode/running-and-debugging.mdx`, extend the sentence on conditions in the section on failures: a condition is written as for line breakpoints, the run stops there only when it is true, and `${EXCEPTION_NAME}` and `${EXCEPTION_MESSAGE}` hold the name and the message of the failure, with an example in the form `$name` such as `$EXCEPTION_NAME == 'BuiltIn.Should Be Equal'`. Mark finding G2 in `playground/pycharm-befunde.md` as resolved by this change. Verify that `npm run docs:build` passes.

## 3. Verification

- [ ] 3.1 In the isolated VS Code harness with the real RobotCode extension: switch "Failed Tests" on with the debugger before task 1.2 (or a copy of the committed debugger), then with the changed debugger check that it is still on; set the condition `'${TEST_NAME}' == 'Second'` on it with **Edit Condition**, where the box shows VS Code's own placeholder text, and debug a suite whose tests `First` and `Second` fail: the run stops only at the end of `Second`. Then set `$EXCEPTION_NAME == 'BuiltIn.Should Be Equal'` on "Failed Keywords" and check that the run stops only at that keyword. Record the results in design.md under a Verification section.

## Workflow follow-up

- Archive the change with `/opsx:archive` once it is implemented and committed.
