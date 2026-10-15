# Proposal

## Why

In PyCharm and IntelliJ IDEA, a failed Robot Framework test shows only its failure message in the run tab. It does not say which keyword failed or where, and navigating from the failed test opens the test's first line, not the line that failed. The `Output:`, `Log:` and `Report:` lines at the end of the console are plain text, so `output.xml` and the other output files can only be opened by copying the path, and the report and the log only through the run tab's actions. During a run, the progress has no total. "Rerun Failed Tests" stays disabled even after tests failed. VS Code shows the failed keywords with their locations, links the log and the report, marks the tests that a run will execute when it starts, and reruns failed tests.

## What Changes

- A failed test lists the keywords that failed below its failure message, innermost first, each with the file and line where it was called. Each location is a link to that line. Navigating from the failed test opens the call of the innermost failed keyword. Failures that the test caught before, for example with `TRY`/`EXCEPT`, follow, marked as caught, as Robot Framework's log keeps them collapsed.
- The console lines in which Robot Framework names its output files (`Output:`, `Log:`, `Report:`, `XUnit:`, `Debug:`) become links: `log.html` and `report.html` open where "Open output target" says, like Open Report and Open Log, `output.xml` and the other files in the editor.
- The run tab knows from the start how many tests the run executes, so its progress shows the finished tests out of that total.
- "Rerun Failed Tests" is enabled after a run with failed tests. It runs exactly the tests that failed, including tests that failed through their suite teardown, with the run configuration's other settings, in the same tab, for Run and for Debug, also after a run of files and folders. Rerunning again narrows down to the tests that still fail.

Behaviour that users notice, for the release notes (not breaking): failure details with clickable locations, navigation to the failing line, clickable report and log paths, a progress total, and a working "Rerun Failed Tests".

Not part of this change: opening the report or the log automatically after a run, and toolbar actions for them, which intellij-run-and-debug-options added; Robot Framework's own terminal hyperlinks, which it writes only when console colors are forced; a tree of the planned tests before they run; gutter states that follow a test when lines move; warnings and errors as entries of their own, which already appear in the output of their test.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-test-results`: failure details, the test count, links to Robot Framework's output files, and rerunning failed tests in the run tab.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotOutputToGeneralTestEventsConverter.kt`: failure stack traces from the failed keywords, and the test count from `robotEnqueued`.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/debugging/RobotCodeDebugProtocolClient.kt`: keyword name and library in the event attributes.
- A new console filter in `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/` for locations and output file lines, registered by `RobotRunnerConsoleProperties.kt` and `RobotCodeRunnerConsoleView.kt`.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeOutputFiles.kt`: opening a file in the target of "Open output target", shared by Open Report, Open Log and the links.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotRunnerConsoleProperties.kt`: the rerun action with its model and run profile, which finds the failed tests in the discovery model.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/execution/RobotCodeProgramRunner.kt` and `debugging/RobotCodeDebugProgramRunner.kt`: accept the rerun profile; `debugging/RobotCodeDebugProcess.kt`: the rerun action in the debug tab.
- `packages/debugger/src/robotcode/debugger/listeners.py`: each failed keyword says whether its failure was caught; VS Code's test messages ignore the mark and stay as they are; a test under `tests/robotcode/debugger/`.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the VS Code extension or `robot.toml`.
