# Proposal

## Why

The Breakpoints dialog of PyCharm and IntelliJ IDEA shows the Robot Framework exception breakpoints as four groups, "Robot Framework Uncaught Failed Keywords", "Robot Framework Failed Keywords", "Robot Framework Failed Tests" and "Robot Framework Failed Suites", each holding one breakpoint. `intellij-debugger-breakpoints` made each kind of failure its own breakpoint type, and the dialog always groups breakpoints by type. Other exception breakpoints, such as PyCharm's Python exception breakpoints, form one group in which the user adds the exceptions to stop at. The four types are on `main` but in no release yet, so they can still be merged without migrating stored settings.

## What Changes

- The Robot Framework exception breakpoints form one group, "Robot Framework Exception Breakpoints".
- The group holds "Uncaught Failed Keywords", enabled by default. Like every default breakpoint of the IDE, it can be disabled but not removed, and it keeps the settings stored for the exception breakpoint of earlier plugin versions.
- The dialog's add button adds "Failed Keywords", "Failed Tests" or "Failed Suites" to the group, each at most once. An added kind has its own enabled state, suspend policy and log options, and can be removed again.
- What each kind stops at, and how a stop applies its breakpoint's settings, stay as they are.
- Settings that builds of `main` since 2026-10-11 stored for the separate "Failed Keywords", "Failed Tests" and "Failed Suites" breakpoints are not carried over; v2.7.0 and earlier releases had only the former "Any Exception" breakpoint.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-debugging`: the requirement "Exception breakpoints per kind of failure" changes from one breakpoint per kind, all always present, to one group with "Uncaught Failed Keywords" and kinds the user adds.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/debugging/breakpoints/`: one exception breakpoint type instead of four, its properties with the kind, the add button, and one handler.
- `debugging/RobotCodeDebugProcess.kt`: one exception breakpoint handler, and the filter of a breakpoint read from its properties.
- `src/main/resources/META-INF/plugin.xml` and `messages/RobotCode.properties`: one registered type and its texts.
- New and changed unit tests under `intellij-client/src/test/kotlin/`.
- No change to the RobotCode debugger, the language server or the VS Code extension.
- Follows `intellij-debugger-expressions`, which changes `RobotCodeDebugProcess.kt` as well.
