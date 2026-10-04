# Proposal

## Why

In PyCharm and IntelliJ IDEA, Robot Framework breakpoints do not always behave as the editor shows them:

- Removing, disabling or muting the last breakpoint of a file never reaches the debugger, so the run keeps stopping at a line without a breakpoint. Force Step Over stops there as well.
- Moving a breakpoint, by dragging it or by editing lines above it, leaves an invisible breakpoint at the old line.
- Run to Cursor onto a line that already has a breakpoint shows the session as running while Robot Framework stays paused; only Pause recovers it.
- Breakpoints are sent while the run is already being started, so a breakpoint on one of the first keywords can be missed.
- Exception breakpoints never reach the debugger, which keeps using its own default, "uncaught failed keywords", whatever the IDE shows. If the user switches off the IDE's exception breakpoint, the next failure stops Robot Framework without the IDE noticing: the run hangs, and Stop cannot end it. The breakpoint's label "Any Exception" is wrong as well, because failures caught by `TRY/EXCEPT` or by keywords such as `Run Keyword And Ignore Error` never stop.
- Robot Framework line breakpoints can be set in any file, including Python, plain text and TOML files (#658; in Rider they take over C# files).

## What Changes

- Disabling, muting, removing and moving a breakpoint take effect at once in a running session, also for the last breakpoint of a file. Force Step Over and Force Run to Cursor ignore all breakpoints, as the IDE promises.
- Run to Cursor always continues the run and stops at the target line, also when that line has a breakpoint.
- The breakpoints and exception breakpoints that exist when a session starts are in effect before Robot Framework runs its first keyword.
- Run | View Breakpoints offers three Robot Framework exception breakpoints, matching the failures the debugger can stop on today: "Uncaught Failed Keywords" (enabled by default; it keeps the settings of the former "Any Exception" breakpoint), "Failed Keywords" (every failing keyword, also caught ones) and "Failed Suites". The debugger stops only at the enabled ones, each with its own suspend policy, and shows the failure message when it stops. With all of them disabled, failing tests run through without stopping.
- Robot Framework line breakpoints are offered only in `.robot` and `.resource` files; Python and other files keep their own breakpoints.

Behaviour that users notice, for the release notes (not breaking): the former "Any Exception" breakpoint is now called "Uncaught Failed Keywords", which is what it always did.

Not part of this change: breakpoint conditions, log messages and hit counts; the "Breakpoint hit" message, "Remove once hit" and breakpoints that depend on others; an exception breakpoint for failed tests; conditions on exception breakpoints; starting a session without blocking the IDE, and reporting a debugger that never connects.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-debugging`: breakpoints take effect as shown, Run to Cursor, breakpoints in effect from the first keyword, exception breakpoints per kind of failure, and where Robot Framework breakpoints can be placed.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/debugging/RobotCodeDebugProcess.kt`: breakpoint bookkeeping, Run to Cursor, exception breakpoints and the stop handling.
- `execution/RobotCodeRunProfileState.kt` and `debugging/RobotCodeDebugProtocolClient.kt`: the order of the debugger handshake and the `initialized` event.
- `debugging/breakpoints/`: the line breakpoint type and three exception breakpoint types with their handlers.
- `src/main/resources/META-INF/plugin.xml` and `messages/RobotCode.properties`: the new types and their texts.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the RobotCode debugger, the language server or the VS Code extension.
