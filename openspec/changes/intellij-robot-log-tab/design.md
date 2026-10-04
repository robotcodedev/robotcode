# Design

## Context

See proposal.md for the motivation. Decision D6 of the maintainer: Robot Framework's log messages get their own "Robot Log" tab in the run window instead of the main console (issue #528).

**Builds on a planned change.** `intellij-test-result-events` is not implemented yet. This design relies on its planned design: the converter reports to the platform's events processor directly, applies every DAP item under one lock after a fence against the process output, and today's grey log lines become `TestOutputEvent`s for the innermost running suite or test.

**Planned neighbour.** `intellij-debugger-expressions` (planned, not implemented) also overrides `RobotCodeDebugProcess.createTabLayouter()`, to add a "Robot Debug Console" tab in `registerAdditionalContent`, and lets breakpoints with Suspend off send their log text as a logpoint, which the debugger writes as an `output` event.

**How robotcode emits log output** (checked in `packages/debugger/` on 2026-10-03):

- `robotcode debug` sends log messages as DAP `output` events. `--output-log` is on by default (`cli.py`), `--output-messages` and `--output-timestamps` are off, and the plugin passes none of these flags (`RobotCodeRunProfileState.kt:97-106`).
- `Debugger.log_message` sends every message that Robot Framework passes to listeners as an `output` event of category `console` when `--output-log` is on (`debugger.py:1437-1445`). Robot Framework passes only messages at or above the run's log level (`robot/output/listeners.py:298-299`).
- `Debugger.message` sends Robot Framework's system messages with category `messages`: all of them with `--output-messages`, and otherwise the `WARN`, `ERROR` and `FAIL` messages that occur outside a keyword (`debugger.py:1497-1504`).
- The text is `[<timestamp> ][[ <LEVEL> ] ]<message>\n`: the timestamp only with `--output-timestamps`, the level for every level but `INFO` (`debugger.py:1483-1495`). ANSI colors are added only when robotcode decides to color its output: through the plugin's pipe, that happens only with `FORCE_COLOR` in the environment (`plugin/__init__.py:237-259`).
- Each event carries `source` and `line`: the file and line of the current keyword call, or the file and line that the message names in the form `… in file '<path>' on line <n>` (`debugger.py:1453-1481`). Without a file, `source` is missing and `line` is `0`.
- Breakpoints with a log message produce `output` events of category `console` with source and line (`debugger.py:759-778`). The plugin's breakpoint dialog cannot create such breakpoints today. Group output events are sent only with `--group-output`, which the plugin does not pass.
- `robotLog` and `robotMessage` are separate custom events, which the plugin does not show.

**The plugin today:** the converter turns each DAP `output` event into a grey `testStdOut` or `testStdErr` line of the innermost started suite or test (`RobotOutputToGeneralTestEventsConverter.kt:117-126`), so the messages appear in the console between the process output. The run console is `RobotCodeRunnerConsoleView`, an `SMTRunnerConsoleView`. In a debug session, `RobotCodeDebugProcess.createConsole()` returns the same console as the session's Console tab (`RobotCodeDebugProcess.kt:139-141`).

**Platform API** (javap against PyCharm 2026.1, none of it `@ApiStatus`-annotated):

- Run sessions: `RunContentBuilder.createDescriptor` calls `ExecutionConsoleEx.buildUi(RunnerLayoutUi)` when the execution console implements it, and the public static `RunContentBuilder.buildConsoleUiDefault(ui, console)` otherwise; the latter adds the console as content `ConsoleContent` with its editor actions. `ExecutionConsoleEx.getExecutionConsoleId()` names the layout the platform remembers. `RunnerLayoutUi.createContent` and `addContent` are public.
- Debug sessions: `XDebugSessionTab.attachToSession` takes the tab layouter from `XDebugProcess.createTabLayouter()` (in the local IDE through `MonolithSessionProxy`), registers the console with `registerConsoleContent` and then calls `registerAdditionalContent(RunnerLayoutUi)`, which does nothing by default. In 2026.1, `registerConsoleContent` adds the console directly and does not call `ExecutionConsoleEx.buildUi`.
- Consoles: `TextConsoleBuilderFactory.createBuilder(project)` with `setViewer(true)` gives a read-only `ConsoleView`; `print` and `printHyperlink` may be called from any thread. `ConsoleViewContentType` has `LOG_DEBUG_OUTPUT`, `LOG_INFO_OUTPUT`, `LOG_WARNING_OUTPUT` and `LOG_ERROR_OUTPUT`. `AnsiEscapeDecoder` and `OpenFileHyperlinkInfo` are public.

## Goals / Non-Goals

**Goals:**

