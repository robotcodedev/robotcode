# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- **Expression fragments** (`debugging/RobotCodeXDebuggerEditorsProvider.kt`): `createExpressionCodeFragment` ignores `isPhysical` and creates an in-memory Robot Framework file with the event system off, although the platform's `createDocument` asks for a physical fragment. Robot Framework files get their PSI from `RobotCodeTokensFileViewProviderFactory`, LSP4IJ's semantic-token view provider, in-memory files included. In runtime check Q50 typing in the Evaluate dialog caused one SEVERE `TextEditorBackgroundHighlighter` entry about that view provider ("eventSystemEnabled=false … isInUncommittedSet:true") and then about three repetitions per second while the dialog was open; LSP4IJ sent nothing for the fragment, and the text stayed grey. No completion contributor exists.
- **Hover:** `RobotCodeDebuggerEvaluator` does not override `getExpressionInfoAtOffsetAsync`, so the platform finds no expression under the mouse. The language server answers `robot/debugging/getEvaluatableExpression` with `{textDocument, position}` by returning the range and name of the variable at that position, or `null` (`language_server/.../parts/debugging_utils.py`). `RobotCodeServerApi` is the plugin's interface for such requests, as `clearCache` shows.
- **Console:** the debug tab shows only the run's test console; `XDebugProcess.createTabLayouter()` is not overridden. The planned Robot Log tab change overrides it as well; whichever of the two changes lands first creates the override, and the other adds its tab to it.
- **Line breakpoint type** (`debugging/breakpoints/`): it provides no editors provider, so the breakpoint popup and dialog show no Condition and no "Evaluate and log" field (Q47). In 2026.1 the one-argument `XBreakpointType.getEditorsProvider()` is deprecated; `getEditorsProvider(B, Project)` is not. Both properties classes throw from `loadState`, which is harmless only while they have no fields.
- **Stops at line breakpoints** end in `positionReached`, so the IDE never applies a breakpoint's suspend policy or actions (Q47: suspend None still stopped, "Remove once hit" kept the breakpoint).
- **The debugger** (`debugger.py`): it evaluates a breakpoint's condition first, as a Python expression after replacing Robot Framework variables, and does not stop when it is false; then it counts hits for the hit condition; a breakpoint with a log message replaces the variables in it, sends the text as output with source and line, and never stops. A stop carries `hitBreakpointIds`, the ids that the latest `setBreakpoints` response gave the breakpoints of that line; every request assigns new ids. `completions` returns the libraries, resources and their keywords, and the variables of the frame, whatever the text and column, and nothing while the debugger's expression mode is on. A REPL line `# exprmode` toggles that mode.
- **`debugger-dap-e2e-tests` (decision D5, planned to land before this change, not implemented yet):** it makes the debugger accept the `failed_test` filter and stop with "Test failed…", and makes a hit condition N stop exactly on the N-th hit. Its scenarios "Failed test" and "Hit condition" are the debugger-side acceptance tests this change relies on.
- **Builds on planned changes, not implemented yet:** `intellij-async-run-and-debug` makes the evaluator asynchronous, adds request timeouts and maps the evaluation origin to the DAP context, with `EDITOR` mapped to `hover`. `intellij-debugger-breakpoints` adds the breakpoint bookkeeping class, the exception breakpoint types with their common base and the mapping of exception stops by description.

## Goals / Non-Goals

**Goals:**

- Every expression the user types in the debugger is edited and completed as Robot Framework, without errors.
- The IDE's own breakpoint settings work for Robot Framework line breakpoints wherever the debugger stops.

**Non-Goals:**

- Inline values in the editor.
- Conditions on exception breakpoints; the debugger declares them but never evaluates them.
- Language server features, such as diagnostics, inside expression fragments.

## Decisions

### Physical fragments, checked first

`createExpressionCodeFragment` honours `isPhysical` and creates the fragment with the event system enabled when asked for a physical one; the platform's `PsiFileFactory.createFileFromText` overloads take that flag. That this removes the SEVERE entries is a hypothesis from the analysis, so task 1.2 checks it with the Q50 setup, together with whether LSP4IJ starts talking to the server about the fragment. If the errors remain, `RobotCodeTokensFileViewProviderFactory` returns the platform's default view provider for these in-memory Robot Framework files, so they no longer depend on LSP4IJ's semantic tokens. If LSP4IJ attaches to the fragment, the plugin excludes such files through LSP4IJ's per-file client feature switch.

### One completion contributor for fragments and the console

A completion contributor for the Robot Framework language acts only in files that the editors provider or the console has marked with a user data key. It asks the debug process of the current session for DAP `completions` in the selected frame and turns each item into a lookup element with its label, an icon for its kind (keyword, variable, library or resource) and its detail as tail text. The platform's prefix matcher filters the list, because the debugger ignores the text it gets. Completion runs in the background; the request waits with a bound and stops when completion is cancelled.

