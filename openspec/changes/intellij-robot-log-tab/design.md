# Design

## Context

See proposal.md for the motivation. Issue #528 asks for a console that looks like a terminal run. The maintainer's decision of 2026-10-15: what the results tree shows for a test comes from the debugger, because Robot Framework's console can be configured (`--console none`, `dotted` or `quiet`), and the process output gets a "Terminal" tab of its own. This replaces the earlier plan of this change, a "Robot Log" tab next to a console that kept the process output per test.

**Builds on landed changes** (all archived):
- `intellij-test-result-events`: the converter reports to the platform's events processor directly, with the robot event ids as node ids, and applies robot events, DAP `output` events and process output in one order. Process output and `output` events become `TestOutputEvent`s of the innermost running suite or test, the `output` events in grey (`RobotOutputToGeneralTestEventsConverter.kt:171-196`).
- `intellij-debugger-expressions`: `RobotCodeDebugProcess.createTabLayouter()` adds the Robot Debug Console in `registerAdditionalContent` (`RobotCodeDebugProcess.kt:185-187`).
- `intellij-run-and-debug-options`: run configurations and the project default have "Output log", on by default, "Output messages" and "Output timestamps", which a run passes as `--no-output-log`, `--output-messages` and `--output-timestamps`.
- `intellij-test-result-details`: `RobotCodeConsoleFilter` links a location `(<path>:<line>)` at the end of a line and the `Output:`, `Log:`, `Report:`, `XUnit:` and `Debug:` lines; the run console registers it as a message filter (`RobotCodeRunnerConsoleView.kt:17`), and the failed keywords of a failed test are its stack trace.

**How robotcode emits log output** (checked in `packages/debugger/` on 2026-10-15):
- `Debugger.log_message` sends every message that Robot Framework passes to listeners as a DAP `output` event of category `console`, unless "Output log" is off (`debugger.py:1505-1513`). Robot Framework passes only messages at or above the run's log level.
- `Debugger.message` sends Robot Framework's system messages with category `messages`: all of them with "Output messages", otherwise the `WARN`, `ERROR` and `FAIL` messages outside a keyword (`debugger.py:1565-1571`).
- The text is `[<timestamp> ][[ <LEVEL> ] ]<message>\n`: the timestamp only with "Output timestamps", the level for every level but `INFO` (`debugger.py:1551-1563`). ANSI colors come only when robotcode colors its output, which through the plugin's pipe happens only with `FORCE_COLOR` in the environment.
- Each event carries `source` and `line`: the file and line of the current keyword call, or the file and line that the message names in the form `… in file '<path>' on line <n>` (`debugger.py:1517-1549`). Without a file, `source` is missing and `line` is `0`.
- The custom events `robotLog` and `robotMessage` carry the id of the running test, but come only for `WARN`, `ERROR` and `FAIL` (`listeners.py:256-357`); VS Code shows them in its test results.

**The plugin today:** the run console is `RobotCodeRunnerConsoleView`, an `SMTRunnerConsoleView`; selecting a test shows the process output written while it ran and the grey `output` events. In a debug session, `RobotCodeDebugProcess.createConsole()` returns the same console as the session's Console tab (`RobotCodeDebugProcess.kt:180`).

**Platform API** (javap against PyCharm 2026.1 on 2026-10-03, none of it `@ApiStatus`-annotated; to be checked again before the implementation):
- Run sessions: `RunContentBuilder.createDescriptor` calls `ExecutionConsoleEx.buildUi(RunnerLayoutUi)` when the execution console implements it, and the public static `RunContentBuilder.buildConsoleUiDefault(ui, console)` otherwise; the latter adds the console as content `ConsoleContent` with its editor actions. `ExecutionConsoleEx.getExecutionConsoleId()` names the layout the platform remembers. `RunnerLayoutUi.createContent` and `addContent` are public.
- Debug sessions: `XDebugSessionTab.attachToSession` takes the tab layouter from `XDebugProcess.createTabLayouter()`, registers the console with `registerConsoleContent` and then calls `registerAdditionalContent(RunnerLayoutUi)`. In 2026.1, `registerConsoleContent` adds the console directly and does not call `ExecutionConsoleEx.buildUi`.
- Consoles: `TextConsoleBuilderFactory.createBuilder(project)` with `setViewer(true)` gives a read-only `ConsoleView`; `attachToProcess` connects it to a process handler, and `addMessageFilter` gives it filters. The text of test output may contain ANSI sequences, which the console decodes; it shows the basic ANSI colors in the colors of the IDE's color scheme.

## Goals / Non-Goals

**Goals:**

