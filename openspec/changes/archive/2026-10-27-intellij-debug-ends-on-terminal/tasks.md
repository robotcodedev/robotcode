# Tasks

## 1. "Terminal" at the end of a debug session (design D1)

- [x] 1.1 In `addTerminalContent` (`RobotCodeRunnerConsoleView.kt`), register the "Terminal" tab also for `XDebuggerUIConstants.LAYOUT_VIEW_FINISH_CONDITION` with `LayoutAttractionPolicy.FocusOnce()`, next to the registration for `STARTUP`, and adjust the comment. Verify with a test in `RobotCodeRunnerConsoleViewTest`: in a layout that has the platform's attractions of a debug console (as `DebuggerSessionTabBase` sets them) and a console content, after `addTerminalContent`, `attractBy(LAYOUT_VIEW_FINISH_CONDITION)` selects the "Terminal" tab (passes with the change, fails without it). Run `(cd intellij-client && ./gradlew test)` and `(cd intellij-client && ./gradlew verifyPlugin)`, which reports no new use of internal API.

## 2. Check in the harness

- [x] 2.1 In the PyCharm harness (UI-test PyCharm 2026.1, demo project), before and after the change: with the selection `typo`, a debug run of `tests/orders.robot` ends with the "Terminal" tab selected, which shows `Error: No profile matches 'typo'.`; without a selection, a debug run that runs its tests ends with the "Terminal" tab selected; a run still ends with the "Terminal" tab selected.

## Workflow follow-up

- Tick J16 in `playground/pycharm-befunde.md` after the commit.
- Archive the change after review.
