# Design

## Context

See proposal.md for the motivation.

**Builds on landed changes** (all archived):
- `intellij-test-result-events`: the converter reports to the platform's events processor directly (`TestStartedEvent`, `TestFailedEvent` and so on, with the robot event ids as node ids), applies robot events and process output in one order, and re-marks tests on a failed suite teardown. It passes each suite's and test's long name as the node's metainfo, with which `RobotSMTestLocator` finds a test in the discovery model of its file again (`currentLine`). Warnings and errors that Robot Framework writes to its console appear in the output of their test.
- `intellij-run-configuration-target`: the run configuration extends PyCharm's `AbstractPythonRunConfiguration` and stores its target in `RobotCodeRunConfigurationOptions`. A "Tests and suites" target (`SELECTION`) holds items with kind, full name, label, `relSource`, suite and the suite's `relSource`, as discovery reports them, plus the name of the top-level suite; `selectionItemOf` builds such an item for a discovery item, as gutter and context runs store it. An item that has only a full name is looked up in the current discovery model at the start of the run; if it is not found, only `-bl` is passed for it (`resolveStoredSelection`). `ModuleBasedConfiguration.clone()` copies a configuration with its options. The run state's `createAndAttachConsole` creates `RobotCodeRunnerConsoleView`, and its `execute(Executor)` adds the rerun-failed action to the result. Both program runners start the run state off the UI thread.
- `intellij-run-selection-args`: `selectionArguments` turns resolved items into `-I`, `-N` with the top-level suite, `-s` and `-bl` after `--`. A "Files and folders" target (`PATHS`) passes its paths and no `-N` (`targetArguments`).
- `intellij-run-and-debug-options`: the report or the log opens after a run, and the run and debug tabs have "Open Report" and "Open Log"; all of them open the file in the target of "Open output target" (`RobotCodeOutputFiles.kt`).

**Current code** (checked on 2026-10-14):

- A failed test becomes a `TestFailedEvent` with the event's message and no stack trace (`RobotOutputToGeneralTestEventsConverter.kt:147`). `failedKeywords` is decoded into `RobotExecutionEventArguments`, but nothing reads it, and `RobotExecutionAttributes` has no `kwname` or `libname` (`RobotCodeDebugProtocolClient.kt:37-51`, `:102`).
- The listener collects failed keywords of type `KEYWORD`, `SETUP` and `TEARDOWN` that have a source, outermost first (`listeners.py:212-219`, `insert(0, …)`). Each entry holds Robot Framework's keyword attributes plus the failure message. A check with Robot Framework 7.5 showed `kwname` (`Should Be Equal`), `libname` (`BuiltIn`, or the resource name `common` for a user keyword), and `source` and `lineno` of the call site, not of the keyword's definition.
- `robotEnqueued` is decoded, fired as `onRobotEnqueued` and answered with `robot/sync`, but nothing subscribes (`RobotCodeDebugProtocolClient.kt:158`, `:196-200`). The listener sends it once, at the first suite start, with the ids of all suites and tests of the run after Robot Framework's filtering: suites as `<source>;<long name>`, tests as `<source>;<long name>;<line>` (`listeners.py:362-381`).
- `RobotRunnerConsoleProperties` sets `isUsePredefinedMessageFilter = false` and registers no filter (`RobotRunnerConsoleProperties.kt:20`). A runtime check found no hyperlink in a console that printed `Output:`, `Log:` and `Report:`.
- `createRerunFailedTestsAction` returns an action that overrides nothing (`RobotRunnerConsoleProperties.kt:51-57`). `AbstractRerunFailedTestsAction` is active only when a model was set through `setModel` or `setModelProvider`, and its default `getRunProfile` returns `null`, so the action stayed disabled at runtime. The Run and Debug runners accept only `RobotCodeRunConfiguration` (`RobotCodeProgramRunner.kt:61-63`, `RobotCodeDebugProgramRunner.kt:24-26`); the profile runner only rejects Robot Framework configurations.
- Robot Framework 7.5 writes its own OSC 8 terminal links into the `Output:`, `Log:` and `Report:` lines only with `--consolecolors on`; through the pipe of a run with the default colors, the lines are plain (checked on the command line).

**Platform API** (javap against PyCharm 2026.1):

- `TestFailedEvent` has public constructors that take a stack trace. `TestStartedEvent(name, id, parentId, locationUrl, metainfo, nodeType, nodeArgs, running)` is public, and `SMTestProxy.getMetainfo()` returns the metainfo.
- `SMTRunnerConsoleProperties.addStackTraceFilter(Filter)` adds to the filters that its default `getErrorNavigatable(Location, String)` applies to the stack trace, line by line; the first `FileHyperlinkInfo` found becomes the navigation target of a failed leaf (`SMTestProxy.getDescriptor`). These filters do not create links in the console; `BaseTestsOutputConsoleView.addMessageFilter(Filter)` does.
- `GeneralTestEventsProcessor.onTestsCountInSuite(int)` sets the number of tests the progress counts against.
- `AbstractRerunFailedTestsAction`: `init(TestConsoleProperties)`, `setModel(TestFrameworkRunningModel)`, the protected `getRunProfile(ExecutionEnvironment)` and `getFailedTests(Project)`, and the public abstract `MyRunProfile(RunConfigurationBase)`, which implements `WrappingRunConfiguration` with `getPeer()`. By default, failed means failed or interrupted, and not ignored. `SMTRunnerConsoleView.getResultsViewer()` is public. None of these is `@Internal`; `setModelProvider` takes an obsolete `Getter`.
- `OpenFileHyperlinkInfo` is public.

## Goals / Non-Goals

**Goals:**

- Failure locations, output file links and navigation through one filter class, tested as a pure matcher.
- Rerunning failed tests through the same target model and selection arguments as every other run.

