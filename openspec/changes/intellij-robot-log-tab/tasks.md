# Tasks

## 1. Log line formatting

- [ ] 1.1 Add a pure formatter for a DAP `output` event: it reads the level from the `[ <LEVEL> ]` prefix after an optional timestamp, maps it to a console content type (`WARN` to `LOG_WARNING_OUTPUT`, `ERROR` and `FAIL` to `LOG_ERROR_OUTPUT`, `DEBUG` and `TRACE` to `LOG_DEBUG_OUTPUT`, everything else to normal output), splits off the final line break, and returns the link text `<file name>:<line>` and target when the event has a `source` and a `line` above `0`. Verify with JUnit tests: an `INFO` line without prefix, `WARN`, `ERROR`, `FAIL`, `DEBUG` and `TRACE` lines, a line with a timestamp, a message of several lines, an event without `source`, an event with line `0`, and a Windows path.

## 2. The "Robot Log" console

- [ ] 2.1 Let `RobotCodeRunnerConsoleView` create a read-only console with `TextConsoleBuilderFactory` (`setViewer(true)`) and register it for disposal with itself. Let the converter write every DAP `output` event into it through the formatter, printing the link with `printHyperlink` and an `OpenFileHyperlinkInfo` at the event's line, and decoding ANSI sequences with `AnsiEscapeDecoder` when the text has any; the event no longer reaches the results tree or the fence. Verify with a light platform test (as `MyPluginTest`) against the recording processor of the converter tests and a recording log sink: `output` events of the categories `console` and `messages` reach the sink in their order, and none reaches the processor.

## 3. The tab in Run and Debug sessions

- [ ] 3.1 Add a helper that adds the "Robot Log" content to a `RunnerLayoutUi` next to the console content, not closeable, with the title from `RobotCode.properties`, unless content with its id already exists. Let `RobotCodeRunnerConsoleView` implement `ExecutionConsoleEx`: `buildUi` calls `RunContentBuilder.buildConsoleUiDefault(ui, this)` and then the helper; `getExecutionConsoleId()` returns a constant. Verify with a light platform test that `buildUi` on a layout from `RunnerLayoutUi.Factory` leaves a console content and one "Robot Log" content, also when called twice.
- [ ] 3.2 Let `RobotCodeDebugProcess.createTabLayouter()` return a layouter whose `registerAdditionalContent` calls the helper. Verify in task 4.2.

## 4. Verification

- [ ] 4.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 4.2 Check the behaviour in the headless PyCharm harness with a test that calls `Log    should not in console`, `Log To Console    show in console` and `Log    a warning    WARN`:
  - the run window shows the tabs Console and "Robot Log"; the console shows `show in console` and Robot Framework's `[ WARN ] a warning`, but not `should not in console`, also with the test selected in the results tree;
  - the "Robot Log" tab shows `should not in console` and `[ WARN ] a warning` in the warning color, each with a link `<file name>:<line>`; clicking the first link opens the test file at the line of that `Log` call;
  - with `log-level = "TRACE"` in `robot.toml`, the `TRACE` lines appear only in the "Robot Log" tab;
  - a Debug run that stops at a breakpoint after the `Log` call shows the tabs Debugger, Console and "Robot Log", and the message only in "Robot Log";
  - a rerun from the run tab starts with an empty "Robot Log" tab; Stop, Rerun and the results tree navigation work as before;
  - `idea.log` gets no new SEVERE entries from RobotCode.
