# Tasks

## 1. setVariable writes the scope the variable is shown under

- [ ] 1.1 In `Debugger.set_variable` (`packages/debugger/src/robotcode/debugger/debugger.py`), branch on which of `local_id`, `test_id`, `suite_id` and `global_id` matched: Local writes the frame's own scope object (`get_first_or_self().variables()`), Test, Suite and Global call `context.variables.set_test`, `set_suite` (defaults) and `set_global`. Keep the shared evaluation and `_create_set_variable_result`. Verify with a new `tests/robotcode/debugger/test_set_value.py` that runs suites in-process like `test_terminate.py` does, sets a value at the stop through the scopes of the stack frames, resumes, and checks the run's log output: suite variable under Suite seen by the paused keyword and by the test afterwards; test variable under Test; global variable under Global seen by the next test; local of an outer frame changed while the inner keyword's own variables stay; local of the paused keyword.
- [ ] 1.2 Check the name in the target scope (frame scope, `_test`, `_suite`, `_global`) with the bare name and fail with `Variable '<name>' not found in the <scope> scope.`; a stale frame scope fails with `Frame is no longer available.`. Verify with tests for an unknown name under Suite and for a name that exists only in the paused keyword, asserting that no variable was created anywhere.
- [ ] 1.3 Refuse a variables reference of an expanded list or dictionary with `Items of lists and dictionaries cannot be set.` instead of `Invalid variable reference.`. Verify with a test that expands `@{items}` and sets its first item.

## 2. setExpression for watch expressions

- [ ] 2.1 Add `SetExpressionArguments`, `SetExpressionRequest`, `SetExpressionResponseBody` and `SetExpressionResponse` to `packages/debugger/src/robotcode/debugger/dap_types.py`, modelled on the `setVariable` types and the DAP specification. Verify with `hatch run lint:all`.
- [ ] 2.2 Add `Debugger.set_expression(expression, value, frame_id, format)`: accept only whole variables (`${name}`, `@{name}`, `&{name}`), resolve the frame (innermost without `frame_id`), then reuse the Local path of 1.1 and 1.2. Anything else fails with `Only whole variables (${name}, @{name}, &{name}) can be set, not '<expression>'.`. Verify with tests: `${x}` in the paused keyword; `@{items}` set to a list, response expandable; `${x}` for the outer frame changes `Outer` only; `${list}[0]`, `${obj.attr}` and `len(${list})` rejected with that message; an unknown name rejected per 1.2.
- [ ] 2.3 Register `setExpression` in `packages/debugger/src/robotcode/debugger/server.py` with `@rpc_method(name="setExpression", param_type=SetExpressionArguments)` and map the result to `SetExpressionResponseBody`. Verify with a test that sends the request through the server's rpc dispatch, or through a DAP client script against `robotcode debug --tcp`, and gets the new value back.
- [ ] 2.4 Extend the debugging page of the VS Code guide, `docs/src/content/docs/guides/vscode/running-and-debugging.mdx`, with a sentence on Set Value: the variable changes in the scope it is shown under, a watch sets the whole variable in the selected frame, and the value is an expression, so strings need quotes. Verify that `npm run docs:build` passes.

## 3. Verification

- [ ] 3.1 Run `hatch run test:test` and `hatch run lint:all` and verify that both pass.
- [ ] 3.2 Check the behaviour in VS Code with the isolated Playwright harness, or with a DAP client script that drives `robotcode debug --tcp` as the IDEs do: paused in a keyword, set a suite variable under Suite and a watch `${x}`, resume, and verify in the log that both tests see the new values; set `${list}[0]` as a watch and verify the refusal message.
