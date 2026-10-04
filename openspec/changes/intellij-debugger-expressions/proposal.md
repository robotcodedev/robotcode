# Proposal

## Why

In PyCharm and IntelliJ IDEA, everything around debugger expressions lags behind VS Code:

- Typing in the Evaluate dialog or a watch fills `idea.log` with errors, about three per second, and raises an "IDE error occurred" balloon. The editors offer no completion and show plain grey text.
- Hovering a variable while the run is paused shows nothing.
- There is no debug console: keywords can be run only one at a time through the Evaluate dialog, without a history.
- Robot Framework line breakpoints have no Condition and no "Evaluate and log" field, and no hit count. The settings IntelliJ offers for every breakpoint, such as suspend policy None, the "Breakpoint hit" message and "Remove once hit", have no effect, because the plugin never tells the IDE which breakpoint was hit.
- There is no exception breakpoint for failed tests.

Hit counts and failed-test stops also need two fixes in the RobotCode debugger, which the change `debugger-dap-e2e-tests` makes before this one.

## What Changes

- The Evaluate dialog, watches, breakpoint conditions, log expressions and the new debug console accept input without logging errors, and complete the keywords, libraries, resources and variables the paused run knows.
- Hovering a variable in a Robot Framework file while the run is paused shows its value. Hover values never run keywords.
- A "Robot Debug Console" tab in the Debug tool window runs keywords and shows variables in the selected frame while the run is paused, with a history of the entered lines.
- Robot Framework line breakpoints get a Condition, "Evaluate and log" and a hit count:
  - the condition is a Python expression in which Robot Framework variables are replaced, for example `${i} == 3`;
  - the hit count N stops the run only the N-th time it reaches the line;
  - with Suspend off, the log text is a Robot Framework template such as `value is ${i}`, which the debugger writes to the run's output each time the line is reached, as with VS Code's logpoints. With Suspend on, the log text is evaluated like a watch when the run stops there.
  Conditions, log texts and hit counts are saved with the project's breakpoints.
- When the run stops at a line breakpoint, the IDE applies that breakpoint's settings: suspend policy, "Breakpoint hit" message, stack trace, "Remove once hit" and breakpoints that wait for another breakpoint.
- A "Failed Tests" exception breakpoint, disabled by default, stops the run when a test fails.

Not part of this change: inline variable values in the editor; conditions on exception breakpoints, which the debugger does not evaluate; changing values through expressions.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-debugging`: expression editing and completion, hover values, the Robot debug console, breakpoint conditions, log messages and hit counts, breakpoint actions, and the failed-tests exception breakpoint.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/debugging/RobotCodeXDebuggerEditorsProvider.kt`: fragments for the expression editors.
- A completion contributor and the debug console classes in `debugging/`.
- `debugging/RobotCodeDebuggerEvaluator.kt` and `lsp/RobotCodeServerApi.kt`: hover through the language server request `robot/debugging/getEvaluatableExpression`.
- `debugging/RobotCodeDebugProcess.kt`: the console tab, breakpoint ids, `breakpointReached` and the log text of suspending breakpoints.
- `debugging/breakpoints/`: the editors provider and hit count of the line breakpoint type, property persistence, and the failed-tests exception breakpoint type.
- `src/main/resources/META-INF/plugin.xml` and `messages/RobotCode.properties`: the contributor, the console history type, the new breakpoint type and texts.
- New unit tests under `intellij-client/src/test/kotlin/`.
- Requires `debugger-dap-e2e-tests` (Python debugger) to have landed. No change to the language server or the VS Code extension.
