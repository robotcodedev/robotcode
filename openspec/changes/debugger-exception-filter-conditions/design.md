# Design

## Context

See proposal.md for the motivation. Checked on 2026-10-22 in the sources and with scripts that run Robot Framework under the debugger in the same process, as `tests/robotcode/debugger` does:

- `default_capabilities.py` advertises the four filters with `supports_condition=True` and without a `condition_description`; the DAP type has that field. It also advertises `supports_exception_filter_options`, so VS Code sends the filters, with their conditions, as `filterOptions`.
- `set_exception_breakpoints` keeps the `filterOptions` of the request, conditions included. Plain `filters` are ignored; the open change `debugger-dap-e2e-tests` plans to treat them like filter options without a condition.
- `process_end_state` compares only the filter ids of the kept options with the kinds of the failure. `end_keyword` passes `failed_keyword` for a failed keyword, setup or teardown, plus `uncaught_failed_keyword` when nothing catches the failure; `end_test` passes `failed_test`, `end_suite` `failed_suite`. The condition is never read: with `1 == 2` on "Failed Tests" or "Failed Keywords", the run stops at every failure, without a message.
- Line-breakpoint conditions are evaluated in `process_start_state` as `internal_evaluate_expression(variables.replace_string(condition), variables)` on `EXECUTION_CONTEXTS.current.variables.current`. An error doesn't stop the run and sends "Breakpoint condition error: …" to the debug console. `tests/robotcode/debugger/test_breakpoint_conditions.py` tests this.
- The variables at a stop, measured with Robot Framework 7.5:
  - at a failed library keyword inside a user keyword, those of the user keyword, its arguments included;
  - at a failed user keyword, those of its caller: Robot Framework calls `end_keyword` after the keyword's own variables are gone;
  - at a failed test, those of the test, with `${TEST_NAME}`, `${TEST_STATUS}` and the failure message in `${TEST_MESSAGE}`;
  - at a failed suite, those of the suite, with `${SUITE_STATUS}` and `${SUITE_MESSAGE}`, set before the suite teardown; the suite listener runs before the suite's variables are gone (Robot Framework 7.5 sources);
  - no variable holds the failure message of a keyword; `${KEYWORD_MESSAGE}` exists only in a keyword's teardown.
- At each stop the debugger knows the name of what failed and the failure message: it sends them as the id and the description of the exception, which VS Code's exception widget shows. Checked on 2026-10-23 with Robot Framework 7.5:
  - `BuiltIn.Should Be Equal` with `1 != 2`; `BuiltIn.Convert To Integer` with `ValueError: 'abc' cannot be converted to an integer: …`; a user keyword by its name, `My Keyword` with `my own message`;
  - a test by its name with its failure message, a suite by its name with an empty message when only its tests failed;
  - the form of a message can differ between Robot Framework versions: with 5.0, the message of `Convert To Integer    abc` doesn't start with `ValueError`.
- `Variables.copy()` exists from Robot Framework 5.0 to 7.5. Two variables set on a copy of the current variables are seen by `${name}` and by `$name` there, and not by the run: checked on 2026-10-23 with 5.0 on Python 3.10 and 7.5 on 3.14, with a teardown that runs `Variable Should Not Exist` after the stop.
- A condition takes both forms of Robot Framework's `Evaluate`: `'3 != 4' in '${TEST_MESSAGE}'` and `'3 != 4' in $TEST_MESSAGE`, checked with Robot Framework 5.0 on Python 3.10, 6.0 on 3.11 and 7.5 on 3.14. With `$name`, the value stays a Python object, so a message with quotes in it needs no quoting. Robot Framework 5.0 and 6.0 on Python 3.12 or newer, which those versions don't support and the local test matrix still runs, fail on `$name` with a syntax error.
- VS Code recognizes a stored exception filter only when its id, label, description, `supportsCondition` and `conditionDescription` stay the same (design of the archived change `debugger-exception-filter-names`). Otherwise it creates the filter anew with its default, and the stored condition is gone.
- The IntelliJ plugin offers no condition on its Robot Framework exception breakpoints and sends only the filter ids (`RobotCodeExceptionBreakpoints.arguments()`); the PyCharm guide names no condition there.

## Goals / Non-Goals

**Goals:**

- The conditions VS Code offers on the four filters work, with the syntax and the error handling of line-breakpoint conditions.
- A condition can ask for the name and the message of the failure, for every kind of failure in the same way.

**Non-Goals:**

