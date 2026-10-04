# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- **Frames and scopes** (`debugging/RobotCodeStackFrame.kt`): `computeChildren` requests the scopes, picks the Local scope with `first { … }`, which throws when a frame has none, shows its variables inline, and fetches the variables of every other scope right away to hand them to `RobotCodeValueGroup`. `customizePresentation` falls back to the platform default, `file:line`, whenever a frame has a source. The DAP column, which starts at 1, goes unchanged into `createPosition`, which counts from 0. `RobotCodeExecutionStack` and `RobotCodeSuspendContext` create new frame objects on every call, and no frame overrides `getEqualityObject()`.
- **Values** (`RobotCodeNamedValue.kt`): children are requested without a filter. `getModifier()` is not overridden. A variables cache is read but never filled. The type is passed as the debugger sends it, `<class 'str'>`, which the platform shows in braces. The `initialize` request sets `supportsVariablePaging = false`.
- **What the debugger returns** (`packages/debugger/src/robotcode/debugger/debugger.py`):
  - a list has one named child (`len()`) and one indexed child per item; without a filter only `len()` is returned; the `indexed` filter with `start` and `count` pages correctly;
  - a dictionary has its entries plus `len()` as named children and no indexed children; without a filter it returns `len()` and at most 500 entries followed by a marker entry; the `named` filter ignores `start`, it only renumbers;
  - the variables of a scope are returned completely without a filter;
  - scopes: Local, Test (only for frames inside keywords), Suite and Global; no scopes for a frame without an execution context;
  - `setVariable` accepts only a variable directly in a scope, evaluates the value as a Python expression after replacing Robot Framework variables, and always assigns it in the innermost variable scope of the run, whichever scope the variable was shown in;
  - stack frames carry the keyword, test or suite name, the presentation hint `subtle` when they have no source file, and the column; two frames of one stack entry can share an id.
- **Runtime:** list variables expanded only to `len()` (Q51); expanded Suite and Global groups and a nested dictionary collapsed after Step Over within the same test frame (Q53); frames read `sample.robot:15`, `sample.robot:13`, `sample.robot:1`, `Project.Tests`, `Project` (runtime check 7e).
- **Platform API** (2026.1): `XCompositeNode.tooManyChildren(int, Runnable)`, with `MAX_CHILDREN_TO_SHOW = 100`; the overload without the `Runnable` is deprecated. `XValue.getModifier()` and `XValueModifier.setValue(XExpression, XModificationCallback)`; the `String` overload is deprecated. `XStackFrame.getEqualityObject()` returns `null` by default, and the Variables view uses it to keep its expansion state between stops (from the analysis).
- **Builds on a planned change, not implemented yet:** `intellij-async-run-and-debug` makes `computeChildren` asynchronous in the run's coroutine scope, with request timeouts. This change uses that path; it does not add waits of its own.

## Goals / Non-Goals

**Goals:**

- Request only what the user looks at, in the form the debugger handles correctly.
- Offer Set Value only where the debugger assigns the value where the user sees it.

**Non-Goals:**

- Fixing the debugger's `named` paging or its assignment scope. Both fixes are planned in the Python change `debugger-dap-e2e-tests` and affect VS Code too. Once it has landed, Set Value can be offered in every scope and dictionaries can be paged with `named`; that widening is a follow-up, not part of this change.
- Inline values in the editor.
- Value renderers or "View as" actions.

## Decisions

### Children are requested by kind

- A value with indexed children (a list) requests its named children once, which gives `len()`, and its items with the `indexed` filter in pages of 100. When more items remain, `tooManyChildren(remaining, loadNextPage)` offers them.
- A value without indexed children (a dictionary or another container) requests its children without a filter. The debugger then returns `len()` and up to 500 entries, so no paging is needed, and the `named` filter, which ignores `start`, is never used with an offset.
- A scope requests its variables without a filter.

The decision is a small pure function of the counts the debugger sends, so JUnit tests cover it. The `initialize` request sets `supportsVariablePaging = true`.

Alternative: page dictionaries with `named`, `start` and `count`. The debugger ignores `start`, so every page after the first would repeat the first entries.

### Scope groups load lazily, Local stays inline

The frame requests the scopes, shows the Local variables inline as today and adds the other scopes as bottom groups that request their variables when expanded. A frame without a Local scope shows only its groups; a frame without scopes shows nothing and reports no error.

### Set Value only for the Local scope of the innermost frame

`getModifier()` returns a modifier only for a variable that is a direct child of the Local scope of the innermost frame. The modifier sends `setVariable` with the scope reference, the name and the expression text, and reports `valueModified()` on success, after which the platform rebuilds the Variables view, or `errorOccurred` with the debugger's message. Its initial editor text is the current value as the debugger shows it, which is already a valid Python expression for strings, numbers, lists and dictionaries.

The debugger assigns every value in the innermost variable scope. For a variable shown in the Suite or Global group, or in the Local scope of an outer frame, the change would only shadow the variable in the paused keyword, while the group would keep showing the old value. So the modifier is not offered there.

Alternatives:

- Offer Set Value for every scope child, as VS Code does: in the cases above, the view would contradict the change.
- Fix the debugger's assignment scope first: a change to the Python debugger, outside this change; once it lands, the modifier can be offered for the other scopes as well.

### Frames show their name, and keep their identity across stops

`customizePresentation` renders the frame name and then `file:line` in the grey text attributes; a `subtle` frame is rendered in grey as a whole. The source position uses the DAP column minus one. The execution stack creates its frames once per suspend context and returns the same objects for the top frame and the frame list.

`getEqualityObject()` returns the frame name, the source path and the frame's distance from the bottom of the stack. The line is left out on purpose: after a step in the same test, the line has changed, but the platform should restore the expansion state. The distance from the bottom tells apart the two frames that one stack entry can produce, and repeated calls of the same keyword at different depths.

Alternative: name, source and line, as the analysis suggested: the state would be lost after every step within the same test, which is the defect Q53 shows.

### Python type names

The type string `<class 'robot.utils.dotdict.DotDict'>` is shortened to the part after the last dot, `DotDict`; other strings are shown as they are.

## Risks / Trade-offs

- [The debugger cuts dictionaries after 500 entries] → Its marker entry says so; the same limit applies in VS Code.
- [A restored expansion state requests the children of every expanded node at the next stop] → That is what the user asked to see; the requests run in the background.
- [Equal frames at the same depth in different calls of a keyword restore each other's state] → The variable names of a keyword are usually the same in each call, so the restored state fits.
- [Set Value is narrower than in VS Code] → It is offered where the debugger's assignment matches what the view shows.

## Migration Plan

None.