- One place for all log output that the debugger sends, in Run and Debug sessions alike, as VS Code's Debug Console is for both.
- A run console that holds only the process output, so that the order and per-test output of the result events change keep their meaning.
- Only public, non-experimental platform API.

**Non-Goals:**

- The debugger's output flags (`--output-log`, `--output-messages`, `--output-timestamps`) as settings.
- Filtering the tab by the test selected in the results tree, or grouping messages by test.
- Showing `robotLog` or `robotMessage` events.

## Decisions

### Every DAP `output` event goes to the "Robot Log" console

The converter writes every DAP `output` event into the run's "Robot Log" console, whatever its category, and no longer reports it to the results tree. These events then also leave the fence of the result events, because the order between the console and the "Robot Log" tab does not matter; within the tab, the DAP order is kept, since the events arrive in order on one thread. When breakpoints can log messages, which the breakpoint dialog cannot do yet, their messages arrive in the same tab.

Alternative: sending only the `console` category to the tab and keeping `messages` in the console. Robot Framework already writes its warnings and errors to its own stderr, so the console has them either way, and VS Code shows both categories in its Debug Console.

### One read-only console per run, owned by the run console

`RobotCodeRunnerConsoleView` creates the "Robot Log" console with `TextConsoleBuilderFactory` as a viewer and registers it for disposal with itself, so it lives exactly as long as the run's console, also across reruns, which create a new console. The converter reaches it through the console properties' run state, as it reaches the DAP client today, and prints from the DAP thread.

Alternative: one console per project or a tool window. Messages of consecutive or parallel runs would mix, and a rerun would not start with an empty log.

### The tab in Run sessions through `ExecutionConsoleEx`

`RobotCodeRunnerConsoleView` implements `ExecutionConsoleEx`. Its `buildUi` adds itself with `RunContentBuilder.buildConsoleUiDefault`, exactly as the default path does, and then adds the "Robot Log" content next to it, not closeable. `getExecutionConsoleId()` returns a constant, so the platform remembers the layout of Robot Framework runs on its own.

Alternatives:
- Adding the content to the layout of the `RunContentDescriptor` after `showRunContent`: it needs code in the runner and depends on when the descriptor's layout exists.
- The platform's log tabs of run configurations (`LogFileOptions`): they show files from disk, so the messages would have to be written to a temporary file first.

### The tab in Debug sessions through the tab layouter

`RobotCodeDebugProcess.createTabLayouter()` returns a layouter whose `registerAdditionalContent` adds the same "Robot Log" content, unless the layout already has content with that id. The guard covers a future platform version that would call `ExecutionConsoleEx.buildUi` for debug tabs as well. The Debugger and Console tabs stay as they are. A shared helper creates the content for both paths, with the title from `RobotCode.properties`. If the debug console of the expressions change has landed first, its layouter gets the "Robot Log" content as a second addition; otherwise this change creates the layouter and that change adds its tab to it.

Alternative: leaving the log messages in the Console tab of debug sessions. Run and Debug would then show the same run differently, while VS Code shows log messages in its Debug Console for both.

### Lines colored by level, with a location link

A pure formatter reads the level from the `[ <LEVEL> ]` prefix after an optional timestamp and picks the content type: `WARN` as `LOG_WARNING_OUTPUT`, `ERROR` and `FAIL` as `LOG_ERROR_OUTPUT`, `DEBUG` and `TRACE` as `LOG_DEBUG_OUTPUT`, `INFO` and anything else as normal output. Text that contains ANSI sequences is decoded with `AnsiEscapeDecoder` instead. When the event has a `source` and a `line` above `0`, the line ends with a link `<file name>:<line>` to an `OpenFileHyperlinkInfo` at that line, printed before the final line break. The text itself stays as robotcode formats it.

Alternative: the location as a full path in parentheses, which a console filter would link. It makes every line long, and the tab is not a console that other filters need to read.

## Risks / Trade-offs

- [Implementing `ExecutionConsoleEx` changes how the run tab is built] → `buildConsoleUiDefault` is what the platform calls without it; the harness check confirms the toolbar, the results tree and the console actions.
- [Users who read log messages under a test node lose them there] → The "Robot Log" tab keeps their order, `log.html` keeps them per test, and the release notes say where they went.
- [A long run at `TRACE` level fills the "Robot Log" console] → The console's cycle buffer limits it, as for every console; the process console is no longer filled by these messages.
- [`RunContentBuilder` lives in the platform's `lang.impl` module] → `buildConsoleUiDefault` is public and unannotated in 261, and `verifyPlugin` against the configured versions reports a change.
- [The plan relies on the planned converter of the result events change] → Only the place where `output` events are handled changes; if that change lands later, this change replaces the grey service messages of today in the same spot.

## Migration Plan

None. Nothing is stored; the platform remembers the new tab in the layout of Robot Framework runs from the first run on.
