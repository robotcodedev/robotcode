# Proposal

## Why

When a Robot Framework run is paused in PyCharm or IntelliJ IDEA, the Variables and Frames views show much less than in VS Code:

- A list variable such as `@{items}` expands only to `len()`; its items cannot be seen. Large values are fetched in one piece, and the variables of every scope are fetched at each stop, whether the user looks at them or not.
- Variables cannot be changed: Set Value is not offered.
- Frames show only `file:line`, such as `sample.robot:15`, not the keyword, test or suite they belong to.
- Groups and values the user expanded, such as the Suite and Global variables, collapse again after every step.
- Types are shown as `{<class 'str'>}`.

## What Changes

- Lists expand into their items, in pages of 100 with an entry that loads the next page. Dictionaries expand into their entries. The Test, Suite and Global groups load their variables only when they are expanded.
- Set Value (F2) changes a variable of the paused keyword or test. The new value is written as the debugger evaluates it: a Python expression in which Robot Framework variables are replaced, for example `'changed'` or `${count} + 1`. An invalid value shows the debugger's error message.
- Frames show the keyword, test or suite name, followed by the file and line in grey. Frames without a source file, such as a directory suite, are dimmed. Selecting a frame opens the source at the right line and column.
- Groups and values the user expanded stay expanded after a step, as long as the run stays in the same keyword, test or suite.
- Types are shown by their Python name, such as `str`, `list` or `DotDict`.

Not part of this change: changing variables of outer frames, of the Test, Suite and Global groups, or items inside lists and dictionaries, because the debugger would assign such a value in the paused keyword's own scope; inline values in the editor; evaluation, hover values and a debug console.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-debugging`: expandable list and dictionary variables with paging, Set Value, frame names, and expanded variables that stay expanded across steps.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/debugging/RobotCodeStackFrame.kt`, `RobotCodeNamedValue.kt`, `RobotCodeValueGroup.kt`, `RobotCodeExecutionStack.kt`, `RobotCodeSuspendContext.kt`: children and paging, the value modifier, frame presentation, equality and caching.
- `execution/RobotCodeRunProfileState.kt`: the client capability for variable paging in the `initialize` request.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the RobotCode debugger, the language server or the VS Code extension.
