# Design

## Context

See proposal.md for the motivation. The facts that shape the approach, all read in the code on 2026-10-15:

- `Debugger.set_variable` (`packages/debugger/src/robotcode/debugger/debugger.py:2167`) finds the stack frame entry whose `global_id`, `local_id`, `suite_id` or `test_id` equals the variables reference, but then ignores which of the four matched: it checks the name against `context.variables.current` and writes `variables[name] = value` there, the innermost scope at the stop. The `Variables` view fills its groups differently: Global from `context.variables._global`, Suite from `_suite`, Test from `_test`, Local from the frame's own scope object, which `StackFrameEntry.variables` holds as a weak reference (`debugger.py:241`, `_get_variables_no_filter`, `debugger.py:1690`).
- Robot Framework's scopes are copies. `VariableScopes.start_keyword` copies the suite scope, or the test scope while a test runs, so a keyword never sees the caller's locals. `set_global`, `set_suite(name, value, top=False, children=False)` and `set_test` write the current scope and every scope up to the target one and record the assignment, so keyword scopes started later get the value too. Verified in Robot Framework 5.0 and 7.5 (`robot/variables/scopes.py`); the signatures are the same. `VariableStore.__contains__` takes the bare name, `__setitem__` takes the decorated one and normalizes `@{}` and `&{}` values.
- `supportsSetExpression` is advertised (`default_capabilities.py:11`), but `server.py` has no handler and `dap_types.py` has no types for it. The launcher forwards every request it does not handle itself to the debuggee (`launcher/server.py:319-364`), so a new handler in the debuggee is enough.
- The entered value is evaluated with `internal_evaluate_expression(variables.replace_string(value), variables)`, the same path as the Debug Console. The IntelliJ spec (`intellij-debugging`, "Set Value evaluates the new value") describes exactly that.
- The IntelliJ plugin offers Set Value only for the Local scope of the innermost frame (`RobotCodeNamedValue.kt`), by design, because of the behaviour this change fixes. VS Code offers it everywhere the debugger advertises it.
- `tests/robotcode/debugger/test_terminate.py` has a helper that runs a suite in-process with `robot.run`, the debugger's listeners and `Debugger.instance`, and acts at the first `StoppedEvent`. The set-value tests can use the same pattern: at the stop, read the frames and scopes, set a value, resume, and check the run's log output.

## Goals / Non-Goals

**Goals:**

- One rule for the target of a set: the scope the client shows the variable under, or the own variables of the frame a watch expression is evaluated in.
- Reuse Robot Framework's own scope semantics for Test, Suite and Global instead of imitating them.
- Error messages that say what went wrong in the words of the Variables view (scope names, "whole variables").

**Non-Goals:**

- Changing how the value is interpreted (expression stays).
- Setting items of lists and dictionaries, extended variables (`${obj.attr}`) or anything but whole variables.
- The command-line debugger's `.set` and the IntelliJ plugin's restriction; both are follow-ups named in the proposal.

## Decisions

### The matched variables reference decides the target scope

`set_variable` keeps finding the frame entry by the four ids, but then branches on which id matched. Local: the frame's own scope object from `StackFrameEntry.variables()` (via `get_first_or_self()`, as the Variables view does). Test, Suite, Global: Robot Framework's `context.variables.set_test`, `set_suite` and `set_global`.

Alternative, writing only the target dictionary (`_suite[name] = value`): rejected, because the copies in the test and keyword scopes between the paused keyword and the suite would keep the old value, the mirror image of today's bug. Robot Framework's methods write the whole chain and record the assignment for scopes that start later, identical from 5.0 to 7.5.

`set_suite` is called with its defaults (`children=False`), as `Set Suite Variable` without `children=True` does: the value holds for the rest of this suite, not for child suites.

### Local writes only the frame's own scope

