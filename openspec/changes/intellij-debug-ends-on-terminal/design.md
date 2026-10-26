# Design: intellij-debug-ends-on-terminal

## Context

See proposal.md - Why. In the platform sources at the tag `pycharm/261.22158.340`, the build of the harness IDE:

- `DebuggerSessionTabBase` gives the console of a debug window two attractions: it comes to the front at `LayoutViewOptions.STARTUP` with `FocusOnce(false)`, and at `XDebuggerUIConstants.LAYOUT_VIEW_FINISH_CONDITION` (`"finish"`) with `FocusOnce()` (`platform/xdebugger-impl/ui/src/com/intellij/xdebugger/impl/ui/DebuggerSessionTabBase.java`, lines 50-53).
- `XDebugSessionTab.sessionStopped()` calls `attractBy(LAYOUT_VIEW_FINISH_CONDITION)` when a session ends (`XDebugSessionTab.java`, line 330).
- The console of a RobotCode debug session is the results tree, which the plugin names "Debug Console". `addTerminalContent` (`RobotCodeRunnerConsoleView.kt`) registers the "Terminal" tab for `STARTUP`, which replaces the console's attraction for the start, since the window keeps one content per condition. It registers nothing for `"finish"`, so the console keeps that attraction.
- A run window never fires `"finish"`; there the tab that is in front stays when the run ends.
- `XDebuggerUIConstants` is a public class in `com.intellij.xdebugger.impl.ui` without an `@ApiStatus` annotation.

## Goals / Non-Goals

**Goals:**

- Every debug session ends with the "Terminal" tab in front, as a run does.

**Non-Goals:**

- Showing the output of the process in the "Debug Console" as well.
- Changing what a stop at a breakpoint brings to the front.

## Decisions

### D1: The "Terminal" tab takes the console's attraction for the end of a session

`addTerminalContent` registers the "Terminal" tab also for `XDebuggerUIConstants.LAYOUT_VIEW_FINISH_CONDITION`, next to the registration for `STARTUP`, with the policy that the platform gives its console for that condition, `LayoutAttractionPolicy.FocusOnce()`. The "Terminal" tab is where the output of the process is, which the platform's console shows in other debug sessions, so it takes the console's place at the end as it does at the start.

- **Alternative:** bring the "Terminal" tab to the front only when the process ends before Robot Framework starts. It needs to know whether a run started, and a normal debug session would still end differently from a run; rejected.
- **Alternative:** also write the output of the process before Robot Framework starts to the "Debug Console". The error is in the "Terminal" tab already, so this would show it twice; rejected.
- **Alternative:** the literal `"finish"` instead of the platform's constant. The constant is public and not marked internal, and a renamed condition would then fail at compile time; `verifyPlugin` confirms that its use is reported nowhere.

## Risks / Trade-offs

- [Users who look at the results tree after a debug session now find the "Terminal" tab in front] → As after a run; the "Debug Console" tab is one click away.
- [The platform could change the condition's name or the console's attraction in a later version] → The constant follows a rename; a later version that drops the attraction makes the registration unused, not wrong.