- What a test shows comes from the debugger, whatever Robot Framework's console options are.
- One place that shows the process output as a terminal run does, for Run and Debug alike.
- Only public, non-experimental platform API.

**Non-Goals:**

- The `robotLog` and `robotMessage` events.
- Settings beyond "Output log", "Output messages" and "Output timestamps".
- Filtering messages by level.

## Decisions

### The debugger's `output` events are the messages of a test

The converter keeps reporting each DAP `output` event as a `TestOutputEvent` of the innermost running suite or test, in its place among the robot events, so that a message belongs to the test that ran when it was logged. It formats the text with a pure formatter instead of the grey color. Selecting a node in the results tree shows its own output and that of everything below it, so a suite or the run shows all messages below it.

Alternative: the `robotLog` and `robotMessage` events, which name their test: they come only for `WARN`, `ERROR` and `FAIL`, so the messages of `Log` would be missing.

### Lines colored by level, with the location at the end

The formatter reads the level from the `[ <LEVEL> ]` prefix after an optional timestamp and colors the line with a basic ANSI color: `WARN` yellow, `ERROR` and `FAIL` red, `DEBUG` and `TRACE` grey, `INFO` and anything else not at all. Text that already contains ANSI sequences keeps them. When the event has a `source` and a `line` above `0`, the formatter appends ` (<path>:<line>)` before the final line break, which `RobotCodeConsoleFilter` links in the run console, as it links the failed keywords of the failure details.

Alternatives:
- Console content types such as `LOG_WARNING_OUTPUT`: a `TestOutputEvent` knows only standard output and standard error.
- A short `<file name>:<line>` link: the events processor takes text only, and a console filter cannot find a file from its name.

### The process output goes to a "Terminal" console

`RobotCodeRunnerConsoleView` creates a read-only console with `TextConsoleBuilderFactory`, registers `RobotCodeConsoleFilter` on it and attaches it to the run's process handler, so it shows everything the process writes, with its colors, as the console of any other run does. It disposes the console with itself, so a rerun, which creates a new run console, starts with an empty "Terminal" tab. The converter no longer reports process output to the results tree; the platform's system output, the command line and the exit message, stays uncaptured output of the run, so the root of the results tree keeps it, and the "Terminal" tab shows it as well.

Alternative: printing the process output from the converter into the "Terminal" console: the console attached to the process handler shows the same text without a second path through the converter's ordering.

### The tab in Run sessions through `ExecutionConsoleEx`

`RobotCodeRunnerConsoleView` implements `ExecutionConsoleEx`. Its `buildUi` adds itself with `RunContentBuilder.buildConsoleUiDefault`, as the default path does, and then the "Terminal" content next to it, not closeable. `getExecutionConsoleId()` returns a constant, so the platform remembers the layout of Robot Framework runs.

Alternatives:
- Adding the content to the layout of the `RunContentDescriptor` after `showRunContent`: it needs code in the runner and depends on when the descriptor's layout exists.
- The platform's log tabs of run configurations (`LogFileOptions`): they show files from disk.

### The tab in Debug sessions through the tab layouter

The tab layouter of `RobotCodeDebugProcess`, which adds the Robot Debug Console, adds the "Terminal" content as well, unless the layout already has content with its id; the guard covers a platform version that would call `ExecutionConsoleEx.buildUi` for debug tabs too. A shared helper creates the content for both paths, with the title from `RobotCode.properties`. The session's Console tab is the run console, so it shows the results tree with the messages per test.

## Risks / Trade-offs

- [Users who looked for the text of `Log To Console` under a test] → It is in the "Terminal" tab, in the order of a terminal run; the release notes say so.
- [With "Output log" switched off, a test shows no messages] → It is the user's switch; the "Terminal" tab still has the process output, and `log.html` has every message.
- [Long lines from the full paths of the locations] → The same form as the failed keywords of the failure details; the console can soft-wrap.
- [A long run at `TRACE` level fills the output of the results tree] → As today, where the grey lines hold the same messages.
- [Implementing `ExecutionConsoleEx` changes how the run tab is built] → `buildConsoleUiDefault` is what the platform calls without it; the harness check confirms the toolbar, the results tree and the console actions.
- [`RunContentBuilder` lives in the platform's `lang.impl` module] → `buildConsoleUiDefault` is public and unannotated in 261; `verifyPlugin` against the configured versions reports a change.

## Migration Plan

None. Nothing is stored; the platform remembers the new tab in the layout of Robot Framework runs from the first run on.

## Open Questions

- The tab title "Terminal" may be mistaken for IntelliJ's Terminal tool window; "Output" would avoid that.
