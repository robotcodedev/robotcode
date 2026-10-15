# Proposal

## Why

In PyCharm and IntelliJ IDEA, every log message of a Robot Framework run is printed into the run console, between the output of the Robot Framework process (issue #528). A test that calls `Log    should not in console` and `Log To Console    show in console` shows both lines in the console, while a terminal run shows only the second: `Log` writes to the log file, not to the console. With a lower log level, the console fills up with the arguments and return values of every keyword. At the same time, what the console shows under a test depends on Robot Framework's console options: with `console = "none"`, the process writes nothing for a test, with `dotted` a single dot. VS Code shows the log messages of a test in its test results, whatever the console options are, and the process output in a terminal of its own.

## What Changes

- Selecting a test in the results tree shows the log messages that the RobotCode debugger sent while the test ran, in the order they were logged:
  - messages of `Log` and of other keywords that log, as far as the run's log level lets them through, and Robot Framework's own warnings and errors;
  - each with its level, except for `INFO`, and colored by level;
  - each with a link at its end to the file and line it was logged from, where RobotCode reports one;
  - followed by the test's failure details, as before.
- Selecting a suite or the run shows the messages of everything below it. The results tree no longer shows the output of the Robot Framework process, so Robot Framework's console options no longer change what a test shows.
- The output of the Robot Framework process moves to a "Terminal" tab, complete and in its order, as a terminal run shows it: for example the text of `Log To Console`, the test status lines, the `[ WARN ]` and `[ ERROR ]` lines that Robot Framework writes, and the `Output:`, `Log:` and `Report:` lines, which stay links. It is the first tab of the run window and the one shown when a run starts; the results tree with the messages follows in a tab named "Debug Console".
- Debug sessions show the same "Terminal" tab, also shown when the session starts, next to their Debugger tab and their console, which is named "Debug Console" and shows the results tree with the messages per test.

Behaviour that users notice, for the release notes (not breaking): a selected test shows its log messages instead of the process output, also when Robot Framework's console is switched off; the process output has a "Terminal" tab of its own that looks like a terminal run and is shown first (#528); the tab of the results tree is named "Debug Console".

Not part of this change: the debugger's `robotLog` and `robotMessage` events; settings beyond "Output log", "Output messages" and "Output timestamps", which already decide what the debugger sends; filtering messages by level.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-test-results`: what the results tree shows for a test and for the run, the "Terminal" tab of Robot Framework runs and debug sessions, and where the output file lines are links.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotOutputToGeneralTestEventsConverter.kt`: the debugger's `output` events become colored messages with a location for the innermost running suite or test; the process output no longer reaches the results tree.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeRunnerConsoleView.kt`: owns the "Terminal" console, attaches it to the process and adds its tab to the run window.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/debugging/RobotCodeDebugProcess.kt`: adds the tab to the window of a debug session.
- A new formatter for log messages in `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/`.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the tab title.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to robotcode, the language server, the VS Code extension or `robot.toml`.