**Non-Goals:**

- Opening the report or the log after a run, and toolbar actions for that; intellij-run-and-debug-options added them.
- Per-test entries built from `robotLog` and `robotMessage`, see the decision below.
- A pre-built tree of planned tests, and gutter state keys based on long names.
- Turning off Robot Framework's own terminal links when a project forces console colors.

## Decisions

### The failed keywords as the failure's stack trace

The converter reports a failed test with a `TestFailedEvent` whose message is Robot Framework's message, as before, and whose stack trace has one line per failed keyword, innermost first (the listener's list reversed):

```
    at BuiltIn.Should Be Equal (/path/resources/common.resource:4)
    at common.Build Greeting (/path/tests/sample.robot:7)
```

The name is `<libname>.<kwname>`, or `kwname` alone when there is no library name; the location is the call site from `source` and `lineno`. `RobotExecutionAttributes` gets `kwname` and `libname`. A test without failed keywords gets no stack trace, so it keeps navigating to its own line.

Alternative: one message per keyword, as VS Code's test messages. The platform's failure has exactly one message and one stack trace, and the console shows them together.

### One filter class for locations and output files

A filter recognizes two forms in a console line:
- a location `(<path>:<line>)` at the end of a line, where the path may contain spaces, a drive letter and backslashes; it links the path and line to an `OpenFileHyperlinkInfo` for that line;
- an output file line `Output:`, `Log:`, `Report:`, `XUnit:` or `Debug:`, followed by spaces and a path; it links the path: an `.html` file opens in the target of "Open output target", through the function of Open Report and Open Log, any other file with an `OpenFileHyperlinkInfo`.

Both forms get a link only for an absolute path of an existing file, so `NONE` stays plain text.

The console properties register it with `addStackTraceFilter`, so navigation from a failed test uses the first location of the stack trace, which is the innermost keyword. The run console registers it with `addMessageFilter`, so the stack trace and the output file lines are clickable. No override of `getErrorNavigatable` is needed.

Alternatives:
- Switching on the platform's predefined message filters: they know no Robot Framework formats and add filters, such as URL detection, that the run console does not have today.
- `BrowserUtil.browse(Path)` for `.html` files: with the IDE's default browser setting "System default", the desktop picks the program for the file, which can be a file manager, as intellij-run-and-debug-options found.

### The test count from `robotEnqueued`

On `robotEnqueued`, the converter counts the ids that have the test form, at least three `;`-separated parts with a numeric last part, and calls `onTestsCountInSuite` once with that number. Tasks have the same id form. Tests that Robot Framework filtered out are not in the list.

Alternatives:
- Looking the ids up in the discovery model: the model can be stale or empty after a failed discovery, and the event already carries everything.
- Pre-building the tree of planned tests: unclear in the id-based tree, and not needed for the count.

### Rerun Failed Tests through the discovery items of the failed tests

- **Model:** `createRerunFailedTestsAction` calls `init` with the console properties and `setModel` with the console's results viewer.
- **Run profile:** the action's `getRunProfile` returns a `MyRunProfile` around the configuration of the console properties. Its `getState` builds the state of a copy of that configuration (`clone()`) whose target is a `SELECTION` of the failed tests (`getFailedTests`).
- **Items:** each failed test is looked up in the current discovery model: the test with its name in the file suite whose URI is the file of the test's location. A found test is stored as `selectionItemOf` stores the item of a gutter run, with discovery's top-level suite, so the run resolves it and the selection-argument builder turns it into `-I`, `-N`, `-s` and `-bl`. A failed test that discovery does not know becomes an item with only its long name from the run.
- **Runners:** both runners accept a `WrappingRunConfiguration` whose peer is a Robot Framework configuration, and keep accepting the configuration itself.

File and name identify a test after both kinds of run: a run of a "Tests and suites" target passes `-N` with discovery's top-level suite, so its long names are discovery's, while a run of a "Files and folders" target passes no `-N`, so its long names can start with another top-level suite when its paths differ from discovery's. A rerun's console properties belong to the copy, so a second rerun works from the copy and narrows down further.

Alternatives:
- Items with only the long names from the run, resolved by the run's name lookup: after a run of files and folders whose paths differ from discovery's, these names find nothing.
- Long names cut below the top-level suite: stored items hold the full names as discovery reports them.
- `-bl` arguments without a target: they bypass the selection rules (`-I`, `-N` and `-s`), and a Debug rerun would need its own path.

### No per-test entries from `robotLog` and `robotMessage`

Robot Framework writes every `WARN` and `ERROR` message to its console itself (`[ WARN ] …`), and the console output of a test already shows it. Adding the `robotLog` and `robotMessage` entries as well would print each warning twice. `FAIL` entries are the failure message that the test already shows. The location of a log message is not part of the console line, so it is not linked here.

Alternative: the analysis' plan of `[ LEVEL ] message (<file>:<line>)` lines per test, as VS Code appends them to its test results. VS Code keeps the console output out of its test results; the plugin's run console has it.

## Risks / Trade-offs

- [A failed test was renamed or deleted before the rerun, or lies outside discovery's paths] → It becomes an item with only its long name from the run, which gets only `-bl`, as names typed in the editor do. The other failed tests still run; when none of them is found, Robot Framework ends with its "contains no tests" error, which names the selection.
- [The id form of tests changes in the listener] → The count only feeds the progress total; a unit test pins the form against a recorded `robotEnqueued`.
- [A path ending in `:<digits>)` inside a message is mistaken for a location] → Only a location at the end of a line counts, and a link is created only for an existing file.
- [Projects that force console colors get Robot Framework's own OSC 8 sequences in the output file lines] → This is today's behaviour too; the filter matches the plain form of the default run.

## Migration Plan

None. Nothing is stored.