Alternative: let the language server complete in the fragment. The server knows the document's static context, not the paused run's variables and imported libraries, and LSP4IJ does not serve in-memory fragments.

### Hover through the language server's evaluatable expression

The evaluator overrides `getExpressionInfoAtOffsetAsync`: it sends `robot/debugging/getEvaluatableExpression` through a new request method on `RobotCodeServerApi`, with the file URI as LSP4IJ reports it to the server and the position of the offset, and resolves the promise with the returned range and expression, or with `null`. The platform then evaluates the expression with the origin `EDITOR`, which the evaluator maps to the `hover` context, so a hover never runs a keyword.

### A Robot debug console tab built from the platform's console parts

`createTabLayouter()` returns a layouter whose `registerAdditionalContent` adds a "Robot Debug Console" tab. The console is a `LanguageConsoleImpl` for the Robot Framework language, with a `ConsoleExecuteAction` and a `BaseConsoleExecuteActionHandler`, and a `ConsoleHistoryController` with the plugin's own `ConsoleRootType`, registered as a scratch root type. The history controller's constructor with a plain string id is deprecated and internal in 2026.1, and `LanguageConsoleBuilder` is experimental, so neither is used. Executing a line evaluates it in the `repl` context with the frame selected in the session, and prints the result or the debugger's error message. While the session is not suspended, the handler prints that the run is not paused, because the debugger runs keywords only for a paused run and would otherwise wait for its 60-second limit.

Alternative: rely on the Evaluate dialog alone. It has no history and closes after each evaluation, while VS Code users keep a console open while paused.

### Breakpoint properties, editors provider and hit count

`loadState` of both properties classes copies the stored bean (`XmlSerializerUtil.copyBean`) before the line breakpoint properties get their first field, the hit count. The line breakpoint type overrides `getEditorsProvider(breakpoint, project)` with the expression editors provider, which makes the platform show the Condition and "Evaluate and log" fields, and `createCustomConditionsPanel` with a hit count field. That panel also carries a short comment on what the log text means with and without Suspend.

### What is sent for a line breakpoint

- `condition`: the breakpoint's condition expression, when enabled.
- `hitCondition`: the hit count, when set.
- `logMessage`: the log expression, only when the suspend policy is None. The debugger then writes the template to the output and never stops, which is the logpoint behaviour VS Code users know.

With a suspending policy, the log expression is not sent. When the run stops at the breakpoint, the debug process evaluates the expression in the `watch` context and passes the result, or the error message, to `breakpointReached`, which logs it.

The two meanings differ because the debugger replaces variables in a log message only for log points, which never stop, and no evaluation context of the debugger expands a template: `watch` evaluates the text as a Python expression after replacing variables, `repl` runs it as a keyword. A single variable such as `${i}` gives the same value in both modes.

Alternatives:

- Evaluate every log text in the IDE, stopping the run at each hit and resuming it: one meaning and every IDE action for every breakpoint, but templates such as `value is ${i}` would fail, and each hit would cost a stop, a stack request, an evaluation and a resume.
- Always send the log text as a log message: breakpoints with Suspend on would never stop.
- Wrap the template in a Python string literal for the `watch` context: values that contain quotes or backslashes would break the literal.

### `breakpointReached` through the hit ids

The breakpoint bookkeeping keeps, per file, the ids from the latest `setBreakpoints` response, in request order. A stop with reason `breakpoint` looks up the breakpoint for its `hitBreakpointIds` and calls `breakpointReached`; when that returns `false`, the debug process continues the run. A stop whose ids match no registered breakpoint, such as the temporary Run to Cursor entry or a stop that raced with a new request, ends in `positionReached` as today.

### A "Failed Tests" exception breakpoint

A fourth exception breakpoint type on the common base, filter `failed_test`, disabled by default. Stops with the description "Test failed." map to it. It relies on the debugger fix from `debugger-dap-e2e-tests`; before that fix, the debugger rejects the filter.

## Risks / Trade-offs

- [The fragment fix is a hypothesis] → Task 1.2 checks it before anything builds on it, and the fallback is decided above.
- [The log text means a template without Suspend and an expression with Suspend] → The hit count panel states it, and a single variable works the same in both.
- [A log breakpoint with suspend None never reaches the IDE, so its "Breakpoint hit" message, stack trace, "Remove once hit" and dependent breakpoints do not apply] → The same holds for VS Code's logpoints; every breakpoint that stops, and every non-suspending breakpoint without a log text, gets all actions.
- [`# exprmode` switches the debugger's REPL lines to expressions for every later evaluation, and its completion then returns nothing] → This is the debugger's behaviour in VS Code as well; entering `# exprmode` again switches it back.
- [`debugger-dap-e2e-tests` has not landed when this change is implemented] → Task 1.1 checks it first; the hit count and the "Failed Tests" breakpoint must not ship without it.

## Migration Plan

None. Breakpoints stored by earlier versions have no properties, so they load unchanged.
