# Proposal

## Why

In PyCharm and IntelliJ IDEA, every log message of a Robot Framework run is printed into the run console, between the output of the Robot Framework process (issue #528). A test that calls `Log    should not in console` and `Log To Console    show in console` shows both lines in the console, while a terminal run shows only the second: `Log` writes to the log file, not to the console. With a lower log level, the console fills up with the arguments and return values of every keyword. VS Code keeps these messages in its Debug Console, apart from the terminal that shows the process output. The plugin had no such place, so the messages went into the console as a workaround.

## What Changes

- Every Robot Framework run gets a "Robot Log" tab in its run window, next to the console. It lists the log messages that RobotCode sends for the run, in the order they were logged:
  - messages of `Log` and of other keywords that log, as far as the run's log level lets them through, and Robot Framework's own warnings and errors;
  - each with its level, except for `INFO`, and colored by level;
  - each with a link at its end to the file and line it was logged from, where RobotCode reports one.
- The console shows only what the Robot Framework process writes, as a terminal run does: for example the text of `Log To Console`, the test status lines, and the `[ WARN ]` and `[ ERROR ]` lines that Robot Framework writes for warnings and errors. Log messages no longer appear in the console, neither for the run nor under a test.
- Debug sessions show the same "Robot Log" tab next to their Console and Debugger tabs, with the same messages.

Behaviour that users notice, for the release notes (not breaking): Robot Framework's log messages move from the console to the new "Robot Log" tab, and the console looks like a terminal run (#528).

Not part of this change: switching the log messages off, adding the rest of Robot Framework's system messages, or timestamps; filtering the "Robot Log" tab by test; showing log messages in the results tree.

## Capabilities

### New Capabilities

- `intellij-test-results`: the "Robot Log" tab of Robot Framework runs and what the run console shows. The capability has no main spec yet; this change adds these requirements to it.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotOutputToGeneralTestEventsConverter.kt`: DAP output events go to the "Robot Log" console instead of the results tree.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeRunnerConsoleView.kt`: owns the "Robot Log" console and adds its tab to the run window.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/debugging/RobotCodeDebugProcess.kt`: adds the tab to the debug session window.
- A new formatter for log lines in `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/`.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the tab title.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to robotcode, the language server, the VS Code extension or `robot.toml`.