- A condition field for the exception breakpoints in PyCharm; a change of its own.
- The type of a Python exception as a variable of its own; where Robot Framework puts it in front of the message, a condition finds it there.
- A placeholder text for the condition; see the decision below.
- Checking a condition when the client sets it.
- Plain `filters` in the request, planned in `debugger-dap-e2e-tests`.
- The stops at each enclosing keyword that a failure ends (finding G1), which stay as they are by decision of 2026-10-22.

## Decisions

### The conditions are evaluated where the filters are matched

`process_end_state` already gets the kinds of the failure and looks at the kept options. Each option of such a kind counts when it has no condition or its condition is true. The run stops when at least one option counts, and the stop is "unhandled" when `uncaught_failed_keyword` counts, as now with the matching options.

Alternative: evaluating in `end_keyword`, `end_test` and `end_suite`. Rejected: three places, and none of them sees the options.

### One evaluation for line breakpoints and exception filters

The evaluation of a condition, `replace_string` and then `internal_evaluate_expression` on the current variables, moves into a helper that raises on an error and takes variables to add for the evaluation. Both kinds of breakpoint call it and report an error each in their own way; line breakpoints add no variables. A condition is then written and understood the same way everywhere.

Alternative: a second copy of the evaluation. Rejected: two places that can drift apart.

### The variables of the place where the failure ends, and two of the failure

The condition sees the variables that are current when the debugger stops, as Robot Framework has them at that moment. In addition it sees `${EXCEPTION_NAME}` and `${EXCEPTION_MESSAGE}`, the id and the description of the exception the debugger reports for the stop. The user decided on 2026-10-23 to add them, since no variable of Robot Framework holds the failure message of a keyword, and one pair of names then works on all four filters.

The helper evaluates on a copy of the current variables with the two added, only when a condition is set. The run never sees them, and a variable of the run with the same name keeps its value; inside the condition, the two names stand for the failure.

Alternatives: Robot Framework's own names, `${KEYWORD_MESSAGE}` at a keyword and `${TEST_MESSAGE}` at a test. Rejected: a condition would need other names per filter, and there is no such variable for the name of a keyword. Python names in the namespace of the evaluation. Rejected: a condition could use them only as bare Python names, not as `${name}` or `$name` like every other variable. Setting them in the run's variables. Rejected: the run would see them, and they could overwrite a variable of the same name.

### An error doesn't stop the run

When a condition cannot be evaluated, its option doesn't count, and the debug console gets `Exception breakpoint condition error (<name of the filter>): <error>` as error output, each time, as line breakpoints do. Other options of the same failure still count: "Uncaught Failed Keywords" without a condition stops even when "Failed Keywords" has a condition with an error.

Alternatives: stopping on an error. Rejected, line breakpoints don't. Checking the condition in `set_exception_breakpoints` and answering unverified, which VS Code shows grayed out. Rejected: the variables exist only at the failure, and line breakpoints are not checked either.

### No placeholder text

The filters get no `condition_description`. A new one would make VS Code create the four filters anew once: "Failed Keywords", "Failed Tests" and "Failed Suites" off, "Uncaught Failed Keywords" on, and conditions gone. The user decided on 2026-10-22 to keep the stored filters. The condition box shows VS Code's own placeholder text, and the guide explains the syntax.

### Documentation

The sentence on conditions in the section on failures of `guides/vscode/running-and-debugging.mdx` says that a condition is written as for line breakpoints, that the run stops there only when it is true, and that `${EXCEPTION_NAME}` and `${EXCEPTION_MESSAGE}` hold the name and the message of the failure, with an example in the form `$name`. The PyCharm guide stays.

## Risks / Trade-offs

- [At a failed user keyword, a condition of "Failed Keywords" sees the variables of the caller, not the keyword's arguments] → that is where Robot Framework ends the keyword; accepted.
- [A condition with a variable of a user keyword is also evaluated at the enclosing keywords the failure ends, where the variable doesn't exist, and reports an error there] → correct, but noisy; the guide's example uses a variable of the test.
- [A test of the `$name` form fails in the local test matrix for Robot Framework 5.0 and 6.0, which run there on an unsupported Python] → such a test is skipped for Robot Framework before 6.1 on Python 3.12 or newer.
- [Whoever set a condition that the debugger ignored so far gets fewer stops after the update] → this is what VS Code and the guide promise; not breaking.
- [Inside a condition, a variable of the run named `${EXCEPTION_NAME}` or `${EXCEPTION_MESSAGE}` is hidden by the variable of the failure] → accepted; the names are unlikely in tests, and the run keeps its own value.
- [A condition on a message can depend on the Robot Framework version, as the message of `Convert To Integer` shows] → the messages are Robot Framework's; the scenarios use messages of `Fail`.