For the Local group of any frame, the value is written into that frame's scope object only, with `__setitem__` on the decorated name. For the innermost frame that is `context.variables.current`, today's behaviour. For an outer frame it is the scope the keyword resumes with after the inner keyword returns; the inner keyword's scope is a copy of the test or suite scope, not of the caller's, so nothing has to be propagated and a same-named local of the inner keyword stays untouched.

Alternative, routing Local through `set_keyword`/`set_local_variable`: rejected, because both write `current`, not an outer frame, and `set_local_variable` no longer exists in Robot Framework 7.5.

### Existence is checked in the target scope

Before writing, the bare name must be in the target: the frame scope for Local and the watch case, `_test`, `_suite` or `_global` for the groups. Otherwise `NameError("Variable '${x}' not found in the Suite scope.")`, which the DAP layer turns into the error response the client shows. This keeps "never creates a variable" and makes the scope part of the message. The names arrive decorated from the clients; `IS_VARIABLE_RE` strips the decoration for the check, as today.

### `setExpression` sets whole variables in the frame's own scope

The expression must match a whole variable (`${name}`, `@{name}`, `&{name}`; `IS_VARIABLE_RE` without a trailing item or attribute part). The target is the own scope of the frame `frameId` names, or the innermost frame without one; evaluation, existence check and response are the Local path of `set_variable`, so both requests share one implementation. Anything else fails with "Only whole variables (`${name}`, `@{name}`, `&{name}`) can be set, not '<expression>'."

Alternative, resolving the scope a watched variable "comes from" (global, suite, test or local): rejected. With shadowing the origin is ambiguous, and the Variables view groups already give the user explicit control over the scope. A watch is evaluated in the selected frame, so setting it there is what the view suggests.

### The value stays an expression

Unchanged: `replace_string` then `internal_evaluate_expression`, result stored with its type, response built with `_create_set_variable_result` so lists and dictionaries get a variables reference and can be expanded. A literal mode would change the IntelliJ spec and the Debug Console's contract; the command-line `.set` keeps its own literal convention.

### Items get a clear refusal

A variables reference that belongs to an expanded list or dictionary (the variables cache, not a frame) fails with "Items of lists and dictionaries cannot be set." instead of today's "Invalid variable reference.", which also covers a stale reference.

### DAP plumbing

`dap_types.py` gets `SetExpressionArguments(expression, value, frame_id, format)`, `SetExpressionRequest`, `SetExpressionResponseBody(value, type, presentation_hint, variables_reference, named_variables, indexed_variables)` and `SetExpressionResponse`, modelled on the `setVariable` types. `server.py` gets `@rpc_method(name="setExpression", param_type=SetExpressionArguments)` that calls `Debugger.instance.set_expression`. Nothing changes in the launcher or the clients.

## Risks / Trade-offs

- [The frame's scope object is held weakly and may be gone for a hidden or finished frame] → the Local and watch paths fail with "Frame is no longer available." instead of writing `current`.
- [`_test`, `_suite`, `_global` and the `set_*` methods are Robot Framework internals] → the debugger already reads the first three to fill the Variables view, and the methods' signatures were checked in 5.0 and 7.5; a test runs the scenarios across the Robot Framework matrix.
- [Setting under Test or Suite also overwrites a same-named local of the paused keyword] → that is Robot Framework's own behaviour for `Set Test Variable` and `Set Suite Variable`, and the spec says the chain gets the value; the design doc of the IntelliJ follow-up can decide whether to warn.
- [VS Code sends `setExpression` for Set Value on a watch, but `setVariable` for variables listed under a watch's expansion] → both paths end in the same implementation; items are refused on both.

## Open Questions

- Whether the IntelliJ plugin lifts its "innermost Local only" restriction in the same release or later; it changes `intellij-debugging`, not this change.
- Whether `robotcode robot-debug`'s `.set` should adopt the same scope rule and expression evaluation (today: selected frame only, literal strings); it changes `repl-*` specs, not this change.
