# Proposal

## Why

VS Code offers **Edit Condition** on all four exception filters of the debugger, "Failed Keywords", "Uncaught Failed Keywords", "Failed Tests" and "Failed Suites", because the debugger advertises `supportsCondition` for them, and the VS Code guide says that each of them takes a condition. The debugger never evaluates the condition, though: with the condition `1 == 2` on "Failed Tests", a run still stops at every failing test (finding G2 of the review of the PyCharm guide, reproduced on 2026-10-22 with Robot Framework 7.5). Whoever narrows the stops down with a condition gets every stop anyway.

## What Changes

- The debugger evaluates the condition of an exception filter each time a failure of that filter's kind occurs, and stops for that filter only when the condition is true. A filter without a condition stops as before.
- A condition is written like the condition of a line breakpoint: a Python expression in which Robot Framework variables are replaced, or used as Python values in the form `$name`. It sees the variables of the place where the failure ends, for example `${TEST_NAME}`, and at a failed test the failure message in `${TEST_MESSAGE}`.
- A condition also sees two variables of the failure: `${EXCEPTION_NAME}`, the name of the keyword, test or suite that failed, as VS Code's exception widget shows it, and `${EXCEPTION_MESSAGE}`, the failure message. They exist only while the condition is evaluated; the run never sees them.
- A condition that cannot be evaluated doesn't stop the run; the Debug Console says why, as it does for line breakpoints.
- The filters keep their ids, names, descriptions and `supportsCondition`, and get no placeholder text for the condition, so that VS Code keeps the filters as the user has switched them on or off.
- The VS Code guide says how a condition is written and which variables it sees, the two of the failure included.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `debugger-exception-filters`: a new requirement on the conditions of the exception filters.

## Impact

- `packages/debugger/src/robotcode/debugger/debugger.py`: `process_end_state` evaluates the conditions of the filter options; the evaluation of line-breakpoint conditions moves into a helper that both use.
- `tests/robotcode/debugger/`: tests of conditions on exception filters, with Robot Framework running under the debugger as in `test_breakpoint_conditions.py`.
- `docs/src/content/docs/guides/vscode/running-and-debugging.mdx`: the sentence about conditions in the section on failures.
- No change to `default_capabilities.py`, the VS Code extension, the IntelliJ plugin or the PyCharm guide. PyCharm offers no condition on its Robot Framework exception breakpoints; a condition field there would be a change of its own.
