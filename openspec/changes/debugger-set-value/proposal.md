# Proposal

## Why

While a run is paused, VS Code's Variables view offers Set Value for every variable under Local, Test, Suite and Global, and its Watch view offers it for watch expressions, because the RobotCode debugger advertises `supportsSetVariable` and `supportsSetExpression`. Neither does what the views promise (#671): `setVariable` always writes into the innermost scope at the stop, so a variable edited under Test, Suite or Global, or under an outer frame, keeps its old value where it is shown; and `setExpression` has no handler at all, so Set Value on a watch expression ends with an error.

## What Changes

- Set Value changes the variable in the scope it is shown under. Under Local of a frame it changes that frame's own variables. Under Test, Suite and Global it sets the variable the way Robot Framework's `Set Test Variable`, `Set Suite Variable` and `Set Global Variable` do, so the scopes between the paused keyword and the target scope, which Robot Framework creates as copies, get the new value too.
- Set Value never creates a variable: a name that does not exist in the target scope is rejected with an error message, as it is today for the innermost scope.
- Set Value on a watch expression works for a whole variable (`${name}`, `@{name}`, `&{name}`) and changes it in the selected frame's own variables. Any other expression, including item access such as `${list}[0]`, is rejected with a message that says what can be set.
- Unchanged, and now written down: the entered value is evaluated as the debugger evaluates expressions, a Python expression in which Robot Framework variables are replaced first, so strings need quotes; and Set Value on items of lists and dictionaries stays unsupported and keeps its error.

Not part of this change: the command-line debugger `robotcode robot-debug` and its `.set`, which has its own implementation (it writes the selected frame only and stores strings) and could follow the same scope rules later; and the IntelliJ plugin, which offers Set Value only in the Local scope of the innermost frame and can lift that restriction once the debugger behaves this way.

## Capabilities

### New Capabilities

- `debugger-set-value`: how the RobotCode debugger changes a variable's value on a client's `setVariable` or `setExpression` request: which scope it writes, that it never creates a variable, how it interprets the entered value and what it rejects.

### Modified Capabilities

_None._ The Set Value requirements of `intellij-debugging` describe the plugin's own restriction and stay as they are.

## Impact

- `packages/debugger/src/robotcode/debugger/debugger.py`: `set_variable` picks the target scope from the variables reference that matched (Local, Test, Suite or Global) instead of always writing `context.variables.current`, and uses Robot Framework's `VariableScopes.set_test`, `set_suite` and `set_global` for the shared scopes; a new `set_expression` for watch expressions.
- `packages/debugger/src/robotcode/debugger/server.py`: a `setExpression` request handler; `dap_types.py`: its argument and response types. The launcher forwards the request to the debuggee like every request it does not handle itself, so `launcher/server.py` does not change.
- `packages/debugger/src/robotcode/debugger/default_capabilities.py`: `supportsSetExpression` stays advertised and becomes true in fact.
- New tests under `tests/robotcode/debugger/`.
- `docs/src/content/docs/guides/vscode/running-and-debugging.mdx`: a sentence on changing variables while paused.
- No change to the messages VS Code or the IntelliJ plugin send; both get the new behaviour through the debugger.
