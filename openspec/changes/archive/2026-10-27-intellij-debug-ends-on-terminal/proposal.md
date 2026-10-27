# Proposal: intellij-debug-ends-on-terminal

## Why

When a debug session ends, PyCharm brings the "Debug Console" tab to the front, the results tree, also when the run ended before Robot Framework started (J16 of the PyCharm findings). Checked on 2026-10-26 on `main` in the harness (PyCharm 2026.1, demo project, a selection that names the profile `typo`, which `robot.toml` does not define):
- A run of `tests/orders.robot` ends with the "Terminal" tab in front, which shows `Error: No profile matches 'typo'.` and the exit code 252.
- A debug run ends with the "Debug Console" tab in front. It shows only "Test framework quit unexpectedly" and the exit code; the error is only in the "Terminal" tab.

The platform's debug window brings its console to the front when a session starts and when it ends. The plugin makes the "Terminal" tab take the console's place at the start, but not at the end.

## What Changes

- A debug session ends with the "Terminal" tab in front, as a run does, also a debug session whose tests ran normally. An error that stops the session before Robot Framework runs is then in view.
- The "Debug Console" keeps its content; the output of the process stays in the "Terminal" tab only.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `intellij-test-results`: the requirement "Debug sessions show the "Terminal" tab" also selects the "Terminal" tab when the session ends.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeRunnerConsoleView.kt`: `addTerminalContent` registers the "Terminal" tab also for the end of a debug session.
- Tests: `intellij-client/src/test/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeRunnerConsoleViewTest.kt`.
- Docs: none; the PyCharm guide does not say which tab is in front when a session ends.
- Users: after a debug session, the "Terminal" tab is in front instead of the "Debug Console"; the results tree is one click away, as after a run.
